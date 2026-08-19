"""Official Strava HTTP client.

URLs are from https://developers.strava.com/docs/authentication/ and
https://developers.strava.com/docs/reference/. Timeouts are required. This
module must not log tokens, codes, or raw activity payloads.

Rate limits (published default, per application): 200 requests / 15 minutes and
2,000 / day overall; 100 / 15 minutes and 1,000 / day for non-upload endpoints
(including activity streams). First sync is bounded (see provider).
"""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import Settings
from app.core.errors import AppError
from app.integrations.strava.mapping import STREAM_KEYS

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://www.strava.com/oauth/token"  # noqa: S105
REVOKE_URL = "https://www.strava.com/oauth/revoke"
API_BASE = "https://www.strava.com/api/v3"

# Minimum read scope for “Only You” training data.
REQUESTED_SCOPE = "activity:read_all"

HTTP_TIMEOUT = httpx.Timeout(15.0, read=30.0)


class StravaAuthError(AppError):
    def __init__(self, message: str, *, status_code: int = 401) -> None:
        super().__init__("STRAVA_AUTH_FAILED", message, status_code=status_code)


class StravaHttpError(AppError):
    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__("STRAVA_UNAVAILABLE", message, status_code=status_code)


def authorize_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "approval_prompt": "auto",
            "scope": REQUESTED_SCOPE,
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


class StravaApiClient:
    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=HTTP_TIMEOUT, transport=self._transport)

    async def exchange_code(self, code: str) -> dict[str, Any]:
        payload = {
            "client_id": self._settings.strava_client_id,
            "client_secret": self._settings.strava_client_secret,
            "code": code,
            "grant_type": "authorization_code",
        }
        return await self._post_form(OAUTH_TOKEN_URL, data=payload)

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        payload = {
            "client_id": self._settings.strava_client_id,
            "client_secret": self._settings.strava_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        return await self._post_form(OAUTH_TOKEN_URL, data=payload)

    async def revoke_token(self, token: str) -> None:
        credentials = f"{self._settings.strava_client_id}:{self._settings.strava_client_secret}"
        basic = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        async with self._client() as client:
            response = await client.post(
                REVOKE_URL,
                headers={
                    "Authorization": f"Basic {basic}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"token": token, "token_type_hint": "refresh_token"},
            )
        if response.status_code >= 500:
            raise StravaHttpError(
                "Strava could not revoke access. Try disconnecting again shortly.",
                status_code=503,
            )
        if response.status_code not in {200, 204}:
            raise StravaHttpError(
                "Strava rejected the disconnect request.",
                status_code=502,
            )

    async def list_athlete_activities(
        self,
        access_token: str,
        *,
        after: datetime | None,
        page: int,
        per_page: int,
    ) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {"page": page, "per_page": per_page}
        if after is not None:
            params["after"] = int(after.timestamp())
        payload = await self._get_json(
            f"{API_BASE}/athlete/activities",
            access_token=access_token,
            params=params,
        )
        if not isinstance(payload, list):
            raise StravaHttpError("Strava returned an unexpected activity list.")
        return [item for item in payload if isinstance(item, dict)]

    async def get_activity_streams(
        self,
        access_token: str,
        activity_id: str,
    ) -> dict[str, Any]:
        keys = ",".join(STREAM_KEYS)
        payload = await self._get_json(
            f"{API_BASE}/activities/{activity_id}/streams",
            access_token=access_token,
            params={"keys": keys, "key_by_type": "true"},
            allow_404=True,
        )
        if payload is None:
            return {}
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            as_dict: dict[str, Any] = {}
            for item in payload:
                if isinstance(item, dict) and isinstance(item.get("type"), str):
                    as_dict[item["type"]] = item
            return as_dict
        return {}

    async def _post_form(self, url: str, *, data: dict[str, str]) -> dict[str, Any]:
        async with self._client() as client:
            response = await client.post(url, data=data)
        return self._read_object(response, form_post=True)

    async def _get_json(
        self,
        url: str,
        *,
        access_token: str,
        params: dict[str, str | int],
        allow_404: bool = False,
    ) -> Any:
        async with self._client() as client:
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
        if allow_404 and response.status_code == 404:
            return None
        if response.status_code == 401:
            raise StravaAuthError("Strava rejected the access token.")
        if response.status_code == 403:
            raise StravaAuthError("Strava denied access to this resource.", status_code=403)
        if response.status_code == 429:
            raise AppError(
                "STRAVA_RATE_LIMITED",
                "Strava rate limit reached. Wait and sync again.",
                status_code=429,
            )
        if response.status_code >= 400:
            raise StravaHttpError("Strava request failed.")
        try:
            return response.json()
        except ValueError as exc:
            raise StravaHttpError("Strava returned a non-JSON body.") from exc

    def _read_object(self, response: httpx.Response, *, form_post: bool) -> dict[str, Any]:
        del form_post
        if response.status_code == 401:
            raise StravaAuthError("Strava rejected the token request.")
        if response.status_code >= 400:
            raise StravaHttpError("Strava token request failed.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise StravaHttpError("Strava returned a non-JSON body.") from exc
        if not isinstance(payload, dict):
            raise StravaHttpError("Strava returned an unexpected token payload.")
        return payload
