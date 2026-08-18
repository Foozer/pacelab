"""Configuration validation tests. These do not require PostgreSQL."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_database_url_must_use_asyncpg() -> None:
    with pytest.raises(ValidationError):
        Settings(
            secret_key="a-sufficiently-long-secret",
            database_url="postgresql://pacelab:pacelab@localhost:5432/pacelab",
        )


def test_production_rejects_placeholder_secret() -> None:
    settings = Settings(
        secret_key="change-me-to-a-long-random-string-please",
        database_url="postgresql+asyncpg://pacelab:pacelab@localhost:5432/pacelab",
        environment="production",
        debug=False,
    )
    with pytest.raises(ValueError, match="SECRET_KEY"):
        settings.validate_for_environment()


def test_production_rejects_debug() -> None:
    settings = Settings(
        secret_key="this-is-a-long-enough-production-secret-key",
        database_url="postgresql+asyncpg://pacelab:pacelab@localhost:5432/pacelab",
        environment="production",
        debug=True,
    )
    with pytest.raises(ValueError, match="DEBUG"):
        settings.validate_for_environment()


def test_cors_origins_come_from_frontend_url() -> None:
    settings = Settings(
        secret_key="a-sufficiently-long-secret",
        database_url="postgresql+asyncpg://pacelab:pacelab@localhost:5432/pacelab",
        frontend_url="http://localhost:5173/",
    )
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
