"""Idempotent import of activities from the configured provider.

Duplicates are prevented by UNIQUE (user_id, provider, provider_activity_id).
There is no background worker: callers invoke this from the API or seed command.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.integrations.exceptions import ProviderNotConfiguredError
from app.integrations.protocol import ActivityProvider
from app.models.activity import Activity
from app.models.provider_connection import ProviderConnection
from app.services.activities import (
    activity_from_provider,
    apply_provider_summary,
    replace_provider_samples,
)

logger = logging.getLogger(__name__)


class SyncResult:
    def __init__(self, provider: str, created: int, updated: int, last_sync_at: datetime) -> None:
        self.provider = provider
        self.created = created
        self.updated = updated
        self.last_sync_at = last_sync_at

    @property
    def total(self) -> int:
        return self.created + self.updated


async def sync_user_activities(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: ActivityProvider,
) -> SyncResult:
    try:
        incoming = await provider.sync_activities(user_id)
    except ProviderNotConfiguredError as exc:
        raise AppError("PROVIDER_NOT_CONFIGURED", exc.message, status_code=501) from exc

    existing_rows = await session.execute(
        select(Activity)
        .options(selectinload(Activity.samples))
        .where(Activity.user_id == user_id, Activity.provider == provider.provider_name)
    )
    by_provider_id = {row.provider_activity_id: row for row in existing_rows.scalars().all()}

    created = 0
    updated = 0
    for item in incoming:
        existing = by_provider_id.get(item.provider_activity_id)
        if existing is None:
            session.add(activity_from_provider(user_id=user_id, incoming=item))
            created += 1
        else:
            apply_provider_summary(existing, item)
            await replace_provider_samples(session, existing, item)
            updated += 1

    last_sync_at = await _record_sync(
        session,
        user_id=user_id,
        provider_name=provider.provider_name,
    )
    await session.flush()
    logger.info(
        "Synced activities for user %s from %s: created=%s updated=%s",
        user_id,
        provider.provider_name,
        created,
        updated,
    )
    return SyncResult(
        provider=provider.provider_name,
        created=created,
        updated=updated,
        last_sync_at=last_sync_at,
    )


async def _record_sync(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider_name: str,
) -> datetime:
    now = datetime.now(UTC)
    result = await session.execute(
        select(ProviderConnection).where(
            ProviderConnection.user_id == user_id,
            ProviderConnection.provider == provider_name,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = ProviderConnection(
            user_id=user_id,
            provider=provider_name,
            last_sync_at=now,
        )
        session.add(connection)
    else:
        connection.last_sync_at = now
        connection.updated_at = now
    return now
