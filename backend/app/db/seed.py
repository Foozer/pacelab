"""Development-only seed: local user + mock running activities.

Usage (from backend/):

    python -m app.db.seed

Refuses to run when ENVIRONMENT=production. Does not store Garmin credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.db.session import create_engine, create_session_factory
from app.integrations.mock import MockActivityProvider
from app.models.user import User
from app.services.activity_sync import sync_user_activities
from app.services.auth import get_user_by_email, normalize_email

# Must satisfy Pydantic EmailStr so the seeded account can sign in through the
# API. Reserved suffixes such as .local are rejected by email-validator.
SEED_EMAIL = "dev@example.com"
DEFAULT_SEED_PASSWORD = "pacelab-dev-local-only"


async def seed(*, email: str, password: str) -> None:
    settings = get_settings()
    if settings.is_production:
        raise SystemExit("Refusing to seed when ENVIRONMENT=production")

    engine = create_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            user = await _get_or_create_user(session, email=email, password=password)
            result = await sync_user_activities(
                session,
                user_id=user.id,
                provider=MockActivityProvider(),
            )
            await session.commit()
        print(f"Seed user: {email}")
        print(
            f"Mock sync ({result.provider}): created={result.created} "
            f"updated={result.updated} total={result.total}"
        )
        print("Sign in with the seed password documented in README.md (never logged here).")
    finally:
        await engine.dispose()


async def _get_or_create_user(session: AsyncSession, *, email: str, password: str) -> User:
    normalized = normalize_email(email)
    existing = await get_user_by_email(session, normalized)
    if existing is not None:
        print("Seed user already exists; password was not changed.")
        return existing

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        email_verified=True,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    print("Created seed user.")
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a local PaceLab user with mock activities")
    parser.add_argument(
        "--email",
        default=os.environ.get("PACELAB_SEED_EMAIL", SEED_EMAIL),
        help=f"Account email (default: {SEED_EMAIL})",
    )
    args = parser.parse_args()
    password = os.environ.get("PACELAB_SEED_PASSWORD", DEFAULT_SEED_PASSWORD)
    try:
        asyncio.run(seed(email=args.email, password=password))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
