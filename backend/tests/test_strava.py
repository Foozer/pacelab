"""Official Strava OAuth tests. HTTP is mocked; this never calls strava.com."""

from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.integrations.strava.mapping import activity_from_strava, map_strava_sport
from app.main import create_app
from tests.conftest import TEST_PASSWORD, _truncate_auth_tables, csrf_headers, register_account

ACCESS_TOKEN = "test-strava-access-token-never-export"
REFRESH_TOKEN = "test-strava-refresh-token-never-export"
ENCRYPTION_KEY = Fernet.generate_key().decode()

SUMMARY: dict[str, Any] = {
    "id": 424242,
    "sport_type": "Run",
    "type": "Run",
    "start_date": "2026-08-01T07:00:00Z",
    "elapsed_time": 1800,
    "distance": 5000.0,
    "average_speed": 2.777,
    "average_heartrate": 145,
    "max_heartrate": 155,
    "average_cadence": 80.0,
    "total_elevation_gain": 12.0,
    "calories": 310.0,
}

STREAMS: dict[str, Any] = {
    "time": {"data": [0, 1]},
    "distance": {"data": [0.0, 2.8]},
    "heartrate": {"data": [140, 141]},
    "cadence": {"data": [80, 81]},
    "altitude": {"data": [10.0, 10.5]},
    "velocity_smooth": {"data": [2.7, 2.8]},
    "latlng": {"data": [[51.5, -0.12], [51.5001, -0.1201]]},
}


class FakeStrava:
    def __init__(self) -> None:
        self.revoked: list[str] = []
        self.list_calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path in {"/oauth/token", "/api/v3/oauth/token"}:
            return httpx.Response(
                200,
                json={
                    "token_type": "Bearer",
                    "expires_at": int((datetime.now(UTC) + timedelta(hours=6)).timestamp()),
                    "expires_in": 21600,
                    "refresh_token": REFRESH_TOKEN,
                    "access_token": ACCESS_TOKEN,
                    "athlete": {"id": 99},
                    "scope": "activity:read_all",
                },
            )
        if request.method == "POST" and path == "/oauth/revoke":
            body = request.content.decode()
            self.revoked.append(body)
            return httpx.Response(200, json={})
        if request.method == "GET" and path == "/api/v3/athlete/activities":
            self.list_calls += 1
            return httpx.Response(200, json=[SUMMARY])
        if request.method == "GET" and path.endswith("/streams"):
            return httpx.Response(200, json=STREAMS)
        return httpx.Response(404, json={"message": "not mocked"})


@pytest.fixture
def strava_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "strava-test-secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost:8000/api/v1/strava/callback")
    monkeypatch.setenv("ENCRYPTION_KEY", ENCRYPTION_KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def strava_client(strava_env: None) -> Generator[tuple[TestClient, FakeStrava], None, None]:
    fake = FakeStrava()
    application = create_app(get_settings())
    application.state.strava_transport = httpx.MockTransport(fake)
    with TestClient(application) as test_client:
        yield test_client, fake
    _truncate_auth_tables()


def _connect(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    start = client.get("/api/v1/strava/connect", follow_redirects=False)
    assert start.status_code == 302
    location = start.headers["location"]
    assert location.startswith("https://www.strava.com/oauth/authorize")
    state = parse_qs(urlparse(location).query)["state"][0]
    callback = client.get(
        "/api/v1/strava/callback",
        params={"code": "one-time-code", "state": state, "scope": "activity:read_all"},
        follow_redirects=False,
    )
    assert callback.status_code == 302
    assert "strava=connected" in callback.headers["location"]


def test_map_strava_sport() -> None:
    assert map_strava_sport("Run", "Run") == "run"
    assert map_strava_sport("Treadmill", None) == "run"
    assert map_strava_sport("Ride", "Ride") == "ride"
    assert map_strava_sport(None, None) == "other"


def test_samples_drop_latlng_even_when_present() -> None:
    activity = activity_from_strava(SUMMARY, streams=STREAMS)
    assert activity.provider == "strava"
    assert activity.provider_activity_id == "424242"
    assert activity.activity_type == "run"
    sample = activity.samples[0]
    assert not hasattr(sample, "latlng")
    assert "latlng" not in sample.__slots__
    dumped = json.dumps(asdict(sample), default=str)
    assert "51.5" not in dumped
    assert "latlng" not in dumped


def test_connect_returns_501_when_unconfigured(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    response = client.get("/api/v1/strava/connect", follow_redirects=False)
    assert response.status_code == 501
    body = response.json()
    assert body["error"]["code"] == "STRAVA_NOT_CONFIGURED"
    assert "not configured" in body["error"]["message"].lower()


def test_connect_returns_501_without_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRAVA_CLIENT_ID", "12345")
    monkeypatch.setenv("STRAVA_CLIENT_SECRET", "strava-test-secret")
    monkeypatch.setenv("STRAVA_REDIRECT_URI", "http://localhost:8000/api/v1/strava/callback")
    monkeypatch.setenv("ENCRYPTION_KEY", "")
    get_settings.cache_clear()
    application = create_app(get_settings())
    with TestClient(application) as configured:
        register_account(configured, "keyless@example.com")
        response = configured.get("/api/v1/strava/connect", follow_redirects=False)
        assert response.status_code == 501
        assert response.json()["error"]["code"] == "ENCRYPTION_UNAVAILABLE"
    _truncate_auth_tables()
    get_settings.cache_clear()


def test_callback_rejects_bad_state(strava_client: tuple[TestClient, FakeStrava]) -> None:
    client, _fake = strava_client
    register_account(client, "runner@example.com")
    client.get("/api/v1/strava/connect", follow_redirects=False)
    response = client.get(
        "/api/v1/strava/callback",
        params={"code": "abc", "state": "not-the-real-state", "scope": "activity:read_all"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "STRAVA_OAUTH_STATE_INVALID"


def test_tokens_absent_from_json_and_export(strava_client: tuple[TestClient, FakeStrava]) -> None:
    client, _fake = strava_client
    _connect(client)
    status = client.get("/api/v1/strava/status")
    assert status.status_code == 200
    payload = status.json()
    raw = status.text
    assert payload["connected"] is True
    assert ACCESS_TOKEN not in raw
    assert REFRESH_TOKEN not in raw
    assert "access_token" not in payload
    assert "refresh_token" not in payload

    export = client.get("/api/v1/privacy/export")
    assert export.status_code == 200
    assert ACCESS_TOKEN not in export.text
    assert REFRESH_TOKEN not in export.text
    assert "access_token_encrypted" not in export.text
    assert "refresh_token" not in export.text
    body = export.json()
    for needle in ("access_token", "refresh_token", "ENCRYPTION_KEY"):
        assert needle not in json.dumps(body)


def test_sync_requires_auth_and_csrf(strava_client: tuple[TestClient, FakeStrava]) -> None:
    client, _fake = strava_client
    headers = csrf_headers(client)
    unauthenticated = client.post("/api/v1/strava/sync", headers=headers)
    assert unauthenticated.status_code == 401

    register_account(client, "runner@example.com")
    missing_csrf = client.post("/api/v1/strava/sync")
    assert missing_csrf.status_code == 403

    not_connected = client.post("/api/v1/strava/sync", headers=csrf_headers(client))
    assert not_connected.status_code == 409
    assert not_connected.json()["error"]["code"] == "STRAVA_NOT_CONNECTED"


def test_sync_and_resync_are_idempotent(strava_client: tuple[TestClient, FakeStrava]) -> None:
    client, _fake = strava_client
    _connect(client)
    headers = csrf_headers(client)
    first = client.post("/api/v1/strava/sync", headers=headers)
    assert first.status_code == 200
    body = first.json()
    assert body["provider"] == "strava"
    assert body["created"] == 1
    listed = client.get("/api/v1/activities")
    items = listed.json()["items"]
    assert len(items) == 1
    assert items[0]["provider"] == "strava"
    assert items[0]["provider_activity_id"] == "424242"
    detail = client.get(f"/api/v1/activities/{items[0]['id']}")
    samples = detail.json()["samples"]
    assert samples
    for sample in samples:
        assert "latlng" not in sample
        assert "latitude" not in sample
        assert "longitude" not in sample

    second = client.post("/api/v1/strava/sync", headers=csrf_headers(client))
    assert second.status_code == 200
    assert second.json()["created"] == 0
    assert second.json()["updated"] == 1
    listed_again = client.get("/api/v1/activities")
    assert listed_again.json()["total"] == 1


def test_user_b_cannot_see_user_a_strava(strava_client: tuple[TestClient, FakeStrava]) -> None:
    client, _fake = strava_client
    _connect(client)
    client.post("/api/v1/strava/sync", headers=csrf_headers(client))
    alpha_id = client.get("/api/v1/activities").json()["items"][0]["id"]

    client.cookies.clear()
    register_account(client, "other@example.com")
    listed = client.get("/api/v1/activities")
    assert listed.json()["total"] == 0
    missing = client.get(f"/api/v1/activities/{alpha_id}")
    assert missing.status_code == 404
    status = client.get("/api/v1/strava/status")
    assert status.json()["connected"] is False


def test_disconnect_revokes_keeps_activities(strava_client: tuple[TestClient, FakeStrava]) -> None:
    client, fake = strava_client
    _connect(client)
    client.post("/api/v1/strava/sync", headers=csrf_headers(client))
    response = client.post(
        "/api/v1/privacy/providers/strava/disconnect",
        json={"password": TEST_PASSWORD},
        headers=csrf_headers(client),
    )
    assert response.status_code == 200
    message = response.json()["message"]
    assert "not a Garmin disconnect" in message
    assert fake.revoked
    listed = client.get("/api/v1/activities")
    assert listed.json()["total"] == 1
    status = client.get("/api/v1/strava/status")
    assert status.json()["connected"] is False
    connections = client.get("/api/v1/privacy/connections")
    assert all(item["provider"] != "strava" for item in connections.json()["items"])


def test_app_starts_with_empty_strava_env(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    status = client.get("/api/v1/strava/status")
    assert status.status_code == 401


def test_mock_sync_is_not_strava(strava_client: tuple[TestClient, FakeStrava]) -> None:
    client, fake = strava_client
    register_account(client, "runner@example.com")
    response = client.post("/api/v1/activities/sync", headers=csrf_headers(client))
    assert response.status_code == 200
    assert response.json()["provider"] == "mock"
    assert fake.list_calls == 0
