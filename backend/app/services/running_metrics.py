"""Simple running aggregates for the dashboard and activity views.

Pace and volume live here rather than in API routes. Aerobic efficiency, easy
running, and 5K estimation live in `running_analytics` and
`performance_prediction`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

# Instantaneous speeds at or below this are treated as a pause, not running.
PAUSE_SPEED_METERS_PER_SECOND = 0.4

# Heart-rate samples outside this window are dropped as sensor noise.
PLAUSIBLE_HEART_RATE_MIN = 80
PLAUSIBLE_HEART_RATE_MAX = 220

# Query-parameter bounds. Wider than a typical training zone so the UI can
# choose; still rejects nonsense such as 5 bpm or 400 bpm.
HEART_RATE_QUERY_MIN = 40
HEART_RATE_QUERY_MAX = 220

DEFAULT_EASY_HEART_RATE_MIN = 140
DEFAULT_EASY_HEART_RATE_MAX = 150

# Easy/moderate ceiling used by aerobic efficiency. Harder work is a different
# comparison and is excluded rather than mixed in.
MODERATE_HEART_RATE_MAX = 168

RUN_ACTIVITY_TYPES = frozenset(
    {
        "run",
        "running",
        "trail_run",
        "treadmill",
        "indoor_run",
        "track",
        "virtual_run",
    }
)


@dataclass(frozen=True)
class VolumeRow:
    started_at: datetime | None
    distance_meters: float | None
    duration_seconds: int | None


@dataclass(frozen=True)
class TrainingVolume:
    run_count: int
    distance_meters: float
    duration_seconds: int
    period_start: datetime
    period_end: datetime


@dataclass(frozen=True)
class HeartRateBand:
    """Inclusive beats-per-minute window. Not a personal Zone 2 definition."""

    minimum: int
    maximum: int

    def __post_init__(self) -> None:
        if self.minimum < HEART_RATE_QUERY_MIN or self.maximum > HEART_RATE_QUERY_MAX:
            raise ValueError(
                f"Heart-rate bounds must be between {HEART_RATE_QUERY_MIN} and "
                f"{HEART_RATE_QUERY_MAX} bpm"
            )
        if self.minimum >= self.maximum:
            raise ValueError("Heart-rate minimum must be lower than maximum")

    @property
    def midpoint(self) -> float:
        return (self.minimum + self.maximum) / 2.0

    def contains(self, heart_rate: float) -> bool:
        return self.minimum <= heart_rate <= self.maximum


def default_easy_heart_rate_band() -> HeartRateBand:
    return HeartRateBand(
        minimum=DEFAULT_EASY_HEART_RATE_MIN,
        maximum=DEFAULT_EASY_HEART_RATE_MAX,
    )


def calculate_pace(
    *,
    distance_meters: float | None,
    duration_seconds: int | None,
) -> float | None:
    """Return seconds per kilometre, or None when the inputs cannot form a pace."""
    if distance_meters is None or duration_seconds is None:
        return None
    if distance_meters < 1 or duration_seconds < 1:
        return None
    return duration_seconds / (distance_meters / 1000.0)


def calculate_pace_from_speed(speed_meters_per_second: float | None) -> float | None:
    """Convert instantaneous speed (m/s) to seconds per kilometre."""
    if speed_meters_per_second is None or speed_meters_per_second <= 0:
        return None
    return 1000.0 / speed_meters_per_second


def calculate_training_volume(
    rows: Sequence[VolumeRow],
    *,
    period_start: datetime,
    period_end: datetime,
) -> TrainingVolume:
    """Count runs and sum distance/time whose start falls in [period_start, period_end)."""
    if period_end < period_start:
        raise ValueError("period_end must be on or after period_start")

    run_count = 0
    distance = 0.0
    duration = 0
    for row in rows:
        if row.started_at is None:
            continue
        if row.started_at < period_start or row.started_at >= period_end:
            continue
        run_count += 1
        if row.distance_meters is not None and row.distance_meters > 0:
            distance += row.distance_meters
        if row.duration_seconds is not None and row.duration_seconds > 0:
            duration += row.duration_seconds

    return TrainingVolume(
        run_count=run_count,
        distance_meters=distance,
        duration_seconds=duration,
        period_start=period_start,
        period_end=period_end,
    )


def is_run_activity(activity_type: str | None) -> bool:
    if activity_type is None:
        return False
    return activity_type.strip().lower() in RUN_ACTIVITY_TYPES


def is_plausible_heart_rate(heart_rate: int | float | None) -> bool:
    if heart_rate is None:
        return False
    return PLAUSIBLE_HEART_RATE_MIN <= heart_rate <= PLAUSIBLE_HEART_RATE_MAX


def is_moving_speed(speed_meters_per_second: float | None) -> bool:
    if speed_meters_per_second is None:
        return False
    return speed_meters_per_second > PAUSE_SPEED_METERS_PER_SECOND


def calculate_pace_at_heart_rate(
    *,
    pace_seconds_per_km: float,
    heart_rate: float,
    reference_heart_rate: float,
) -> float | None:
    """Estimate pace at a reference heart rate.

    Assumption: over easy/moderate running, speed scales roughly with heart
    rate. Then pace_at_ref = pace * (actual_hr / ref_hr). This is a simple
    comparability adjustment, not a physiological model.
    """
    if pace_seconds_per_km <= 0 or heart_rate <= 0 or reference_heart_rate <= 0:
        return None
    return pace_seconds_per_km * (heart_rate / reference_heart_rate)
