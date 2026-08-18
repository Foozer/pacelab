"""FastAPI dependencies. Current user always comes from the session cookie."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import SESSION_COOKIE_NAME
from app.db.session import get_db
from app.models.user import User
from app.services.auth import get_user_for_session_token
from app.services.email import EmailSender, RecordingEmailSender


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    user = await get_user_for_session_token(db, raw_token)
    if user is None:
        raise AppError("UNAUTHENTICATED", "Authentication required", status_code=401)
    if not user.is_active:
        raise AppError("ACCOUNT_DISABLED", "This account is disabled", status_code=403)
    return user


def get_email_sender(request: Request) -> EmailSender:
    sender: EmailSender = request.app.state.email_sender
    return sender


def get_recording_email_sender(request: Request) -> RecordingEmailSender:
    sender = request.app.state.email_sender
    if not isinstance(sender, RecordingEmailSender):
        raise AppError("NOT_FOUND", "Not Found", status_code=404)
    return sender


def enforce_rate_limit(request: Request, action: str, *, limit: int, window_seconds: int) -> None:
    settings = request.app.state.settings
    if settings.environment == "test":
        return
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    host = request.client.host if request.client is not None else "unknown"
    if not limiter.allow(f"{action}:{host}", limit=limit, window_seconds=window_seconds):
        raise AppError(
            "RATE_LIMITED",
            "Too many attempts. Please wait and try again.",
            status_code=429,
        )
