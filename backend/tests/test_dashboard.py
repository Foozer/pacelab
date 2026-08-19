"""Dashboard API tests. Every query is scoped to the authenticated user."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.conftest import csrf_headers, register_account
from tests.test_activities import _activity_payload


def _payload_at(
    provider_activity_id: str,
    started: datetime,
    *,
    activity_type: str = "run",
    distance_meters: float = 5000,
    duration_seconds: int = 1800,
) -> dict[str, object]:
    payload = _activity_payload(provider_activity_id)
    payload["started_at"] = started.isoformat()
    payload["activity_type"] = activity_type
    payload["distance_meters"] = distance_meters
    payload["duration_seconds"] = duration_seconds
    payload["samples"] = []
    return payload


def test_dashboard_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_dashboard_aggregates_current_user_only(client: TestClient) -> None:
    now = datetime.now(UTC)
    register_account(client, "alpha@example.com")
    headers = csrf_headers(client)
    created = client.post(
        "/api/v1/activities",
        json=_payload_at("alpha-recent", now - timedelta(hours=2), distance_meters=6200),
        headers=headers,
    )
    assert created.status_code == 201
    alpha_id = created.json()["id"]

    client.cookies.clear()
    register_account(client, "beta@example.com")
    headers = csrf_headers(client)
    other = client.post(
        "/api/v1/activities",
        json=_payload_at("beta-recent", now - timedelta(hours=1), distance_meters=10000),
        headers=headers,
    )
    assert other.status_code == 201

    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["weekly"]["run_count"] == 1
    assert body["weekly"]["distance_meters"] == 10000
    assert [item["id"] for item in body["recent_activities"]] == [other.json()["id"]]
    assert all(point["activity_id"] != alpha_id for point in body["pace_heart_rate_trend"])
    assert body["five_k_estimate"]["available"] is False
    assert "estimate" in body["five_k_estimate"]["note"].lower()
    assert body["easy_pace"]["available"] is True
    assert body["easy_pace"]["run_count"] == 1
    assert body["aerobic_efficiency"]["available"] is True
    assert body["aerobic_efficiency"]["qualifying_run_count"] == 1


def test_dashboard_weekly_ignores_older_runs(client: TestClient) -> None:
    now = datetime.now(UTC)
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    old = client.post(
        "/api/v1/activities",
        json=_payload_at("old-run", now - timedelta(days=10)),
        headers=headers,
    )
    recent = client.post(
        "/api/v1/activities",
        json=_payload_at(
            "new-run",
            now - timedelta(days=1),
            distance_meters=8000,
            duration_seconds=2400,
        ),
        headers=headers,
    )
    assert old.status_code == 201
    assert recent.status_code == 201

    body = client.get("/api/v1/dashboard").json()
    assert body["weekly"]["run_count"] == 1
    assert body["weekly"]["distance_meters"] == 8000
    assert body["weekly"]["duration_seconds"] == 2400
    assert len(body["recent_activities"]) == 2
    assert len(body["pace_heart_rate_trend"]) == 2
    assert body["pace_heart_rate_trend"][0]["activity_id"] == old.json()["id"]
    assert body["pace_heart_rate_trend"][1]["pace_seconds_per_km"] == 300.0
