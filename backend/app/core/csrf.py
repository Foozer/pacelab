"""Double-submit CSRF protection for cookie-authenticated mutating requests."""

from __future__ import annotations

import secrets
from collections.abc import Awaitable, Callable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import CSRF_COOKIE_NAME, CSRF_HEADER_NAME

_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _tokens_match(cookie: str | None, header: str | None) -> bool:
    if not cookie or not header:
        return False
    if len(cookie) != len(header):
        return False
    return secrets.compare_digest(cookie, header)


def _csrf_error(code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": {"code": code, "message": message}},
    )


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in _UNSAFE_METHODS and request.url.path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin:
                allowed = {item.rstrip("/") for item in request.app.state.settings.cors_origins}
                if origin.rstrip("/") not in allowed:
                    return _csrf_error("CSRF_INVALID", "Request origin is not allowed")
            cookie = request.cookies.get(CSRF_COOKIE_NAME)
            header = request.headers.get(CSRF_HEADER_NAME)
            if not cookie or not header:
                return _csrf_error(
                    "CSRF_REQUIRED",
                    "A CSRF token is required. Fetch /api/v1/auth/csrf first.",
                )
            if not _tokens_match(cookie, header):
                return _csrf_error("CSRF_INVALID", "CSRF token was missing or invalid")

        return await call_next(request)
