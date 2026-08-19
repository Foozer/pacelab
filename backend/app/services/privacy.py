"""Privacy operations for the signed-in user.

Identity is always the session user passed in by the caller. Routes must not
accept a client-supplied user_id.

Export JSON shape (a copy of PaceLab rows, not a Garmin Connect export):

{
  "exported_at": "<ISO-8601 datetime>",
  "account": {
    "id": "<uuid>",
    "email": "<email>",
    "email_verified": true,
    "is_active": true,
    "created_at": "<ISO-8601 datetime>",
    "updated_at": "<ISO-8601 datetime>"
  },
  "activities": [
    {
      "id": "<uuid>",
      "provider": "mock",
      "provider_activity_id": "<id>",
      "activity_type": "run",
      "started_at": "<ISO-8601 datetime>|null",
      "duration_seconds": 0,
      "distance_meters": 0.0,
      "average_speed": 0.0,
      "average_heart_rate": 0,
      "max_heart_rate": 0,
      "average_cadence": 0.0,
      "elevation_gain": 0.0,
      "calories": 0.0,
      "created_at": "<ISO-8601 datetime>",
      "updated_at": "<ISO-8601 datetime>",
      "samples": [
        {
          "timestamp": "<ISO-8601 datetime>",
          "elapsed_seconds": 0,
          "distance_meters": 0.0,
          "heart_rate": 0,
          "speed": 0.0,
          "cadence": 0.0,
          "elevation": 0.0
        }
      ]
    }
  ],
  "provider_connections": [
    {"provider": "mock", "last_sync_at": "<ISO-8601 datetime>|null"}
  ]
}

Included: public account fields, activities, samples (no GPS; none is stored),
provider name and last_sync_at.

Excluded: password_hash, auth_sessions, user_tokens (hashed email-verify and
reset tokens), CSRF and session secrets, SECRET_KEY, other users, Strava
OAuth tokens, encryption keys.

Deletion:

- Running data: this user's activities (samples cascade), provider_connections,
  and strava_connections. The account, sessions, and tokens remain.
- Account: revoke sessions, delete the user row; SQLAlchemy / FK CASCADE
  removes sessions, tokens, activities, samples, provider_connections, and
  strava_connections. Hard delete; there is no deleted_at.
- Disconnect provider: delete this user's provider_connections for that
  provider name. For `strava`, also delete strava_connections and call Strava
  token revoke. Activities are kept. This is not a Garmin disconnect.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.core.passwords import verify_password
from app.models.activity import Activity
from app.models.provider_connection import ProviderConnection
from app.models.strava_connection import StravaConnection, StravaOAuthState
from app.models.user import User
from app.schemas.activity import ActivityDetail
from app.schemas.privacy import (
    ExportAccount,
    ExportProviderConnection,
    UserDataExport,
)
from app.services import auth as auth_service

logger = logging.getLogger(__name__)


def require_current_password(user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Current password is incorrect", status_code=401)


def _connection_public(row: ProviderConnection) -> ExportProviderConnection:
    return ExportProviderConnection(provider=row.provider, last_sync_at=row.last_sync_at)


async def build_export(session: AsyncSession, user: User) -> UserDataExport:
    activities_result = await session.execute(
        select(Activity)
        .options(selectinload(Activity.samples))
        .where(Activity.user_id == user.id)
        .order_by(Activity.started_at.asc().nulls_last(), Activity.created_at.asc())
    )
    activities = activities_result.scalars().unique().all()

    connections_result = await session.execute(
        select(ProviderConnection)
        .where(ProviderConnection.user_id == user.id)
        .order_by(ProviderConnection.provider.asc())
    )
    connections = connections_result.scalars().all()

    logger.info("Assembled data export for user %s", user.id)
    return UserDataExport(
        exported_at=datetime.now(UTC),
        account=ExportAccount.model_validate(user),
        activities=[ActivityDetail.model_validate(item) for item in activities],
        provider_connections=[_connection_public(row) for row in connections],
    )


async def list_provider_connections(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[ExportProviderConnection]:
    result = await session.execute(
        select(ProviderConnection)
        .where(ProviderConnection.user_id == user_id)
        .order_by(ProviderConnection.provider.asc())
    )
    return [_connection_public(row) for row in result.scalars().all()]


async def delete_running_data(session: AsyncSession, user: User) -> None:
    """Remove activities, samples (CASCADE), provider sync rows, and Strava tokens."""
    await session.execute(delete(Activity).where(Activity.user_id == user.id))
    await session.execute(delete(ProviderConnection).where(ProviderConnection.user_id == user.id))
    await session.execute(delete(StravaOAuthState).where(StravaOAuthState.user_id == user.id))
    await session.execute(delete(StravaConnection).where(StravaConnection.user_id == user.id))
    logger.info("Deleted running data for user %s", user.id)


async def disconnect_provider(session: AsyncSession, user: User, provider: str) -> None:
    """Forget PaceLab's sync record for this provider. Does not delete activity history."""
    await session.execute(
        delete(ProviderConnection).where(
            ProviderConnection.user_id == user.id,
            ProviderConnection.provider == provider,
        )
    )
    logger.info("Disconnected provider %s for user %s", provider, user.id)


async def delete_account(session: AsyncSession, user: User) -> None:
    """Hard-delete the user. Related rows cascade. Callers must clear cookies."""
    user_id = user.id
    await auth_service.revoke_all_sessions(session, user_id)
    await session.delete(user)
    logger.info("Deleted account for user %s", user_id)
