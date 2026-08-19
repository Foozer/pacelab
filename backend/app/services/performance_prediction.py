"""Isolated 5K time estimate.

Replace the body of ``estimate_5k_time`` when a better model exists. Callers
depend only on ``FiveKEstimate``: available or not, labelled seconds, and a
plain-English note. Do not treat the result as a race prediction.

Algorithm (Riegel scaling)
--------------------------
Consider run-type activities with:

- distance between 3 km and 16 km (inclusive)
- duration at least 10 minutes
- a start time inside the lookback window (56 days by default)

For each qualifying run:

    estimated_5k_seconds = duration_seconds * (5000 / distance_meters) ** 1.06

That is Pete Riegel's power-law endurance formula with the usual 1.06 exponent.
It assumes similar effort across distances and ignores hills, weather, and
whether the run was easy or a time trial.

The reported estimate is the **median** of the three fastest (lowest) of those
scaled times. Two qualifying runs are required; a single scaled workout is too
thin to show. If nothing qualifies, the result is unavailable with an
explanation — numbers are never invented.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from app.services.running_analytics import ActivityObservation
from app.services.running_metrics import is_run_activity

RIEGEL_EXPONENT = 1.06
FIVE_K_METERS = 5000.0
MIN_DISTANCE_METERS = 3000.0
MAX_DISTANCE_METERS = 16000.0
MIN_DURATION_SECONDS = 600
DEFAULT_LOOKBACK = timedelta(days=56)
MIN_QUALIFYING_RUNS = 2
FASTEST_SAMPLE_LIMIT = 3


@dataclass(frozen=True)
class FiveKEstimate:
    available: bool
    estimated_seconds: int | None
    qualifying_run_count: int
    headline: str
    note: str


def riegel_equivalent_seconds(
    *,
    duration_seconds: float,
    distance_meters: float,
    target_meters: float = FIVE_K_METERS,
    exponent: float = RIEGEL_EXPONENT,
) -> float:
    """Scale a completed effort to another distance with Riegel's formula."""
    if duration_seconds <= 0 or distance_meters <= 0 or target_meters <= 0:
        raise ValueError("duration and distances must be positive")
    return float(duration_seconds * (target_meters / distance_meters) ** exponent)


def estimate_5k_time(
    activities: Sequence[ActivityObservation],
    *,
    now: datetime,
    lookback: timedelta = DEFAULT_LOOKBACK,
) -> FiveKEstimate:
    """Deterministic 5K estimate from recent runs. See module docstring."""
    window_start = now - lookback
    scaled: list[float] = []
    for activity in activities:
        if not is_run_activity(activity.activity_type):
            continue
        if activity.started_at is None or activity.started_at < window_start:
            continue
        if activity.distance_meters is None or activity.duration_seconds is None:
            continue
        if activity.distance_meters < MIN_DISTANCE_METERS:
            continue
        if activity.distance_meters > MAX_DISTANCE_METERS:
            continue
        if activity.duration_seconds < MIN_DURATION_SECONDS:
            continue
        scaled.append(
            riegel_equivalent_seconds(
                duration_seconds=float(activity.duration_seconds),
                distance_meters=activity.distance_meters,
            )
        )

    note = (
        "This is an estimate from recent training, not a race prediction. "
        "It scales runs between 3 km and 16 km with a simple formula and "
        "does not know about courses, weather, or how hard you meant to go."
    )
    if len(scaled) < MIN_QUALIFYING_RUNS:
        return FiveKEstimate(
            available=False,
            estimated_seconds=None,
            qualifying_run_count=len(scaled),
            headline="Not enough data for a 5K estimate",
            note=(
                "A labelled estimate needs at least two recent runs between "
                "3 km and 16 km. " + note
            ),
        )

    fastest = sorted(scaled)[:FASTEST_SAMPLE_LIMIT]
    seconds = int(round(median(fastest)))
    minutes = seconds // 60
    remainder = seconds % 60
    headline = f"About {minutes}:{remainder:02d} for 5K"
    return FiveKEstimate(
        available=True,
        estimated_seconds=seconds,
        qualifying_run_count=len(scaled),
        headline=headline,
        note=note,
    )
