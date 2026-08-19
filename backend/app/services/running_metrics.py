"""Simple running aggregates for the dashboard and activity views.

Pace and volume live here rather than in API routes. Aerobic efficiency and
5K estimation are Phase 5 and must not be added here yet.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime


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
