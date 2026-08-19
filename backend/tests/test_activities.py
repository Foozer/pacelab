"""Activity API and provider tests."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.integrations.exceptions import ProviderNotConfiguredError
from app.integrations.garmin import GarminActivityProvider
from app.integrations.mock.catalog import build_mock_activities
from tests.conftest import csrf_headers, register_account


def _activity_payload(provider_activity_id: str = "test-run-1") -> dict[str, object]:
    started = datetime(2026, 4, 1, 7, 30, tzinfo=UTC)
    return {
        "provider": "mock",
        "provider_activity_id": provider_activity_id,
        "activity_type": "run",
        "started_at": started.isoformat(),
        "duration_seconds": 1800,
        "distance_meters": 5000,
        "average_speed": 5000 / 1800,
        "average_heart_rate": 148,
        "max_heart_rate": 162,
        "average_cadence": 170,
        "elevation_gain": 32,
        "calories": 310,
        "samples": [
            {
                "timestamp": started.isoformat(),
                "elapsed_seconds": 0,
                "distance_meters": 0,
                "heart_rate": 132,
                "speed": 2.7,
                "cadence": 168,
                "elevation": 0,
            },
            {
                "timestamp": datetime(2026, 4, 1, 8, 0, tzinfo=UTC).isoformat(),
                "elapsed_seconds": 1800,
                "distance_meters": 5000,
                "heart_rate": 155,
                "speed": 2.8,
                "cadence": 172,
                "elevation": 32,
            },
        ],
    }


def test_create_and_retrieve_activity(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    created = client.post("/api/v1/activities", json=_activity_payload(), headers=headers)
    assert created.status_code == 201
    body = created.json()
    assert body["provider"] == "mock"
    assert body["provider_activity_id"] == "test-run-1"
    assert body["distance_meters"] == 5000
    assert "user_id" not in body
    assert len(body["samples"]) == 2

    activity_id = body["id"]
    fetched = client.get(f"/api/v1/activities/{activity_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == activity_id
    assert fetched.json()["average_heart_rate"] == 148


def test_unauthenticated_activity_access_rejected(client: TestClient) -> None:
    listed = client.get("/api/v1/activities")
    assert listed.status_code == 401
    assert listed.json()["error"]["code"] == "UNAUTHENTICATED"

    missing = client.get(f"/api/v1/activities/{uuid.uuid4()}")
    assert missing.status_code == 401


def test_user_cannot_retrieve_another_users_activity(client: TestClient) -> None:
    register_account(client, "alpha@example.com")
    headers = csrf_headers(client)
    created = client.post("/api/v1/activities", json=_activity_payload(), headers=headers)
    assert created.status_code == 201
    activity_id = created.json()["id"]

    client.cookies.clear()
    register_account(client, "beta@example.com")
    other = client.get(f"/api/v1/activities/{activity_id}")
    assert other.status_code == 404
    assert other.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"
    assert other.json()["error"]["message"] == "Activity not found"

    unknown = client.get(f"/api/v1/activities/{uuid.uuid4()}")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_duplicate_provider_activity_rejected(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    first = client.post("/api/v1/activities", json=_activity_payload("dup-1"), headers=headers)
    assert first.status_code == 201
    second = client.post("/api/v1/activities", json=_activity_payload("dup-1"), headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_ACTIVITY"


def test_same_provider_id_allowed_for_different_users(client: TestClient) -> None:
    register_account(client, "alpha@example.com")
    headers = csrf_headers(client)
    first = client.post("/api/v1/activities", json=_activity_payload("shared-id"), headers=headers)
    assert first.status_code == 201

    client.cookies.clear()
    register_account(client, "beta@example.com")
    headers = csrf_headers(client)
    second = client.post("/api/v1/activities", json=_activity_payload("shared-id"), headers=headers)
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_activity_list_is_paginated_and_scoped(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    for index in range(3):
        created = client.post(
            "/api/v1/activities",
            json=_activity_payload(f"page-{index}"),
            headers=headers,
        )
        assert created.status_code == 201

    page = client.get("/api/v1/activities", params={"limit": 2, "offset": 0})
    assert page.status_code == 200
    payload = page.json()
    assert payload["total"] == 3
    assert payload["limit"] == 2
    assert len(payload["items"]) == 2
    assert "samples" not in payload["items"][0]


def test_sync_is_idempotent(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    first = client.post("/api/v1/activities/sync", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["provider"] == "mock"
    assert body["created"] >= 20
    assert body["updated"] == 0
    assert body["total"] == body["created"]

    listed = client.get("/api/v1/activities", params={"limit": 100})
    assert listed.status_code == 200
    assert listed.json()["total"] == body["created"]
    assert listed.json()["last_sync_at"] is not None

    second = client.post("/api/v1/activities/sync", headers=headers)
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["updated"] == body["created"]
    listed_again = client.get("/api/v1/activities", params={"limit": 100})
    assert listed_again.json()["total"] == body["created"]


def test_sync_requires_csrf(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    response = client.post("/api/v1/activities/sync")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_REQUIRED"


def test_mock_catalog_has_varied_improving_runs() -> None:
    as_of = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    activities = build_mock_activities(as_of=as_of)
    assert len(activities) >= 20
    distances = {round(item.distance_meters or 0) for item in activities}
    assert len(distances) >= 4
    heart_rates = {item.average_heart_rate for item in activities}
    assert len(heart_rates) >= 4
    started = [item.started_at for item in activities if item.started_at is not None]
    span_days = (max(started) - min(started)).days
    assert span_days >= 40

    easy = [
        item
        for item in activities
        if item.distance_meters is not None
        and 5000 <= item.distance_meters <= 8000
        and item.duration_seconds
        and item.average_heart_rate
        and item.average_heart_rate <= 150
    ]
    easy_sorted = sorted(easy, key=lambda item: item.started_at or datetime.min.replace(tzinfo=UTC))
    assert len(easy_sorted) >= 6
    first_pace = easy_sorted[0].duration_seconds / (easy_sorted[0].distance_meters / 1000)
    last_pace = easy_sorted[-1].duration_seconds / (easy_sorted[-1].distance_meters / 1000)
    assert last_pace < first_pace - 15
    assert all(item.samples for item in activities)
    assert all(
        sample.heart_rate is None or sample.heart_rate > 0
        for item in activities
        for sample in item.samples
    )


def test_garmin_provider_is_stub() -> None:
    async def _check() -> None:
        provider = GarminActivityProvider()
        user_id = uuid.uuid4()
        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            await provider.get_activities(user_id)
        assert exc_info.value.provider == "garmin"
        assert "OAuth" in exc_info.value.message
        assert "password" in exc_info.value.message.lower()
        with pytest.raises(ProviderNotConfiguredError):
            await provider.get_activity(user_id, "any")
        with pytest.raises(ProviderNotConfiguredError):
            await provider.sync_activities(user_id)

    asyncio.run(_check())
