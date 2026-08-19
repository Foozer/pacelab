"""Aerobic efficiency, easy-running, and trend maths.

All formulas live here so API routes only pass the authenticated user and query
parameters. None of these numbers is a lab VO2 test or a medical claim.

Aerobic efficiency
------------------
For each easy/moderate *run*, drop pause samples (speed at or below
``PAUSE_SPEED_METERS_PER_SECOND``) and implausible heart rates. Remaining
samples give a mean moving speed and mean heart rate. The efficiency score is:

    score = mean_moving_speed_m_s / mean_heart_rate_bpm

Higher means more speed at the same heart rate (or the same speed at a lower
heart rate). When samples are missing, the activity summary pace and average
heart rate are used instead. Non-run types and efforts whose mean heart rate is
above ``MODERATE_HEART_RATE_MAX`` are excluded so a bike ride or an interval
session is not mixed into the easy/moderate story.

Direction compares the mean score of the first half of qualifying runs with the
mean of the last half (chronological). A rise of 3% or more is "improving"; a
fall of 3% or more is "declining"; otherwise "stable". Fewer than four runs, or
a span shorter than 14 days, is "not enough data". The headline stays in plain
English; the numeric score is optional detail.

Easy running
------------
A run is included when it is a run type *and* either its activity-average heart
rate sits in the requested band, or it has moving samples whose heart rate sits
in that band. Aggregates prefer in-band moving samples (pace, heart rate,
distance from those samples). If there are no samples, the activity summary is
used only when the average heart rate is in the band.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from app.services.running_metrics import (
    MODERATE_HEART_RATE_MAX,
    HeartRateBand,
    VolumeRow,
    calculate_pace,
    calculate_pace_at_heart_rate,
    calculate_pace_from_speed,
    calculate_training_volume,
    is_moving_speed,
    is_plausible_heart_rate,
    is_run_activity,
)

Direction = Literal["improving", "stable", "declining", "not_enough_data"]

MIN_SAMPLES_FOR_ACTIVITY_MEANS = 3
MIN_RUNS_FOR_EFFICIENCY_TREND = 4
MIN_SPAN_DAYS_FOR_EFFICIENCY_TREND = 14
EFFICIENCY_CHANGE_THRESHOLD = 0.03

TREND_RANGE_KEYS = ("4w", "8w", "3m", "6m", "1y", "all")
TrendRangeKey = Literal["4w", "8w", "3m", "6m", "1y", "all"]

_RANGE_DELTAS: dict[str, timedelta | None] = {
    "4w": timedelta(weeks=4),
    "8w": timedelta(weeks=8),
    "3m": timedelta(days=90),
    "6m": timedelta(days=182),
    "1y": timedelta(days=365),
    "all": None,
}


@dataclass(frozen=True)
class SampleObservation:
    heart_rate: int | None
    speed: float | None
    distance_meters: float | None = None
    elapsed_seconds: int | None = None


@dataclass(frozen=True)
class ActivityObservation:
    id: UUID | None
    activity_type: str | None
    started_at: datetime | None
    distance_meters: float | None
    duration_seconds: int | None
    average_heart_rate: int | None
    samples: tuple[SampleObservation, ...] = ()


@dataclass(frozen=True)
class MovingEffort:
    """Pause-stripped, plausible-HR view of one activity."""

    pace_seconds_per_km: float
    heart_rate: float
    speed_meters_per_second: float
    sample_count: int
    from_samples: bool


@dataclass(frozen=True)
class EfficiencyPoint:
    started_at: datetime
    activity_id: UUID | None
    score: float
    pace_seconds_per_km: float
    heart_rate: float


@dataclass(frozen=True)
class AerobicEfficiencyResult:
    direction: Direction
    headline: str
    note: str
    score: float | None
    relative_change_percent: float | None
    qualifying_run_count: int
    points: tuple[EfficiencyPoint, ...]


@dataclass(frozen=True)
class EasyRunPoint:
    started_at: datetime
    activity_id: UUID | None
    pace_seconds_per_km: float
    heart_rate: float
    comparable_pace_seconds_per_km: float
    distance_meters: float


@dataclass(frozen=True)
class EasyRunningResult:
    heart_rate_min: int
    heart_rate_max: int
    run_count: int
    distance_meters: float
    average_pace_seconds_per_km: float | None
    average_heart_rate: float | None
    comparable_pace_seconds_per_km: float | None
    headline: str
    note: str
    points: tuple[EasyRunPoint, ...]


@dataclass(frozen=True)
class TrendPoint:
    started_at: datetime
    activity_id: UUID | None
    pace_seconds_per_km: float | None
    average_heart_rate: float | None
    distance_meters: float | None
    comparable_pace_seconds_per_km: float | None


@dataclass(frozen=True)
class WeeklyTrendPoint:
    week_start: datetime
    distance_meters: float
    run_count: int


@dataclass(frozen=True)
class TrendsResult:
    range_key: str
    period_start: datetime | None
    period_end: datetime
    heart_rate_min: int
    heart_rate_max: int
    points: tuple[TrendPoint, ...]
    weekly: tuple[WeeklyTrendPoint, ...]


def parse_trend_range(value: str) -> TrendRangeKey:
    if value not in _RANGE_DELTAS:
        allowed = ", ".join(TREND_RANGE_KEYS)
        raise ValueError(f"Range must be one of: {allowed}")
    return value  # type: ignore[return-value]


def window_start_for_range(range_key: TrendRangeKey, *, now: datetime) -> datetime | None:
    delta = _RANGE_DELTAS[range_key]
    if delta is None:
        return None
    return now - delta


def valid_moving_samples(samples: Sequence[SampleObservation]) -> tuple[SampleObservation, ...]:
    """Keep samples that look like running with a usable heart rate."""
    kept: list[SampleObservation] = []
    for sample in samples:
        if not is_moving_speed(sample.speed):
            continue
        if not is_plausible_heart_rate(sample.heart_rate):
            continue
        kept.append(sample)
    return tuple(kept)


def samples_in_heart_rate_band(
    samples: Sequence[SampleObservation],
    band: HeartRateBand,
) -> tuple[SampleObservation, ...]:
    in_band: list[SampleObservation] = []
    for sample in valid_moving_samples(samples):
        if sample.heart_rate is not None and band.contains(sample.heart_rate):
            in_band.append(sample)
    return tuple(in_band)


def moving_effort_from_samples(
    samples: Sequence[SampleObservation],
) -> MovingEffort | None:
    valid = valid_moving_samples(samples)
    if len(valid) < MIN_SAMPLES_FOR_ACTIVITY_MEANS:
        return None
    speeds = [sample.speed for sample in valid if sample.speed is not None]
    rates = [float(sample.heart_rate) for sample in valid if sample.heart_rate is not None]
    if not speeds or not rates:
        return None
    mean_speed = sum(speeds) / len(speeds)
    mean_hr = sum(rates) / len(rates)
    pace = calculate_pace_from_speed(mean_speed)
    if pace is None:
        return None
    return MovingEffort(
        pace_seconds_per_km=pace,
        heart_rate=mean_hr,
        speed_meters_per_second=mean_speed,
        sample_count=len(valid),
        from_samples=True,
    )


def moving_effort_from_activity(activity: ActivityObservation) -> MovingEffort | None:
    if not is_run_activity(activity.activity_type):
        return None
    from_samples = moving_effort_from_samples(activity.samples)
    if from_samples is not None:
        return from_samples
    pace = calculate_pace(
        distance_meters=activity.distance_meters,
        duration_seconds=activity.duration_seconds,
    )
    if pace is None or not is_plausible_heart_rate(activity.average_heart_rate):
        return None
    if activity.average_heart_rate is None:
        return None
    speed = 1000.0 / pace
    return MovingEffort(
        pace_seconds_per_km=pace,
        heart_rate=float(activity.average_heart_rate),
        speed_meters_per_second=speed,
        sample_count=0,
        from_samples=False,
    )


def efficiency_score(effort: MovingEffort) -> float:
    """Speed per beat. Documented in the module docstring."""
    return effort.speed_meters_per_second / effort.heart_rate


def _in_window(activity: ActivityObservation, started_after: datetime | None) -> bool:
    if activity.started_at is None:
        return False
    if started_after is None:
        return True
    return activity.started_at >= started_after


def calculate_aerobic_efficiency(
    activities: Sequence[ActivityObservation],
    *,
    started_after: datetime | None = None,
) -> AerobicEfficiencyResult:
    points: list[EfficiencyPoint] = []
    for activity in activities:
        if not _in_window(activity, started_after):
            continue
        effort = moving_effort_from_activity(activity)
        if effort is None:
            continue
        if effort.heart_rate > MODERATE_HEART_RATE_MAX:
            continue
        if activity.started_at is None:
            continue
        points.append(
            EfficiencyPoint(
                started_at=activity.started_at,
                activity_id=activity.id,
                score=efficiency_score(effort),
                pace_seconds_per_km=effort.pace_seconds_per_km,
                heart_rate=effort.heart_rate,
            )
        )
    points.sort(key=lambda item: item.started_at)

    note = (
        "This is a PaceLab running metric from pace at a similar heart rate. "
        "It is not a lab test and not a medical measurement."
    )
    if not points:
        return AerobicEfficiencyResult(
            direction="not_enough_data",
            headline="Not enough data yet",
            note=(
                "Import easy or moderate runs with heart rate to see whether "
                "your pace at a similar effort is changing. " + note
            ),
            score=None,
            relative_change_percent=None,
            qualifying_run_count=0,
            points=(),
        )

    latest_score = points[-1].score
    span_days = (points[-1].started_at - points[0].started_at).total_seconds() / 86400
    if (
        len(points) < MIN_RUNS_FOR_EFFICIENCY_TREND
        or span_days < MIN_SPAN_DAYS_FOR_EFFICIENCY_TREND
    ):
        return AerobicEfficiencyResult(
            direction="not_enough_data",
            headline="Not enough data yet",
            note=(
                "A direction needs at least four easy or moderate runs spread "
                "over two weeks. " + note
            ),
            score=latest_score,
            relative_change_percent=None,
            qualifying_run_count=len(points),
            points=tuple(points),
        )

    split = len(points) // 2
    earlier = sum(point.score for point in points[:split]) / split
    later = sum(point.score for point in points[split:]) / (len(points) - split)
    change = (later - earlier) / earlier if earlier > 0 else 0.0
    if change >= EFFICIENCY_CHANGE_THRESHOLD:
        direction: Direction = "improving"
        headline = "Your easy pace is improving"
    elif change <= -EFFICIENCY_CHANGE_THRESHOLD:
        direction = "declining"
        headline = "Your easy pace looks a little slower lately"
    else:
        direction = "stable"
        headline = "Your easy pace is holding steady"

    return AerobicEfficiencyResult(
        direction=direction,
        headline=headline,
        note=note,
        score=latest_score,
        relative_change_percent=change * 100.0,
        qualifying_run_count=len(points),
        points=tuple(points),
    )


def _sample_distance(samples: Sequence[SampleObservation]) -> float | None:
    distances = [sample.distance_meters for sample in samples if sample.distance_meters is not None]
    if len(distances) < 2:
        return None
    span = max(distances) - min(distances)
    return span if span > 0 else None


def easy_effort_for_activity(
    activity: ActivityObservation,
    band: HeartRateBand,
) -> EasyRunPoint | None:
    if not is_run_activity(activity.activity_type) or activity.started_at is None:
        return None

    in_band = samples_in_heart_rate_band(activity.samples, band)
    if len(in_band) >= MIN_SAMPLES_FOR_ACTIVITY_MEANS:
        effort = moving_effort_from_samples(in_band)
        if effort is None:
            return None
        distance = _sample_distance(in_band)
        if distance is None:
            distance = activity.distance_meters or 0.0
        comparable = calculate_pace_at_heart_rate(
            pace_seconds_per_km=effort.pace_seconds_per_km,
            heart_rate=effort.heart_rate,
            reference_heart_rate=band.midpoint,
        )
        if comparable is None:
            return None
        return EasyRunPoint(
            started_at=activity.started_at,
            activity_id=activity.id,
            pace_seconds_per_km=effort.pace_seconds_per_km,
            heart_rate=effort.heart_rate,
            comparable_pace_seconds_per_km=comparable,
            distance_meters=distance,
        )

    if activity.average_heart_rate is None or not band.contains(activity.average_heart_rate):
        return None
    pace = calculate_pace(
        distance_meters=activity.distance_meters,
        duration_seconds=activity.duration_seconds,
    )
    if pace is None:
        return None
    comparable = calculate_pace_at_heart_rate(
        pace_seconds_per_km=pace,
        heart_rate=float(activity.average_heart_rate),
        reference_heart_rate=band.midpoint,
    )
    if comparable is None:
        return None
    return EasyRunPoint(
        started_at=activity.started_at,
        activity_id=activity.id,
        pace_seconds_per_km=pace,
        heart_rate=float(activity.average_heart_rate),
        comparable_pace_seconds_per_km=comparable,
        distance_meters=activity.distance_meters or 0.0,
    )


def calculate_easy_pace_trend(
    activities: Sequence[ActivityObservation],
    band: HeartRateBand,
    *,
    started_after: datetime | None = None,
) -> EasyRunningResult:
    points: list[EasyRunPoint] = []
    for activity in activities:
        if not _in_window(activity, started_after):
            continue
        point = easy_effort_for_activity(activity, band)
        if point is not None:
            points.append(point)
    points.sort(key=lambda item: item.started_at)

    note = (
        f"Runs whose heart rate sits in {band.minimum}–{band.maximum} bpm. "
        "In-band moving samples are used when they exist; otherwise the run "
        "average is used if it falls in the range. This is not a personal "
        "Zone 2 definition."
    )
    if not points:
        return EasyRunningResult(
            heart_rate_min=band.minimum,
            heart_rate_max=band.maximum,
            run_count=0,
            distance_meters=0.0,
            average_pace_seconds_per_km=None,
            average_heart_rate=None,
            comparable_pace_seconds_per_km=None,
            headline="No runs in this heart-rate range yet",
            note=note,
            points=(),
        )

    distance = sum(point.distance_meters for point in points)
    avg_pace = sum(point.pace_seconds_per_km for point in points) / len(points)
    avg_hr = sum(point.heart_rate for point in points) / len(points)
    comparable = sum(point.comparable_pace_seconds_per_km for point in points) / len(points)

    if len(points) >= 4:
        split = len(points) // 2
        earlier = sum(p.comparable_pace_seconds_per_km for p in points[:split]) / split
        later = sum(p.comparable_pace_seconds_per_km for p in points[split:]) / (
            len(points) - split
        )
        if later <= earlier * (1.0 - EFFICIENCY_CHANGE_THRESHOLD):
            headline = "Your easy pace is improving"
        elif later >= earlier * (1.0 + EFFICIENCY_CHANGE_THRESHOLD):
            headline = "Your easy pace looks a little slower lately"
        else:
            headline = "Your easy pace is holding steady"
    else:
        headline = "A few more easy runs will show a trend"

    return EasyRunningResult(
        heart_rate_min=band.minimum,
        heart_rate_max=band.maximum,
        run_count=len(points),
        distance_meters=distance,
        average_pace_seconds_per_km=avg_pace,
        average_heart_rate=avg_hr,
        comparable_pace_seconds_per_km=comparable,
        headline=headline,
        note=note,
        points=tuple(points),
    )


def _monday_utc(moment: datetime) -> datetime:
    local = moment.astimezone(UTC)
    week_start = local - timedelta(days=local.weekday())
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)


def calculate_weekly_distance(
    activities: Sequence[ActivityObservation],
    *,
    started_after: datetime | None,
    period_end: datetime,
) -> tuple[WeeklyTrendPoint, ...]:
    rows = [
        VolumeRow(
            started_at=activity.started_at,
            distance_meters=activity.distance_meters,
            duration_seconds=activity.duration_seconds,
        )
        for activity in activities
        if is_run_activity(activity.activity_type) and _in_window(activity, started_after)
    ]
    if not rows:
        return ()

    first = min(row.started_at for row in rows if row.started_at is not None)
    start = _monday_utc(started_after or first)
    end = _monday_utc(period_end) + timedelta(days=7)
    points: list[WeeklyTrendPoint] = []
    week = start
    while week < end:
        week_end = week + timedelta(days=7)
        volume = calculate_training_volume(rows, period_start=week, period_end=week_end)
        points.append(
            WeeklyTrendPoint(
                week_start=week,
                distance_meters=volume.distance_meters,
                run_count=volume.run_count,
            )
        )
        week = week_end
    return tuple(points)


def calculate_trends(
    activities: Sequence[ActivityObservation],
    band: HeartRateBand,
    *,
    range_key: TrendRangeKey,
    now: datetime,
) -> TrendsResult:
    started_after = window_start_for_range(range_key, now=now)
    points: list[TrendPoint] = []
    for activity in activities:
        if not is_run_activity(activity.activity_type) or not _in_window(activity, started_after):
            continue
        if activity.started_at is None:
            continue
        effort = moving_effort_from_activity(activity)
        easy = easy_effort_for_activity(activity, band)
        pace: float | None
        heart_rate: float | None
        if effort is not None:
            pace = effort.pace_seconds_per_km
            heart_rate = effort.heart_rate
        else:
            pace = calculate_pace(
                distance_meters=activity.distance_meters,
                duration_seconds=activity.duration_seconds,
            )
            heart_rate = (
                float(activity.average_heart_rate)
                if activity.average_heart_rate is not None
                else None
            )
        points.append(
            TrendPoint(
                started_at=activity.started_at,
                activity_id=activity.id,
                pace_seconds_per_km=pace,
                average_heart_rate=heart_rate,
                distance_meters=activity.distance_meters,
                comparable_pace_seconds_per_km=(
                    easy.comparable_pace_seconds_per_km if easy else None
                ),
            )
        )
    points.sort(key=lambda item: item.started_at)
    weekly = calculate_weekly_distance(
        activities,
        started_after=started_after,
        period_end=now,
    )
    return TrendsResult(
        range_key=range_key,
        period_start=started_after,
        period_end=now,
        heart_rate_min=band.minimum,
        heart_rate_max=band.maximum,
        points=tuple(points),
        weekly=weekly,
    )
