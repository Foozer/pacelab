"""Current-user account tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD, csrf_headers, register_account


def test_change_password_keeps_current_session(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    response = client.post(
        "/api/v1/users/me/password",
        json={"current_password": TEST_PASSWORD, "new_password": "new-horse-battery"},
        headers=headers,
    )
    assert response.status_code == 200
    me = client.get("/api/v1/users/me")
    assert me.status_code == 200

    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 200
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "runner@example.com", "password": "new-horse-battery"},
        headers=headers,
    )
    assert login.status_code == 200


def test_change_password_rejects_wrong_current(client: TestClient) -> None:
    register_account(client, "runner@example.com")
    headers = csrf_headers(client)
    response = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "not-the-password", "new_password": "new-horse-battery"},
        headers=headers,
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
