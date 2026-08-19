"""Seed command guards. The seeded account must be usable through the API."""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr

from app.db.seed import SEED_EMAIL
from tests.conftest import csrf_headers, register_account


class _EmailCheck(BaseModel):
    email: EmailStr


def test_seed_email_passes_api_validation() -> None:
    assert _EmailCheck(email=SEED_EMAIL).email == SEED_EMAIL


def test_seed_email_can_register_and_sign_in(client: TestClient) -> None:
    created = register_account(client, SEED_EMAIL)
    assert created.status_code == 201

    headers = csrf_headers(client)
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": SEED_EMAIL, "password": "correct-horse-battery"},
        headers=headers,
    )
    assert login.status_code == 200
