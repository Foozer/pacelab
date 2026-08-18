"""Authentication API tests."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD, csrf_headers, recording_sender, register_account


def test_register_creates_user_and_session(client: TestClient) -> None:
    response = register_account(client, "runner@example.com")
    assert response.status_code == 201
    payload = response.json()
    assert payload["email"] == "runner@example.com"
    assert payload["email_verified"] is False
    assert payload["is_active"] is True
    assert "password_hash" not in payload
    assert "password" not in payload
    assert client.cookies.get("pacelab_session")


def test_register_duplicate_email_rejected(client: TestClient) -> None:
    first = register_account(client, "runner@example.com")
    assert first.status_code == 201
    second = register_account(client, "Runner@example.com")
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_without_csrf_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "runner@example.com", "password": TEST_PASSWORD},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_REQUIRED"


def test_login_success_and_invalid_password(client: TestClient) -> None:
    created = register_account(client, "runner@example.com")
    assert created.status_code == 201

    logout_headers = csrf_headers(client)
    client.post("/api/v1/auth/logout", headers=logout_headers)

    headers = csrf_headers(client)
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "runner@example.com", "password": "wrong-password"},
        headers=headers,
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "INVALID_CREDENTIALS"

    good = client.post(
        "/api/v1/auth/login",
        json={"email": "runner@example.com", "password": TEST_PASSWORD},
        headers=headers,
    )
    assert good.status_code == 200
    assert good.json()["email"] == "runner@example.com"


def test_unauthenticated_me_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_current_user_matches_session(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    response = client.get("/api/v1/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == "runner@example.com"


def test_users_are_isolated_by_session(client: TestClient) -> None:
    register_account(client, "alpha@example.com")
    session_a = client.cookies.get("pacelab_session")
    assert session_a
    me_a = client.get("/api/v1/users/me")
    assert me_a.status_code == 200

    client.cookies.clear()
    register_account(client, "beta@example.com")
    me_b = client.get("/api/v1/users/me")
    assert me_b.status_code == 200
    assert me_b.json()["email"] == "beta@example.com"
    assert me_a.json()["id"] != me_b.json()["id"]

    client.cookies.clear()
    client.cookies.set("pacelab_session", session_a)
    me_a_again = client.get("/api/v1/users/me")
    assert me_a_again.status_code == 200
    assert me_a_again.json()["email"] == "alpha@example.com"
    assert me_a_again.json()["id"] == me_a.json()["id"]


def test_logout_revokes_session(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    me = client.get("/api/v1/users/me")
    assert me.status_code == 401


def test_email_verification_flow(client: TestClient, app: FastAPI) -> None:
    register_account(client, "runner@example.com")
    sender = recording_sender(app)
    assert sender.outbox
    token = sender.outbox[-1].token
    headers = csrf_headers(client)
    verify = client.post(
        "/api/v1/auth/email/verify",
        json={"token": token},
        headers=headers,
    )
    assert verify.status_code == 200
    assert verify.json()["email_verified"] is True


def test_password_reset_flow(client: TestClient, app: FastAPI) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    request_reset = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "runner@example.com"},
        headers=headers,
    )
    assert request_reset.status_code == 200
    sender = recording_sender(app)
    reset_messages = [item for item in sender.outbox if item.template == "password_reset"]
    assert reset_messages
    token = reset_messages[-1].token

    confirm = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "password": "new-horse-battery"},
        headers=headers,
    )
    assert confirm.status_code == 200

    me = client.get("/api/v1/users/me")
    assert me.status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "runner@example.com", "password": "new-horse-battery"},
        headers=headers,
    )
    assert login.status_code == 200


def test_password_reset_unknown_email_is_generic(client: TestClient) -> None:
    headers = csrf_headers(client)
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "missing@example.com"},
        headers=headers,
    )
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]


def test_short_password_rejected(client: TestClient) -> None:
    headers = csrf_headers(client)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "runner@example.com", "password": "short"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
