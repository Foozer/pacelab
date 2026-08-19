"""Cookie and session security helpers.

Session cookies are HttpOnly. CSRF cookies are readable by JavaScript so the
frontend can send a matching X-CSRF-Token header (double-submit).
"""

from __future__ import annotations

from typing import Final

from fastapi import Response

from app.core.config import Settings

SESSION_COOKIE_NAME: Final = "pacelab_session"
CSRF_COOKIE_NAME: Final = "pacelab_csrf"
CSRF_HEADER_NAME: Final = "X-CSRF-Token"

SESSION_TTL_SECONDS: Final = 60 * 60 * 24 * 14  # 14 days
EMAIL_VERIFICATION_TTL_SECONDS: Final = 60 * 60 * 24
PASSWORD_RESET_TTL_SECONDS: Final = 60 * 60


def set_session_cookie(response: Response, raw_token: str, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def clear_csrf_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )


def set_csrf_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
