"""Analytics API tests. Every query is scoped to the authenticated user."""

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
    average_heart_rate: int = 145,
) -> dict[str, object]:
    payload = _activity_payload(provider_activity_id)
    payload["started_at"] = started.isoformat()
    payload["activity_type"] = activity_type
    payload["distance_meters"] = distance_meters
    payload["duration_seconds"] = duration_seconds
    payload["average_heart_rate"] = average_heart_rate
    payload["average_speed"] = distance_meters / duration_seconds if duration_seconds else None
    payload["samples"] = []
    return payload


def _post_run(client: TestClient, payload: dict[str, object]) -> dict[str, object]:
    headers = csrf_headers(client)
    response = client.post("/api/v1/activities", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


ANALYTICS_PATHS = (
    "/api/v1/analytics/easy-running",
    "/api/v1/analytics/trends",
    "/api/v1/analytics/aerobic-efficiency",
)


def test_analytics_routes_require_authentication(client: TestClient) -> None:
    for path in ANALYTICS_PATHS:
        response = client.get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_analytics_user_isolation(client: TestClient) -> None:
    now = datetime.now(UTC)
    register_account(client, "alpha@example.com")
    _post_run(
        client,
        _payload_at(
            "alpha-easy",
            now - timedelta(days=2),
            distance_meters=6200,
            duration_seconds=2400,
        ),
    )

    client.cookies.clear()
    register_account(client, "beta@example.com")
    beta = _post_run(
        client,
        _payload_at(
            "beta-easy",
            now - timedelta(days=1),
            distance_meters=8000,
            duration_seconds=3000,
            average_heart_rate=144,
        ),
    )

    easy = client.get("/api/v1/analytics/easy-running").json()
    assert easy["run_count"] == 1
    assert easy["distance_meters"] == 8000
    assert [point["activity_id"] for point in easy["points"]] == [beta["id"]]

    trends = client.get("/api/v1/analytics/trends").json()
    assert [point["activity_id"] for point in trends["points"]] == [beta["id"]]

    aerobic = client.get("/api/v1/analytics/aerobic-efficiency").json()
    assert aerobic["metric"]["available"] is True
    assert aerobic["metric"]["qualifying_run_count"] == 1
    assert aerobic["metric"]["direction"] == "not_enough_data"
    assert [point["activity_id"] for point in aerobic["points"]] == [beta["id"]]


def test_analytics_insufficient_data(client: TestClient) -> None:
    register_account(client, "empty@example.com")
    easy = client.get("/api/v1/analytics/easy-running").json()
    assert easy["run_count"] == 0
    assert easy["average_pace_seconds_per_km"] is None

    aerobic = client.get("/api/v1/analytics/aerobic-efficiency").json()
    assert aerobic["metric"]["available"] is False
    assert "enough" in aerobic["metric"]["headline"].lower()

    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["five_k_estimate"]["available"] is False
    assert "estimate" in dashboard["five_k_estimate"]["note"].lower()
    assert dashboard["easy_pace"]["available"] is False
    assert dashboard["aerobic_efficiency"]["available"] is False


def test_heart_rate_range_validation(client: TestClient) -> None:
    register_account(client, "ranges@example.com")
    inverted = client.get("/api/v1/analytics/easy-running", params={"hr_min": 150, "hr_max": 140})
    assert inverted.status_code == 422
    assert inverted.json()["error"]["code"] == "VALIDATION_ERROR"

    equal = client.get("/api/v1/analytics/easy-running", params={"hr_min": 145, "hr_max": 145})
    assert equal.status_code == 422

    too_low = client.get("/api/v1/analytics/easy-running", params={"hr_min": 10, "hr_max": 140})
    assert too_low.status_code == 422

    bad_range = client.get("/api/v1/analytics/trends", params={"range": "2d"})
    assert bad_range.status_code == 422
    assert bad_range.json()["error"]["code"] == "VALIDATION_ERROR"


def test_easy_running_respects_requested_band(client: TestClient) -> None:
    now = datetime.now(UTC)
    register_account(client, "zones@example.com")
    _post_run(client, _payload_at("easy", now - timedelta(days=1), average_heart_rate=145))
    _post_run(
        client,
        _payload_at(
            "tempo",
            now - timedelta(days=2),
            duration_seconds=1500,
            average_heart_rate=168,
        ),
    )

    default_band = client.get("/api/v1/analytics/easy-running").json()
    assert default_band["run_count"] == 1
    assert default_band["heart_rate_min"] == 140
    assert default_band["heart_rate_max"] == 150

    wide = client.get(
        "/api/v1/analytics/easy-running",
        params={"hr_min": 140, "hr_max": 175},
    ).json()
    assert wide["run_count"] == 2


def test_dashboard_fills_metrics_from_seed_shaped_runs(client: TestClient) -> None:
    now = datetime.now(UTC)
    register_account(client, "story@example.com")
    for week in range(6):
        started = now - timedelta(days=(5 - week) * 7 + 1)
        pace = 380 - week * 8
        _post_run(
            client,
            _payload_at(
                f"week-{week}",
                started,
                distance_meters=6000,
                duration_seconds=int(6 * pace),
                average_heart_rate=146,
            ),
        )

    dashboard = client.get("/api/v1/dashboard").json()
    assert dashboard["five_k_estimate"]["available"] is True
    assert dashboard["five_k_estimate"]["estimated_seconds"] > 0
    assert "estimate" in dashboard["five_k_estimate"]["note"].lower()
    assert dashboard["easy_pace"]["available"] is True
    assert dashboard["easy_pace"]["run_count"] == 6
    assert "improving" in dashboard["easy_pace"]["headline"].lower()
    assert dashboard["aerobic_efficiency"]["available"] is True
    assert dashboard["aerobic_efficiency"]["direction"] == "improving"
    assert dashboard["aerobic_efficiency"]["headline"] == "Your easy pace is improving"
    assert dashboard["weekly"]["run_count"] >= 1
    assert len(dashboard["recent_activities"]) == 5
    assert len(dashboard["pace_heart_rate_trend"]) == 6
