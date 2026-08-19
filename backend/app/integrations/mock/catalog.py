"""Deterministic mock running catalog.

Twenty-four runs over eight weeks with mixed distances and a clear easy-pace
improvement at a comparable heart rate. Dates are relative to `as_of` so seed
data stays recent. No GPS coordinates are generated.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.integrations.protocol import ProviderActivity, ProviderActivitySample

PROVIDER_NAME = "mock"
SAMPLE_INTERVAL_SECONDS = 30


def build_mock_activities(*, as_of: datetime | None = None) -> tuple[ProviderActivity, ...]:
    origin = as_of or datetime.now(UTC)
    if origin.tzinfo is None:
        origin = origin.replace(tzinfo=UTC)
    plans = _run_plans()
    return tuple(_build_activity(index, plan, origin) for index, plan in enumerate(plans, start=1))


def _run_plans() -> list[dict[str, float | int | str]]:
    """Oldest week first so later charts read left-to-right as improvement."""
    plans: list[dict[str, float | int | str]] = []
    for week in range(8):
        fitness = week / 7
        easy_pace = 380.0 - (42.0 * fitness)
        easy_hr = int(round(150 - (6 * fitness)))
        long_km = 12.0 + week * 0.4
        days_ago_monday = (7 - week) * 7

        plans.append(
            {
                "days_ago": days_ago_monday + 1,
                "hour": 6,
                "minute": 30,
                "activity_type": "run",
                "kind": "easy",
                "distance_km": 6.2 if week % 2 == 0 else 7.4,
                "pace_sec_per_km": easy_pace,
                "average_hr": easy_hr,
                "cadence": 168 + week * 0.6,
                "elevation_gain": 28 + week * 2,
            }
        )
        if week % 2 == 0:
            plans.append(
                {
                    "days_ago": days_ago_monday + 3,
                    "hour": 18,
                    "minute": 10,
                    "activity_type": "run",
                    "kind": "tempo",
                    "distance_km": 8.0,
                    "pace_sec_per_km": easy_pace - 35,
                    "average_hr": easy_hr + 16,
                    "cadence": 174 + week * 0.4,
                    "elevation_gain": 40 + week,
                }
            )
        else:
            plans.append(
                {
                    "days_ago": days_ago_monday + 3,
                    "hour": 12,
                    "minute": 5,
                    "activity_type": "run",
                    "kind": "easy",
                    "distance_km": 8.1,
                    "pace_sec_per_km": easy_pace + 8,
                    "average_hr": easy_hr - 2,
                    "cadence": 166 + week * 0.5,
                    "elevation_gain": 55 + week * 3,
                }
            )
        plans.append(
            {
                "days_ago": days_ago_monday + 5,
                "hour": 8,
                "minute": 0,
                "activity_type": "run",
                "kind": "long",
                "distance_km": long_km,
                "pace_sec_per_km": easy_pace + 12,
                "average_hr": easy_hr + 4,
                "cadence": 164 + week * 0.3,
                "elevation_gain": 90 + week * 8,
            }
        )
    return plans


def _build_activity(
    index: int,
    plan: dict[str, float | int | str],
    origin: datetime,
) -> ProviderActivity:
    distance_km = float(plan["distance_km"])
    pace = float(plan["pace_sec_per_km"])
    distance_meters = round(distance_km * 1000, 1)
    duration_seconds = int(round(distance_km * pace))
    average_speed = distance_meters / duration_seconds if duration_seconds else None
    average_hr = int(plan["average_hr"])
    max_hr = average_hr + 12 + (index % 5)
    started_at = (origin - timedelta(days=int(plan["days_ago"]))).replace(
        hour=int(plan["hour"]),
        minute=int(plan["minute"]),
        second=0,
        microsecond=0,
    )
    calories = round(duration_seconds / 60 * (8.4 if plan["kind"] == "easy" else 10.2), 1)
    samples = _build_samples(
        started_at=started_at,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        average_hr=average_hr,
        max_hr=max_hr,
        cadence=float(plan["cadence"]),
        elevation_gain=float(plan["elevation_gain"]),
        index=index,
    )
    return ProviderActivity(
        provider=PROVIDER_NAME,
        provider_activity_id=f"mock-run-{index:03d}",
        activity_type=str(plan["activity_type"]),
        started_at=started_at,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        average_speed=average_speed,
        average_heart_rate=average_hr,
        max_heart_rate=max_hr,
        average_cadence=float(plan["cadence"]),
        elevation_gain=float(plan["elevation_gain"]),
        calories=calories,
        samples=samples,
    )


def _build_samples(
    *,
    started_at: datetime,
    duration_seconds: int,
    distance_meters: float,
    average_hr: int,
    max_hr: int,
    cadence: float,
    elevation_gain: float,
    index: int,
) -> tuple[ProviderActivitySample, ...]:
    if duration_seconds <= 0:
        return ()
    average_speed = distance_meters / duration_seconds
    elapsed_points = list(range(0, duration_seconds + 1, SAMPLE_INTERVAL_SECONDS))
    if elapsed_points[-1] != duration_seconds:
        elapsed_points.append(duration_seconds)

    samples: list[ProviderActivitySample] = []
    for elapsed in elapsed_points:
        frac = elapsed / duration_seconds
        wave = _tri(elapsed + index * 7)
        speed = max(0.5, average_speed * (1.0 + 0.045 * wave))
        heart_rate = int(average_hr + (max_hr - average_hr) * 0.35 * frac + 3 * wave)
        heart_rate = max(90, min(max_hr, heart_rate))
        samples.append(
            ProviderActivitySample(
                timestamp=started_at + timedelta(seconds=elapsed),
                elapsed_seconds=elapsed,
                distance_meters=round(distance_meters * frac, 1),
                heart_rate=heart_rate,
                speed=round(speed, 3),
                cadence=round(cadence + 2.0 * wave, 1),
                elevation=round(elevation_gain * frac, 1),
            )
        )
    return tuple(samples)


def _tri(value: int) -> float:
    """Deterministic -1..1 triangle wave. Avoids random() for lint/stability."""
    cycle = value % 10
    if cycle <= 5:
        return (cycle / 5) * 2 - 1
    return ((10 - cycle) / 5) * 2 - 1
