"""Activity persistence. Current user is always supplied by the caller from the session."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError
from app.integrations.protocol import ProviderActivity, ProviderActivitySample
from app.models.activity import Activity, ActivitySample
from app.models.provider_connection import ProviderConnection
from app.schemas.activity import ActivityCreate, ActivitySampleCreate


def is_unique_violation(exc: IntegrityError) -> bool:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) == "23505"


async def get_activity_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    activity_id: uuid.UUID,
) -> Activity | None:
    result = await session.execute(
        select(Activity)
        .options(selectinload(Activity.samples))
        .where(Activity.id == activity_id, Activity.user_id == user_id)
    )
    return result.scalar_one_or_none()


def utc_day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


async def list_activity_types_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[str]:
    result = await session.execute(
        select(Activity.activity_type)
        .where(Activity.user_id == user_id, Activity.activity_type.is_not(None))
        .distinct()
        .order_by(Activity.activity_type)
    )
    return [row[0] for row in result.all() if row[0]]


def _filtered_activity_query(
    *,
    user_id: uuid.UUID,
    started_on_or_after: date | None,
    started_on_or_before: date | None,
    activity_type: str | None,
) -> Select[tuple[Activity]]:
    query = select(Activity).where(Activity.user_id == user_id)
    if activity_type:
        query = query.where(Activity.activity_type == activity_type)
    if started_on_or_after is not None or started_on_or_before is not None:
        query = query.where(Activity.started_at.is_not(None))
    if started_on_or_after is not None:
        query = query.where(Activity.started_at >= utc_day_start(started_on_or_after))
    if started_on_or_before is not None:
        exclusive_end = utc_day_start(started_on_or_before) + timedelta(days=1)
        query = query.where(Activity.started_at < exclusive_end)
    return query


async def list_activities_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
    offset: int,
    started_on_or_after: date | None = None,
    started_on_or_before: date | None = None,
    activity_type: str | None = None,
) -> tuple[list[Activity], int]:
    if (
        started_on_or_after is not None
        and started_on_or_before is not None
        and started_on_or_after > started_on_or_before
    ):
        raise AppError(
            "INVALID_DATE_RANGE",
            "from_date must be on or before to_date",
            status_code=400,
        )

    filtered = _filtered_activity_query(
        user_id=user_id,
        started_on_or_after=started_on_or_after,
        started_on_or_before=started_on_or_before,
        activity_type=activity_type,
    )
    total_result = await session.execute(select(func.count()).select_from(filtered.subquery()))
    total = int(total_result.scalar_one())
    result = await session.execute(
        filtered.order_by(Activity.started_at.desc().nulls_last(), Activity.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def get_last_sync_at(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: str,
) -> datetime | None:
    result = await session.execute(
        select(ProviderConnection).where(
            ProviderConnection.user_id == user_id,
            ProviderConnection.provider == provider,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        return None
    return connection.last_sync_at


async def create_activity_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: ActivityCreate,
) -> Activity:
    activity = Activity(
        user_id=user_id,
        provider=payload.provider,
        provider_activity_id=payload.provider_activity_id,
        activity_type=payload.activity_type,
        started_at=payload.started_at,
        duration_seconds=payload.duration_seconds,
        distance_meters=payload.distance_meters,
        average_speed=payload.average_speed,
        average_heart_rate=payload.average_heart_rate,
        max_heart_rate=payload.max_heart_rate,
        average_cadence=payload.average_cadence,
        elevation_gain=payload.elevation_gain,
        calories=payload.calories,
        samples=[_sample_from_create(item) for item in payload.samples],
    )
    session.add(activity)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        if is_unique_violation(exc):
            raise AppError(
                "DUPLICATE_ACTIVITY",
                "An activity with this provider id already exists",
                status_code=409,
            ) from exc
        raise
    return activity


def apply_provider_summary(activity: Activity, incoming: ProviderActivity) -> None:
    activity.activity_type = incoming.activity_type
    activity.started_at = incoming.started_at
    activity.duration_seconds = incoming.duration_seconds
    activity.distance_meters = incoming.distance_meters
    activity.average_speed = incoming.average_speed
    activity.average_heart_rate = incoming.average_heart_rate
    activity.max_heart_rate = incoming.max_heart_rate
    activity.average_cadence = incoming.average_cadence
    activity.elevation_gain = incoming.elevation_gain
    activity.calories = incoming.calories
    activity.updated_at = datetime.now(UTC)


async def replace_provider_samples(
    session: AsyncSession,
    activity: Activity,
    incoming: ProviderActivity,
) -> None:
    """Delete existing samples before insert so unique elapsed_seconds cannot collide."""
    activity.samples.clear()
    await session.flush()
    activity.samples = [_sample_from_provider(item) for item in incoming.samples]


def activity_from_provider(*, user_id: uuid.UUID, incoming: ProviderActivity) -> Activity:
    activity = Activity(
        user_id=user_id,
        provider=incoming.provider,
        provider_activity_id=incoming.provider_activity_id,
        samples=[_sample_from_provider(item) for item in incoming.samples],
    )
    apply_provider_summary(activity, incoming)
    return activity


def _sample_from_create(item: ActivitySampleCreate) -> ActivitySample:
    return ActivitySample(
        timestamp=item.timestamp,
        elapsed_seconds=item.elapsed_seconds,
        distance_meters=item.distance_meters,
        heart_rate=item.heart_rate,
        speed=item.speed,
        cadence=item.cadence,
        elevation=item.elevation,
    )


def _sample_from_provider(item: ProviderActivitySample) -> ActivitySample:
    return ActivitySample(
        timestamp=item.timestamp,
        elapsed_seconds=item.elapsed_seconds,
        distance_meters=item.distance_meters,
        heart_rate=item.heart_rate,
        speed=item.speed,
        cadence=item.cadence,
        elevation=item.elevation,
    )
