"""Assemble the authenticated dashboard from stored activities.

Identity is always the session user passed in by the caller. Calculations
delegate to running_metrics and analytics services; this module only loads
rows and shapes the response.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.schemas.activity import ActivitySummary
from app.schemas.dashboard import (
    DashboardResponse,
    PaceHeartRatePoint,
    WeeklyVolumePublic,
)
from app.services.analytics import dashboard_metrics_for_user
from app.services.running_metrics import (
    DEFAULT_EASY_HEART_RATE_MAX,
    DEFAULT_EASY_HEART_RATE_MIN,
    VolumeRow,
    calculate_pace,
    calculate_training_volume,
)

RECENT_ACTIVITY_LIMIT = 5
TREND_ACTIVITY_LIMIT = 24
WEEK_WINDOW = timedelta(days=7)


async def get_dashboard_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime | None = None,
    hr_min: int = DEFAULT_EASY_HEART_RATE_MIN,
    hr_max: int = DEFAULT_EASY_HEART_RATE_MAX,
) -> DashboardResponse:
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    else:
        moment = moment.astimezone(UTC)
    period_start = moment - WEEK_WINDOW

    week_result = await session.execute(
        select(Activity).where(
            Activity.user_id == user_id,
            Activity.started_at.is_not(None),
            Activity.started_at >= period_start,
            Activity.started_at < moment,
        )
    )
    week_activities = list(week_result.scalars().all())
    volume = calculate_training_volume(
        [
            VolumeRow(
                started_at=item.started_at,
                distance_meters=item.distance_meters,
                duration_seconds=item.duration_seconds,
            )
            for item in week_activities
        ],
        period_start=period_start,
        period_end=moment,
    )

    recent_result = await session.execute(
        select(Activity)
        .where(Activity.user_id == user_id)
        .order_by(Activity.started_at.desc().nulls_last(), Activity.id.desc())
        .limit(RECENT_ACTIVITY_LIMIT)
    )
    recent = list(recent_result.scalars().all())

    trend_result = await session.execute(
        select(Activity)
        .where(Activity.user_id == user_id, Activity.started_at.is_not(None))
        .order_by(Activity.started_at.desc(), Activity.id.desc())
        .limit(TREND_ACTIVITY_LIMIT)
    )
    newest_first = list(trend_result.scalars().all())
    chronological = list(reversed(newest_first))
    trend_points: list[PaceHeartRatePoint] = []
    for item in chronological:
        if item.started_at is None:
            continue
        trend_points.append(
            PaceHeartRatePoint(
                activity_id=item.id,
                started_at=item.started_at,
                pace_seconds_per_km=calculate_pace(
                    distance_meters=item.distance_meters,
                    duration_seconds=item.duration_seconds,
                ),
                average_heart_rate=item.average_heart_rate,
                distance_meters=item.distance_meters,
            )
        )

    five_k, easy_pace, aerobic = await dashboard_metrics_for_user(
        session,
        user_id=user_id,
        now=moment,
        hr_min=hr_min,
        hr_max=hr_max,
    )

    return DashboardResponse(
        weekly=WeeklyVolumePublic(
            run_count=volume.run_count,
            distance_meters=volume.distance_meters,
            duration_seconds=volume.duration_seconds,
            period_start=volume.period_start,
            period_end=volume.period_end,
        ),
        recent_activities=[ActivitySummary.model_validate(item) for item in recent],
        pace_heart_rate_trend=trend_points,
        five_k_estimate=five_k,
        easy_pace=easy_pace,
        aerobic_efficiency=aerobic,
    )
