"""Load the current user's activities and compute analytics.

Identity is always the session user passed in by the caller. Heart-rate bands
and trend windows are query parameters, not a stored Zone 2.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity
from app.schemas.analytics import (
    AerobicEfficiencyAvailable,
    AerobicEfficiencyMetric,
    AerobicEfficiencyResponse,
    AerobicPointPublic,
    EasyPaceAvailable,
    EasyPaceMetric,
    EasyRunningPointPublic,
    EasyRunningResponse,
    FiveKEstimateAvailable,
    FiveKEstimateMetric,
    TrendActivityPointPublic,
    TrendsResponse,
    UnavailableMetric,
    WeeklyTrendPointPublic,
)
from app.services.performance_prediction import FiveKEstimate, estimate_5k_time
from app.services.running_analytics import (
    ActivityObservation,
    AerobicEfficiencyResult,
    EasyRunningResult,
    SampleObservation,
    TrendRangeKey,
    calculate_aerobic_efficiency,
    calculate_easy_pace_trend,
    calculate_trends,
)
from app.services.running_analytics import (
    parse_trend_range as parse_trend_range,
)
from app.services.running_metrics import HeartRateBand

DIRECTION_LABELS = {
    "improving": "Improving",
    "stable": "Stable",
    "declining": "A little slower",
    "not_enough_data": "Not enough data",
}


def observation_from_activity(activity: Activity) -> ActivityObservation:
    samples = tuple(
        SampleObservation(
            heart_rate=sample.heart_rate,
            speed=sample.speed,
            distance_meters=sample.distance_meters,
            elapsed_seconds=sample.elapsed_seconds,
        )
        for sample in activity.samples
    )
    return ActivityObservation(
        id=activity.id,
        activity_type=activity.activity_type,
        started_at=activity.started_at,
        distance_meters=activity.distance_meters,
        duration_seconds=activity.duration_seconds,
        average_heart_rate=activity.average_heart_rate,
        samples=samples,
    )


async def load_observations_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[ActivityObservation]:
    result = await session.execute(
        select(Activity)
        .options(selectinload(Activity.samples))
        .where(Activity.user_id == user_id)
        .order_by(Activity.started_at.asc().nulls_last(), Activity.id.asc())
    )
    return [observation_from_activity(item) for item in result.scalars().unique().all()]


def parse_heart_rate_band(hr_min: int, hr_max: int) -> HeartRateBand:
    return HeartRateBand(minimum=hr_min, maximum=hr_max)


def five_k_metric(estimate: FiveKEstimate) -> FiveKEstimateMetric:
    if not estimate.available or estimate.estimated_seconds is None:
        return UnavailableMetric(
            label="5K estimate",
            headline=estimate.headline,
            note=estimate.note,
        )
    return FiveKEstimateAvailable(
        headline=estimate.headline,
        note=estimate.note,
        estimated_seconds=estimate.estimated_seconds,
        qualifying_run_count=estimate.qualifying_run_count,
    )


def easy_pace_metric(result: EasyRunningResult) -> EasyPaceMetric:
    if (
        result.run_count == 0
        or result.average_pace_seconds_per_km is None
        or result.comparable_pace_seconds_per_km is None
        or result.average_heart_rate is None
    ):
        return UnavailableMetric(
            label="Easy pace",
            headline=result.headline,
            note=result.note,
        )
    return EasyPaceAvailable(
        headline=result.headline,
        note=result.note,
        pace_seconds_per_km=result.average_pace_seconds_per_km,
        comparable_pace_seconds_per_km=result.comparable_pace_seconds_per_km,
        average_heart_rate=result.average_heart_rate,
        run_count=result.run_count,
        heart_rate_min=result.heart_rate_min,
        heart_rate_max=result.heart_rate_max,
    )


def aerobic_metric(result: AerobicEfficiencyResult) -> AerobicEfficiencyMetric:
    if result.qualifying_run_count == 0:
        return UnavailableMetric(
            label="Aerobic efficiency",
            headline=result.headline,
            note=result.note,
        )
    return AerobicEfficiencyAvailable(
        headline=result.headline,
        note=result.note,
        direction=result.direction,
        direction_label=DIRECTION_LABELS[result.direction],
        score=result.score,
        relative_change_percent=result.relative_change_percent,
        qualifying_run_count=result.qualifying_run_count,
    )


def easy_running_response(result: EasyRunningResult) -> EasyRunningResponse:
    return EasyRunningResponse(
        heart_rate_min=result.heart_rate_min,
        heart_rate_max=result.heart_rate_max,
        run_count=result.run_count,
        distance_meters=result.distance_meters,
        average_pace_seconds_per_km=result.average_pace_seconds_per_km,
        average_heart_rate=result.average_heart_rate,
        comparable_pace_seconds_per_km=result.comparable_pace_seconds_per_km,
        headline=result.headline,
        note=result.note,
        points=[
            EasyRunningPointPublic(
                activity_id=point.activity_id,
                started_at=point.started_at,
                pace_seconds_per_km=point.pace_seconds_per_km,
                heart_rate=point.heart_rate,
                comparable_pace_seconds_per_km=point.comparable_pace_seconds_per_km,
                distance_meters=point.distance_meters,
            )
            for point in result.points
        ],
    )


def aerobic_response(result: AerobicEfficiencyResult) -> AerobicEfficiencyResponse:
    return AerobicEfficiencyResponse(
        metric=aerobic_metric(result),
        points=[
            AerobicPointPublic(
                activity_id=point.activity_id,
                started_at=point.started_at,
                score=point.score,
                pace_seconds_per_km=point.pace_seconds_per_km,
                heart_rate=point.heart_rate,
            )
            for point in result.points
        ],
    )


async def get_easy_running_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    hr_min: int,
    hr_max: int,
    started_after: datetime | None = None,
) -> EasyRunningResponse:
    band = parse_heart_rate_band(hr_min, hr_max)
    observations = await load_observations_for_user(session, user_id=user_id)
    result = calculate_easy_pace_trend(observations, band, started_after=started_after)
    return easy_running_response(result)


async def get_aerobic_efficiency_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    started_after: datetime | None = None,
) -> AerobicEfficiencyResponse:
    observations = await load_observations_for_user(session, user_id=user_id)
    result = calculate_aerobic_efficiency(observations, started_after=started_after)
    return aerobic_response(result)


async def get_trends_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    range_key: str,
    hr_min: int,
    hr_max: int,
    now: datetime,
) -> TrendsResponse:
    parsed: TrendRangeKey = parse_trend_range(range_key)
    band = parse_heart_rate_band(hr_min, hr_max)
    observations = await load_observations_for_user(session, user_id=user_id)
    result = calculate_trends(observations, band, range_key=parsed, now=now)
    return TrendsResponse(
        range_key=result.range_key,
        period_start=result.period_start,
        period_end=result.period_end,
        heart_rate_min=result.heart_rate_min,
        heart_rate_max=result.heart_rate_max,
        points=[
            TrendActivityPointPublic(
                activity_id=point.activity_id,
                started_at=point.started_at,
                pace_seconds_per_km=point.pace_seconds_per_km,
                average_heart_rate=point.average_heart_rate,
                distance_meters=point.distance_meters,
                comparable_pace_seconds_per_km=point.comparable_pace_seconds_per_km,
            )
            for point in result.points
        ],
        weekly=[
            WeeklyTrendPointPublic(
                week_start=point.week_start,
                distance_meters=point.distance_meters,
                run_count=point.run_count,
            )
            for point in result.weekly
        ],
    )


async def dashboard_metrics_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    now: datetime,
    hr_min: int,
    hr_max: int,
) -> tuple[FiveKEstimateMetric, EasyPaceMetric, AerobicEfficiencyMetric]:
    observations = await load_observations_for_user(session, user_id=user_id)
    band = parse_heart_rate_band(hr_min, hr_max)
    five_k = five_k_metric(estimate_5k_time(observations, now=now))
    easy = easy_pace_metric(calculate_easy_pace_trend(observations, band))
    aerobic = aerobic_metric(calculate_aerobic_efficiency(observations))
    return five_k, easy, aerobic
