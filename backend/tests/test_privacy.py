"""Privacy export, deletion, and provider disconnect."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import create_engine
from tests.conftest import TEST_PASSWORD, csrf_headers, register_account
from tests.test_activities import _activity_payload


def _post_activity(client: TestClient, provider_activity_id: str) -> str:
    headers = csrf_headers(client)
    created = client.post(
        "/api/v1/activities",
        json=_activity_payload(provider_activity_id),
        headers=headers,
    )
    assert created.status_code == 201
    return created.json()["id"]


def _sync(client: TestClient) -> None:
    headers = csrf_headers(client)
    response = client.post("/api/v1/activities/sync", headers=headers)
    assert response.status_code == 200


def _forbidden_export_needles() -> tuple[str, ...]:
    return (
        "password_hash",
        "token_hash",
        "SECRET_KEY",
        "pacelab_session",
        "access_token",
        "refresh_token",
    )


def test_export_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/privacy/export")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_export_is_scoped_and_omits_secrets(client: TestClient) -> None:
    register_account(client, "alpha@example.com")
    alpha_activity = _post_activity(client, "alpha-run")
    _sync(client)
    alpha_id = client.get("/api/v1/users/me").json()["id"]

    client.cookies.clear()
    register_account(client, "beta@example.com")
    beta_activity = _post_activity(client, "beta-run")
    export = client.get("/api/v1/privacy/export")
    assert export.status_code == 200
    assert "attachment" in export.headers.get("content-disposition", "").lower()
    assert "pacelab-data.json" in export.headers.get("content-disposition", "")

    body = export.json()
    raw = export.text
    for needle in _forbidden_export_needles():
        assert needle not in raw

    assert body["account"]["email"] == "beta@example.com"
    assert body["account"]["id"] != alpha_id
    assert "password_hash" not in body["account"]
    activity_ids = {item["id"] for item in body["activities"]}
    assert beta_activity in activity_ids
    assert alpha_activity not in activity_ids
    for activity in body["activities"]:
        assert "user_id" not in activity
        for sample in activity["samples"]:
            assert "latitude" not in sample
            assert "longitude" not in sample
            assert "lat" not in sample
            assert "lon" not in sample
    for connection in body["provider_connections"]:
        assert set(connection.keys()) == {"provider", "last_sync_at"}


def test_delete_running_data_keeps_account_and_other_users(client: TestClient) -> None:
    register_account(client, "alpha@example.com")
    alpha_activity = _post_activity(client, "alpha-run")
    _sync(client)

    client.cookies.clear()
    register_account(client, "beta@example.com")
    _post_activity(client, "beta-run")
    _sync(client)

    headers = csrf_headers(client)
    deleted = client.post(
        "/api/v1/privacy/running-data/delete",
        json={"password": TEST_PASSWORD},
        headers=headers,
    )
    assert deleted.status_code == 200

    listed = client.get("/api/v1/activities")
    assert listed.status_code == 200
    assert listed.json()["total"] == 0
    connections = client.get("/api/v1/privacy/connections")
    assert connections.json()["items"] == []
    me = client.get("/api/v1/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "beta@example.com"

    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["recent_activities"] == []

    client.cookies.clear()
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "alpha@example.com", "password": TEST_PASSWORD},
        headers=csrf_headers(client),
    )
    assert login.status_code == 200
    alpha_run = client.get(f"/api/v1/activities/{alpha_activity}")
    assert alpha_run.status_code == 200
    assert alpha_run.json()["id"] == alpha_activity


def test_delete_account_removes_user_and_clears_cookies(client: TestClient) -> None:
    register_account(client, "alpha@example.com")
    _post_activity(client, "alpha-run")

    client.cookies.clear()
    register_account(client, "beta@example.com")
    beta_activity = _post_activity(client, "beta-run")
    assert client.cookies.get("pacelab_session")
    assert client.cookies.get("pacelab_csrf")

    headers = csrf_headers(client)
    deleted = client.post(
        "/api/v1/privacy/account/delete",
        json={"password": TEST_PASSWORD},
        headers=headers,
    )
    assert deleted.status_code == 200
    assert not client.cookies.get("pacelab_session")
    assert not client.cookies.get("pacelab_csrf")

    me = client.get("/api/v1/users/me")
    assert me.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "beta@example.com", "password": TEST_PASSWORD},
        headers=csrf_headers(client),
    )
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "INVALID_CREDENTIALS"

    other = client.post(
        "/api/v1/auth/login",
        json={"email": "alpha@example.com", "password": TEST_PASSWORD},
        headers=csrf_headers(client),
    )
    assert other.status_code == 200
    remaining = client.get("/api/v1/activities?limit=100")
    assert beta_activity not in {item["id"] for item in remaining.json()["items"]}
    assert remaining.json()["total"] >= 1


def test_disconnect_removes_connection_not_activities(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    _post_activity(client, "keep-me")
    _sync(client)
    before = client.get("/api/v1/privacy/connections")
    assert any(item["provider"] == "mock" for item in before.json()["items"])

    headers = csrf_headers(client)
    response = client.post(
        "/api/v1/privacy/providers/mock/disconnect",
        json={"password": TEST_PASSWORD},
        headers=headers,
    )
    assert response.status_code == 200
    after = client.get("/api/v1/privacy/connections")
    assert after.json()["items"] == []
    listed = client.get("/api/v1/activities")
    assert listed.json()["total"] >= 1


def test_destructive_privacy_routes_require_csrf_and_password(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    _sync(client)

    missing_csrf = client.post(
        "/api/v1/privacy/running-data/delete",
        json={"password": TEST_PASSWORD},
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "CSRF_REQUIRED"

    headers = csrf_headers(client)
    wrong = client.post(
        "/api/v1/privacy/running-data/delete",
        json={"password": "not-the-password"},
        headers=headers,
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"

    extra_field = client.post(
        "/api/v1/privacy/account/delete",
        json={"password": TEST_PASSWORD, "user_id": "nope"},
        headers=headers,
    )
    assert extra_field.status_code == 422

    still_there = client.get("/api/v1/users/me")
    assert still_there.status_code == 200

    disconnect_wrong = client.post(
        "/api/v1/privacy/providers/mock/disconnect",
        json={"password": "not-the-password"},
        headers=headers,
    )
    assert disconnect_wrong.status_code == 401


def test_delete_running_data_does_not_leave_orphan_samples(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    _post_activity(client, "sample-run")
    headers = csrf_headers(client)
    client.post(
        "/api/v1/privacy/running-data/delete",
        json={"password": TEST_PASSWORD},
        headers=headers,
    )

    async def _count_samples() -> int:
        engine = create_engine(get_settings())
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT COUNT(*) FROM activity_samples"))
                return int(result.scalar_one())
        finally:
            await engine.dispose()

    assert asyncio.run(_count_samples()) == 0


def test_export_json_is_valid_copy_metadata(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    export = client.get("/api/v1/privacy/export")
    payload = json.loads(export.content.decode())
    exported_at = datetime.fromisoformat(payload["exported_at"].replace("Z", "+00:00"))
    assert exported_at.tzinfo is not None or exported_at.year >= 2026
    assert set(payload.keys()) == {"exported_at", "account", "activities", "provider_connections"}
