"""Per-user official Strava OAuth and sync.

Tokens are encrypted with ENCRYPTION_KEY (Fernet). Identity is the PaceLab
session user. Strava athlete id is stored on strava_connections only.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.errors import AppError
from app.core.tokens import generate_token, hash_token
from app.integrations.strava.client import (
    REQUESTED_SCOPE,
    StravaApiClient,
    StravaAuthError,
    authorize_url,
)
from app.integrations.strava.provider import StravaActivityProvider
from app.models.activity import Activity
from app.models.provider_connection import ProviderConnection
from app.models.strava_connection import StravaConnection, StravaOAuthState
from app.models.user import User
from app.schemas.strava import StravaStatusResponse
from app.services.activity_sync import SyncResult, sync_user_activities

logger = logging.getLogger(__name__)

OAUTH_STATE_TTL = timedelta(minutes=10)
TOKEN_REFRESH_SKEW = timedelta(minutes=10)
FIRST_SYNC_WINDOW = timedelta(days=90)
STATUS_CONNECTED = "connected"
STATUS_NEEDS_RECONNECT = "needs_reconnect"


def require_strava_connect_ready(settings: Settings) -> None:
    if not settings.strava_client_configured:
        raise AppError(
            "STRAVA_NOT_CONFIGURED",
            "Strava is not configured on this server.",
            status_code=501,
        )
    if not settings.encryption_key.strip():
        raise AppError(
            "ENCRYPTION_UNAVAILABLE",
            "Strava cannot be connected until ENCRYPTION_KEY is set so tokens can be encrypted.",
            status_code=501,
        )


async def strava_status(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    settings: Settings,
) -> StravaStatusResponse:
    connection = await _get_connection(session, user_id)
    last_sync = await _strava_last_sync(session, user_id)
    return StravaStatusResponse(
        configured=settings.strava_client_configured and bool(settings.encryption_key.strip()),
        connected=connection is not None,
        needs_reconnect=connection is not None and connection.status == STATUS_NEEDS_RECONNECT,
        last_sync_at=last_sync,
    )


async def start_connect(session: AsyncSession, *, user: User, settings: Settings) -> str:
    require_strava_connect_ready(settings)
    raw_state = generate_token()
    expires_at = datetime.now(UTC) + OAUTH_STATE_TTL
    session.add(
        StravaOAuthState(
            user_id=user.id,
            state_hash=hash_token(raw_state),
            expires_at=expires_at,
        )
    )
    await session.flush()
    await session.commit()
    logger.info("Started Strava OAuth for user %s", user.id)
    return authorize_url(
        client_id=settings.strava_client_id,
        redirect_uri=settings.strava_redirect_uri,
        state=raw_state,
    )


async def complete_callback(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    client: StravaApiClient,
    code: str | None,
    state: str | None,
    error: str | None,
    scope: str | None,
) -> None:
    require_strava_connect_ready(settings)
    if error:
        raise AppError(
            "STRAVA_OAUTH_DENIED",
            "Strava access was not granted.",
            status_code=400,
        )
    if not code or not state:
        raise AppError(
            "STRAVA_OAUTH_STATE_INVALID",
            "Strava callback was missing code or state.",
            status_code=400,
        )
    await _consume_oauth_state(session, user_id=user.id, raw_state=state)
    token_payload = await client.exchange_code(code)
    await _persist_tokens(
        session,
        user=user,
        settings=settings,
        token_payload=token_payload,
        granted_scope=scope or _scope_from_payload(token_payload),
    )
    logger.info("Stored Strava connection for user %s", user.id)


async def sync_strava_activities(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    client: StravaApiClient,
) -> SyncResult:
    require_strava_connect_ready(settings)
    connection = await _get_connection(session, user.id)
    if connection is None:
        raise AppError(
            "STRAVA_NOT_CONNECTED",
            "Connect Strava in Settings before syncing.",
            status_code=409,
        )
    if connection.status == STATUS_NEEDS_RECONNECT:
        raise AppError(
            "STRAVA_NEEDS_RECONNECT",
            "Strava access expired. Connect Strava again in Settings.",
            status_code=409,
        )
    access_token = await _access_token_for_api(session, connection, settings, client)
    after = await _sync_after(session, user.id)

    async def mark_reconnect() -> None:
        await _mark_reconnect(session, connection)

    provider = StravaActivityProvider(
        client,
        access_token=access_token,
        after=after,
        on_auth_failure=mark_reconnect,
    )
    try:
        return await sync_user_activities(session, user_id=user.id, provider=provider)
    except StravaAuthError:
        await _mark_reconnect(session, connection)
        raise AppError(
            "STRAVA_NEEDS_RECONNECT",
            "Strava access expired. Connect Strava again in Settings.",
            status_code=409,
        ) from None


async def disconnect_strava(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    client: StravaApiClient,
) -> None:
    connection = await _get_connection(session, user.id)
    can_revoke = bool(
        connection is not None
        and settings.strava_client_configured
        and settings.encryption_key.strip()
    )
    if connection is not None and can_revoke:
        try:
            refresh_token = decrypt_secret(
                settings.encryption_key, connection.refresh_token_encrypted
            )
            await client.revoke_token(refresh_token)
        except AppError:
            logger.info("Strava revoke failed for user %s; dropping local connection", user.id)
    await session.execute(delete(StravaConnection).where(StravaConnection.user_id == user.id))
    await session.execute(
        delete(ProviderConnection).where(
            ProviderConnection.user_id == user.id,
            ProviderConnection.provider == "strava",
        )
    )
    await session.execute(delete(StravaOAuthState).where(StravaOAuthState.user_id == user.id))
    logger.info("Disconnected Strava for user %s (activities kept)", user.id)


def settings_redirect(settings: Settings, *, result: str) -> str:
    query = urlencode({"strava": result})
    return f"{settings.frontend_url.rstrip('/')}/settings/connected-services?{query}"


async def _consume_oauth_state(
    session: AsyncSession, *, user_id: uuid.UUID, raw_state: str
) -> None:
    now = datetime.now(UTC)
    result = await session.execute(
        select(StravaOAuthState).where(
            StravaOAuthState.user_id == user_id,
            StravaOAuthState.state_hash == hash_token(raw_state),
            StravaOAuthState.expires_at > now,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise AppError(
            "STRAVA_OAUTH_STATE_INVALID",
            "Strava callback state was missing or invalid.",
            status_code=400,
        )
    await session.delete(row)
    await session.flush()


async def _persist_tokens(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    token_payload: dict[str, Any],
    granted_scope: str,
) -> None:
    access, refresh, expires_at_raw = _require_token_fields(token_payload, kind="token")
    if not _scope_allows_activities(granted_scope):
        raise AppError(
            "STRAVA_OAUTH_DENIED",
            "PaceLab needs permission to read your Strava activities.",
            status_code=400,
        )
    athlete = token_payload.get("athlete")
    athlete_id = ""
    if isinstance(athlete, dict) and athlete.get("id") is not None:
        athlete_id = str(athlete["id"])
    expires_at = datetime.fromtimestamp(expires_at_raw, tz=UTC)
    existing_result = await session.execute(
        select(StravaConnection).where(StravaConnection.user_id == user.id)
    )
    existing = existing_result.scalar_one_or_none()
    encrypted_access = encrypt_secret(settings.encryption_key, access)
    encrypted_refresh = encrypt_secret(settings.encryption_key, refresh)
    if existing is None:
        session.add(
            StravaConnection(
                user_id=user.id,
                provider_athlete_id=athlete_id or "unknown",
                access_token_encrypted=encrypted_access,
                refresh_token_encrypted=encrypted_refresh,
                token_expires_at=expires_at,
                scopes=granted_scope[:255],
                status=STATUS_CONNECTED,
                connected_at=datetime.now(UTC),
            )
        )
    else:
        existing.provider_athlete_id = athlete_id or existing.provider_athlete_id
        existing.access_token_encrypted = encrypted_access
        existing.refresh_token_encrypted = encrypted_refresh
        existing.token_expires_at = expires_at
        existing.scopes = granted_scope[:255]
        existing.status = STATUS_CONNECTED
        existing.updated_at = datetime.now(UTC)


def _require_token_fields(payload: dict[str, Any], *, kind: str) -> tuple[str, str, int]:
    access = payload.get("access_token")
    refresh = payload.get("refresh_token")
    expires_at_raw = payload.get("expires_at")
    if (
        not isinstance(access, str)
        or not isinstance(refresh, str)
        or not isinstance(expires_at_raw, int)
    ):
        raise AppError(
            "STRAVA_UNAVAILABLE",
            f"Strava {kind} response was incomplete.",
            status_code=502,
        )
    return access, refresh, expires_at_raw


def _scope_from_payload(payload: dict[str, Any]) -> str:
    scope = payload.get("scope")
    if isinstance(scope, str) and scope:
        return scope
    return REQUESTED_SCOPE


def _scope_allows_activities(scope: str) -> bool:
    parts = {
        item.strip()
        for item in scope.replace("+", ",").replace(" ", ",").split(",")
        if item.strip()
    }
    return "activity:read_all" in parts or "activity:read" in parts


async def _access_token_for_api(
    session: AsyncSession,
    connection: StravaConnection,
    settings: Settings,
    client: StravaApiClient,
) -> str:
    access = decrypt_secret(settings.encryption_key, connection.access_token_encrypted)
    refresh = decrypt_secret(settings.encryption_key, connection.refresh_token_encrypted)
    if connection.token_expires_at - datetime.now(UTC) > TOKEN_REFRESH_SKEW:
        return access
    try:
        payload = await client.refresh_token(refresh)
    except StravaAuthError:
        connection.status = STATUS_NEEDS_RECONNECT
        raise AppError(
            "STRAVA_NEEDS_RECONNECT",
            "Strava access expired. Connect Strava again in Settings.",
            status_code=409,
        ) from None
    new_access, new_refresh, expires_at_raw = _require_token_fields(
        payload, kind="refresh"
    )
    connection.access_token_encrypted = encrypt_secret(settings.encryption_key, new_access)
    connection.refresh_token_encrypted = encrypt_secret(settings.encryption_key, new_refresh)
    connection.token_expires_at = datetime.fromtimestamp(expires_at_raw, tz=UTC)
    connection.updated_at = datetime.now(UTC)
    await session.flush()
    return new_access


async def _mark_reconnect(session: AsyncSession, connection: StravaConnection) -> None:
    connection.status = STATUS_NEEDS_RECONNECT
    connection.updated_at = datetime.now(UTC)
    await session.flush()


async def _get_connection(session: AsyncSession, user_id: uuid.UUID) -> StravaConnection | None:
    result = await session.execute(
        select(StravaConnection).where(StravaConnection.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _strava_last_sync(session: AsyncSession, user_id: uuid.UUID) -> datetime | None:
    result = await session.execute(
        select(ProviderConnection.last_sync_at).where(
            ProviderConnection.user_id == user_id,
            ProviderConnection.provider == "strava",
        )
    )
    return result.scalar_one_or_none()


async def _sync_after(session: AsyncSession, user_id: uuid.UUID) -> datetime:
    last_sync = await _strava_last_sync(session, user_id)
    newest = await session.execute(
        select(func.max(Activity.started_at)).where(
            Activity.user_id == user_id,
            Activity.provider == "strava",
        )
    )
    newest_started = newest.scalar_one_or_none()
    candidates = [value for value in (last_sync, newest_started) if value is not None]
    if candidates:
        return max(candidates)
    return datetime.now(UTC) - FIRST_SYNC_WINDOW
