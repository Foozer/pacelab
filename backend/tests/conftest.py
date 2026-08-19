"""Pytest fixtures. Environment is configured before the app is imported."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import text

os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://pacelab:change-me-dev-only@localhost:5432/pacelab",
)
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.core.config import get_settings  # noqa: E402
from app.db.session import create_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.services.email import RecordingEmailSender  # noqa: E402

get_settings.cache_clear()

TEST_PASSWORD = "correct-horse-battery"


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")


@pytest.fixture
def app() -> FastAPI:
    get_settings.cache_clear()
    return create_app(get_settings())


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
    _truncate_auth_tables()


def _truncate_auth_tables() -> None:
    async def _wipe() -> None:
        engine = create_engine(get_settings())
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    text(
                        "TRUNCATE TABLE activity_samples, activities, strava_oauth_states, "
                        "strava_connections, provider_connections, "
                        "user_tokens, auth_sessions, users RESTART IDENTITY CASCADE"
                    )
                )
        finally:
            await engine.dispose()

    asyncio.run(_wipe())


def csrf_headers(client: TestClient) -> dict[str, str]:
    response = client.get("/api/v1/auth/csrf")
    response.raise_for_status()
    token = response.json()["csrf_token"]
    return {"X-CSRF-Token": token}


def register_account(
    client: TestClient,
    email: str,
    password: str = TEST_PASSWORD,
) -> Response:
    headers = csrf_headers(client)
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
        headers=headers,
    )


def recording_sender(app: FastAPI) -> RecordingEmailSender:
    sender = app.state.email_sender
    assert isinstance(sender, RecordingEmailSender)
    return sender
