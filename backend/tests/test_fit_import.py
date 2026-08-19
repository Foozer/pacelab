"""FIT-file import tests. Fixtures are local; this does not call Garmin or Strava."""

from __future__ import annotations

import asyncio
import gzip
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.integrations.exceptions import ProviderNotConfiguredError
from app.integrations.fit.parser import (
    GPS_FIELD_NAMES,
    compute_provider_activity_id,
    map_fit_sport,
    parse_fit_activity,
)
from app.integrations.garmin import GarminActivityProvider
from tests.conftest import csrf_headers, register_account
from tests.fit_bytes import (
    FIXTURE_DISTANCE_METERS,
    FIXTURE_DURATION_SECONDS,
    FIXTURE_START,
    encode_activity,
)

FIXTURE = Path(__file__).parent / "fixtures" / "short_run.fit"


def _import_fit(
    client: TestClient,
    payload: bytes,
    *,
    filename: str = "short_run.fit",
    content_type: str = "application/octet-stream",
    headers: dict[str, str] | None = None,
):
    return client.post(
        "/api/v1/activities/import/fit",
        headers=headers or csrf_headers(client),
        files=[("files", (filename, payload, content_type))],
    )


def test_fit_import_requires_authentication(client: TestClient) -> None:
    response = _import_fit(client, FIXTURE.read_bytes())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_fit_import_requires_csrf(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    response = client.post(
        "/api/v1/activities/import/fit",
        files=[("files", ("short_run.fit", FIXTURE.read_bytes(), "application/octet-stream"))],
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_REQUIRED"


def test_fit_import_creates_activity_without_gps(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    response = _import_fit(client, FIXTURE.read_bytes())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    assert body["updated"] == 0
    assert body["failed"] == 0
    assert body["provider"] == "fit"
    activity_id = body["files"][0]["activity_id"]

    detail = client.get(f"/api/v1/activities/{activity_id}")
    assert detail.status_code == 200
    activity = detail.json()
    assert activity["provider"] == "fit"
    assert activity["activity_type"] == "run"
    assert activity["distance_meters"] == FIXTURE_DISTANCE_METERS
    assert activity["duration_seconds"] == FIXTURE_DURATION_SECONDS
    assert activity["average_heart_rate"] == 145
    assert activity["calories"] == 80
    assert activity["samples"]
    for sample in activity["samples"]:
        assert set(sample.keys()) == {
            "timestamp",
            "elapsed_seconds",
            "distance_meters",
            "heart_rate",
            "speed",
            "cadence",
            "elevation",
        }
        assert not GPS_FIELD_NAMES.intersection(sample.keys())
        assert "lat" not in sample
        assert "lon" not in sample
        assert "longitude" not in sample

    listed = client.get("/api/v1/activities", params={"limit": 20})
    assert listed.json()["total"] == 1
    assert listed.json()["last_sync_at"] is not None

    exported = client.get("/api/v1/privacy/export")
    assert exported.status_code == 200
    export_body = exported.json()
    assert export_body["activities"][0]["provider"] == "fit"
    assert export_body["provider_connections"][0]["provider"] == "fit"


def test_fit_reupload_does_not_duplicate(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    first = _import_fit(client, FIXTURE.read_bytes())
    assert first.status_code == 200
    second = _import_fit(client, FIXTURE.read_bytes())
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["updated"] == 1
    listed = client.get("/api/v1/activities", params={"limit": 20})
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["provider_activity_id"] == first.json()["files"][0][
        "provider_activity_id"
    ]


def test_user_b_cannot_see_user_a_fit_import(client: TestClient) -> None:
    register_account(client, "alpha@example.com")
    imported = _import_fit(client, FIXTURE.read_bytes())
    assert imported.status_code == 200
    activity_id = imported.json()["files"][0]["activity_id"]

    client.cookies.clear()
    register_account(client, "beta@example.com")
    listed = client.get("/api/v1/activities", params={"limit": 20})
    assert listed.json()["total"] == 0
    missing = client.get(f"/api/v1/activities/{activity_id}")
    assert missing.status_code == 404
    export = client.get("/api/v1/privacy/export")
    assert export.json()["activities"] == []

    easy = client.get("/api/v1/analytics/easy-running").json()
    assert easy["run_count"] == 0
    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["weekly"]["run_count"] == 0
    assert dashboard["five_k_estimate"]["available"] is False


def test_invalid_fit_bytes_return_422(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    response = _import_fit(client, b"not a fit file")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FIT_IMPORT_FAILED"


def test_oversized_fit_rejected(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    huge = b"\x0e" + b"\x00" * 8 + b".FIT" + b"\x00" * (8 * 1024 * 1024)
    response = _import_fit(client, huge)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FIT_IMPORT_FAILED"


def test_wrong_filename_rejected(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    response = _import_fit(client, FIXTURE.read_bytes(), filename="notes.txt")
    assert response.status_code == 422


def test_gzip_fit_imports(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    compressed = gzip.compress(FIXTURE.read_bytes())
    response = _import_fit(
        client,
        compressed,
        filename="short_run.fit.gz",
        content_type="application/gzip",
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_indoor_run_without_gps_imports() -> None:
    payload = encode_activity(include_gps=False)
    activity = parse_fit_activity(payload)
    assert activity.activity_type == "run"
    assert activity.samples
    assert all(
        field not in sample.__dataclass_fields__
        for field in GPS_FIELD_NAMES
        for sample in [activity.samples[0]]
    )


def test_cycling_imports_as_cycling() -> None:
    payload = encode_activity(sport="cycling", include_gps=False)
    activity = parse_fit_activity(payload)
    assert activity.activity_type == "cycling"


def test_map_fit_sport_rules() -> None:
    assert map_fit_sport("running", "treadmill") == "run"
    assert map_fit_sport("cycling") == "cycling"
    assert map_fit_sport(None) == "other"


def test_provider_activity_id_is_stable_for_session() -> None:
    payload = FIXTURE.read_bytes()
    first = parse_fit_activity(payload)
    second = parse_fit_activity(payload)
    assert first.provider_activity_id == second.provider_activity_id
    expected = compute_provider_activity_id(
        started_at=FIXTURE_START,
        activity_type="run",
        duration_seconds=FIXTURE_DURATION_SECONDS,
        distance_meters=FIXTURE_DISTANCE_METERS,
        payload=payload,
    )
    assert first.provider_activity_id == expected
    assert first.provider_activity_id.startswith("session:")


def test_parsed_samples_have_no_gps_keys() -> None:
    activity = parse_fit_activity(FIXTURE.read_bytes())
    sample = activity.samples[0]
    assert not GPS_FIELD_NAMES.intersection(sample.__slots__)
    assert datetime.fromisoformat(sample.timestamp.isoformat()).tzinfo is not None


def test_garmin_stub_still_unavailable() -> None:
    async def _check() -> None:
        provider = GarminActivityProvider()
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            await provider.sync_activities(uuid.uuid4())
        assert exc_info.value.provider == "garmin"
        assert "OAuth" in exc_info.value.message

    asyncio.run(_check())


def test_fit_import_partial_success(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    response = client.post(
        "/api/v1/activities/import/fit",
        headers=headers,
        files=[
            ("files", ("short_run.fit", FIXTURE.read_bytes(), "application/octet-stream")),
            ("files", ("bad.fit", b"nope", "application/octet-stream")),
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["failed"] == 1
    assert body["files"][1]["status"] == "failed"
