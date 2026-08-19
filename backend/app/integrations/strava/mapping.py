"""Map official Strava JSON onto PaceLab provider DTOs.

GPS (`latlng`, map polylines) is dropped. Indoor/treadmill runs without GPS still
import. Do not log raw payloads.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.integrations.protocol import ProviderActivity, ProviderActivitySample

PROVIDER_NAME = "strava"

_RUN_SPORTS = frozenset(
    {
        "run",
        "trailrun",
        "virtualrun",
        "treadmill",
        "trail_run",
        "virtual_run",
    }
)

# Official stream keys we persist. Never request latlng.
STREAM_KEYS = ("time", "distance", "heartrate", "cadence", "altitude", "velocity_smooth")


def map_strava_sport(sport_type: str | None, activity_type: str | None) -> str:
    """Run / treadmill / trail / virtual run → `run`. Other sports keep a short slug."""
    raw = sport_type or activity_type
    if not raw:
        return "other"
    compact = "".join(ch for ch in raw.lower() if ch.isalnum())
    if compact in _RUN_SPORTS:
        return "run"
    slug = raw.strip().lower().replace(" ", "_")
    if not slug:
        return "other"
    return slug[:64]


def parse_strava_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalised = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalised)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stream_data(streams: dict[str, Any], key: str) -> list[Any]:
    entry = streams.get(key)
    if isinstance(entry, dict):
        data = entry.get("data")
        if isinstance(data, list):
            return data
    return []


def samples_from_streams(
    *,
    started_at: datetime | None,
    streams: dict[str, Any],
) -> tuple[ProviderActivitySample, ...]:
    """Build samples from Strava streams. Ignores latlng even if the payload included it."""
    sanitized = {key: value for key, value in streams.items() if key != "latlng"}
    times = _stream_data(sanitized, "time")
    if not times:
        return ()
    distances = _stream_data(sanitized, "distance")
    heart_rates = _stream_data(sanitized, "heartrate")
    cadences = _stream_data(sanitized, "cadence")
    altitudes = _stream_data(sanitized, "altitude")
    speeds = _stream_data(sanitized, "velocity_smooth")
    origin = started_at or datetime.now(UTC)

    samples: list[ProviderActivitySample] = []
    seen_elapsed: set[int] = set()
    for index, raw_elapsed in enumerate(times):
        elapsed = _as_int(raw_elapsed)
        if elapsed is None or elapsed < 0 or elapsed in seen_elapsed:
            continue
        seen_elapsed.add(elapsed)
        samples.append(
            ProviderActivitySample(
                timestamp=origin + timedelta(seconds=elapsed),
                elapsed_seconds=elapsed,
                distance_meters=_as_float(distances[index]) if index < len(distances) else None,
                heart_rate=_as_int(heart_rates[index]) if index < len(heart_rates) else None,
                speed=_as_float(speeds[index]) if index < len(speeds) else None,
                cadence=_as_float(cadences[index]) if index < len(cadences) else None,
                elevation=_as_float(altitudes[index]) if index < len(altitudes) else None,
            )
        )
    return tuple(samples)


def activity_from_strava(
    summary: dict[str, Any],
    *,
    streams: dict[str, Any] | None = None,
) -> ProviderActivity:
    activity_id = summary.get("id")
    if activity_id is None:
        raise ValueError("Strava activity is missing id")
    started_at = parse_strava_datetime(
        summary.get("start_date") if isinstance(summary.get("start_date"), str) else None
    )
    duration = _as_int(summary.get("elapsed_time"))
    samples = samples_from_streams(started_at=started_at, streams=streams or {})
    if isinstance(activity_id, (int, float)):
        provider_activity_id = str(int(activity_id))
    else:
        provider_activity_id = str(activity_id)
    return ProviderActivity(
        provider=PROVIDER_NAME,
        provider_activity_id=provider_activity_id,
        activity_type=map_strava_sport(
            summary.get("sport_type") if isinstance(summary.get("sport_type"), str) else None,
            summary.get("type") if isinstance(summary.get("type"), str) else None,
        ),
        started_at=started_at,
        duration_seconds=duration,
        distance_meters=_as_float(summary.get("distance")),
        average_speed=_as_float(summary.get("average_speed")),
        average_heart_rate=_as_int(summary.get("average_heartrate")),
        max_heart_rate=_as_int(summary.get("max_heartrate")),
        average_cadence=_as_float(summary.get("average_cadence")),
        elevation_gain=_as_float(summary.get("total_elevation_gain")),
        calories=_as_float(summary.get("calories")),
        samples=samples,
    )
