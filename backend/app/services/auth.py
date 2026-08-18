"""Authentication and account services.

Current user identity always comes from a server-side session, never from a
client-supplied user_id. Garmin OAuth (later) will attach to this same user.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import AppError
from app.core.passwords import dummy_password_hash, hash_password, needs_rehash, verify_password
from app.core.security import (
    EMAIL_VERIFICATION_TTL_SECONDS,
    PASSWORD_RESET_TTL_SECONDS,
    SESSION_TTL_SECONDS,
)
from app.core.tokens import generate_token, hash_token
from app.models.auth_session import AuthSession
from app.models.user import User
from app.models.user_token import TokenPurpose, UserToken
from app.services.email import (
    EmailSender,
    password_reset_email,
    verification_email,
)

logger = logging.getLogger(__name__)

_DUMMY_HASH: str | None = None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = dummy_password_hash()
    return _DUMMY_HASH


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


async def register_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    settings: Settings,
    email_sender: EmailSender,
) -> tuple[User, str]:
    normalized = normalize_email(email)
    existing = await get_user_by_email(session, normalized)
    if existing is not None:
        raise AppError(
            "EMAIL_ALREADY_REGISTERED",
            "An account with this email already exists",
            status_code=409,
        )

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        email_verified=False,
        is_active=True,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError(
            "EMAIL_ALREADY_REGISTERED",
            "An account with this email already exists",
            status_code=409,
        ) from exc

    await issue_email_verification(session, user=user, settings=settings, email_sender=email_sender)
    raw_session = await create_session(session, user)
    logger.info("Registered user %s", user.id)
    return user, raw_session


async def authenticate_user(session: AsyncSession, *, email: str, password: str) -> User:
    user = await get_user_by_email(session, email)
    password_hash = user.password_hash if user is not None else _dummy_hash()
    password_ok = verify_password(password, password_hash)
    if user is None or not password_ok:
        raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect", status_code=401)
    if not user.is_active:
        raise AppError("ACCOUNT_DISABLED", "This account is disabled", status_code=403)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


async def create_session(session: AsyncSession, user: User) -> str:
    raw_token = generate_token()
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS),
    )
    session.add(auth_session)
    await session.flush()
    return raw_token


async def get_user_for_session_token(session: AsyncSession, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    result = await session.execute(
        select(AuthSession)
        .options(selectinload(AuthSession.user))
        .where(AuthSession.token_hash == hash_token(raw_token))
    )
    auth_session = result.scalar_one_or_none()
    if auth_session is None:
        return None
    if auth_session.expires_at <= datetime.now(UTC):
        await session.delete(auth_session)
        return None
    return auth_session.user


async def revoke_session(session: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    await session.execute(
        delete(AuthSession).where(AuthSession.token_hash == hash_token(raw_token))
    )


async def revoke_all_sessions(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))


async def _replace_token(
    session: AsyncSession,
    *,
    user: User,
    purpose: TokenPurpose,
    ttl_seconds: int,
) -> str:
    await session.execute(
        delete(UserToken).where(
            UserToken.user_id == user.id,
            UserToken.purpose == purpose,
            UserToken.used_at.is_(None),
        )
    )
    raw_token = generate_token()
    session.add(
        UserToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
    )
    await session.flush()
    return raw_token


async def issue_email_verification(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    email_sender: EmailSender,
) -> None:
    if user.email_verified:
        return
    raw_token = await _replace_token(
        session,
        user=user,
        purpose=TokenPurpose.EMAIL_VERIFICATION,
        ttl_seconds=EMAIL_VERIFICATION_TTL_SECONDS,
    )
    await email_sender.send(verification_email(user.email, settings.frontend_url, raw_token))


async def verify_email_token(session: AsyncSession, raw_token: str) -> User:
    user_token = await _consume_token(session, raw_token, TokenPurpose.EMAIL_VERIFICATION)
    user = await session.get(User, user_token.user_id)
    if user is None or not user.is_active:
        raise AppError("EMAIL_TOKEN_INVALID", "This verification link is invalid", status_code=400)
    user.email_verified = True
    return user


async def request_password_reset(
    session: AsyncSession,
    *,
    email: str,
    settings: Settings,
    email_sender: EmailSender,
) -> None:
    user = await get_user_by_email(session, email)
    if user is None or not user.is_active:
        logger.info("Password reset requested for unknown or inactive account")
        return
    raw_token = await _replace_token(
        session,
        user=user,
        purpose=TokenPurpose.PASSWORD_RESET,
        ttl_seconds=PASSWORD_RESET_TTL_SECONDS,
    )
    await email_sender.send(password_reset_email(user.email, settings.frontend_url, raw_token))
    logger.info("Queued password reset for user %s", user.id)


async def confirm_password_reset(session: AsyncSession, *, raw_token: str, password: str) -> User:
    user_token = await _consume_token(session, raw_token, TokenPurpose.PASSWORD_RESET)
    user = await session.get(User, user_token.user_id)
    if user is None or not user.is_active:
        raise AppError(
            "PASSWORD_RESET_TOKEN_INVALID",
            "This password reset link is invalid",
            status_code=400,
        )
    user.password_hash = hash_password(password)
    await revoke_all_sessions(session, user.id)
    logger.info("Password reset completed for user %s", user.id)
    return user


async def change_password(
    session: AsyncSession,
    *,
    user: User,
    current_password: str,
    new_password: str,
    current_session_token: str | None,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Current password is incorrect", status_code=401)
    user.password_hash = hash_password(new_password)
    await revoke_all_sessions(session, user.id)
    if current_session_token:
        session.add(
            AuthSession(
                user_id=user.id,
                token_hash=hash_token(current_session_token),
                expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS),
            )
        )
    logger.info("Password changed for user %s", user.id)


async def _consume_token(
    session: AsyncSession,
    raw_token: str,
    purpose: TokenPurpose,
) -> UserToken:
    result = await session.execute(
        select(UserToken).where(
            UserToken.token_hash == hash_token(raw_token),
            UserToken.purpose == purpose,
        )
    )
    user_token = result.scalar_one_or_none()
    now = datetime.now(UTC)
    invalid_code = (
        "EMAIL_TOKEN_INVALID"
        if purpose is TokenPurpose.EMAIL_VERIFICATION
        else "PASSWORD_RESET_TOKEN_INVALID"
    )
    invalid_message = (
        "This verification link is invalid or has expired"
        if purpose is TokenPurpose.EMAIL_VERIFICATION
        else "This password reset link is invalid or has expired"
    )
    if user_token is None or user_token.used_at is not None or user_token.expires_at <= now:
        raise AppError(invalid_code, invalid_message, status_code=400)
    user_token.used_at = now
    return user_token
