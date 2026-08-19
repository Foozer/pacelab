"""Map FIT activity/session/record messages onto PaceLab provider DTOs.

``provider_activity_id`` (unique with user_id + provider ``fit``):

1. Prefer a session identity: SHA-256 of
   ``{UTC start YYYYMMDDTHHMMSSZ}|{activity_type}|{duration_seconds}|{distance_meters}``
   prefixed with ``session:``. Start comes from the session (or first record).
   Duration and distance use session totals when present, otherwise derived
   from samples. This is stable across re-upload of the same run even if the
   file bytes differ slightly.
2. If there is no start time, fall back to ``sha256:`` plus the hex digest of
   the uploaded (decompressed) bytes.

Never use a client-supplied id. GPS is not part of the identity.

One FIT file becomes one activity (first session summary + all record samples).
Latitude, longitude, and other position fields are ignored. Developer-data
messages are ignored. The original FIT is never written to disk by this parser.
"""

from __future__ import annotations

import gzip
import hashlib
import io
from datetime import UTC, datetime
from typing import Any

from garmin_fit_sdk import Decoder, Stream

from app.integrations.protocol import ProviderActivity, ProviderActivitySample

FIT_PROVIDER = "fit"
MAX_FIT_BYTES = 8 * 1024 * 1024

# FIT GPS fields. Listed so tests can prove we never copy them onto samples.
GPS_FIELD_NAMES = frozenset(
    {
        "position_lat",
        "position_long",
        "start_position_lat",
        "start_position_long",
        "end_position_lat",
        "end_position_long",
        "nec_lat",
        "nec_long",
        "swc_lat",
        "swc_long",
    }
)

_RUN_SPORTS = frozenset({"running", "run"})
_GENERIC_SPORTS = frozenset({"", "generic", "all", "none", "invalid"})


class FitParseError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def parse_fit_activity(data: bytes) -> ProviderActivity:
    """Parse FIT bytes in memory. Caller must discard ``data`` afterwards."""
    payload = _maybe_decompress(_require_nonempty(data))
    _require_fit_magic(payload)
    messages = _decode_messages(payload)
    session = _first(messages.get("session_mesgs"))
    records = list(messages.get("record_mesgs") or [])
    samples = _samples_from_records(records, session)
    started_at = _started_at(session, samples)
    if started_at is None:
        raise FitParseError(
            "INVALID_FIT",
            "This FIT file has no start time, so it cannot be imported.",
        )
    activity_type = map_fit_sport(
        _message_get(session, "sport"),
        _message_get(session, "sub_sport"),
    )
    duration_seconds = _duration_seconds(session, samples, started_at)
    distance_meters = _distance_meters(session, samples)
    provider_activity_id = compute_provider_activity_id(
        started_at=started_at,
        activity_type=activity_type,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        payload=payload,
    )
    average_speed = _optional_float(
        _message_get(session, "enhanced_avg_speed") or _message_get(session, "avg_speed")
    )
    if average_speed is None and distance_meters is not None and duration_seconds:
        average_speed = distance_meters / duration_seconds
    return ProviderActivity(
        provider=FIT_PROVIDER,
        provider_activity_id=provider_activity_id,
        activity_type=activity_type,
        started_at=started_at,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        average_speed=average_speed,
        average_heart_rate=_optional_int(_message_get(session, "avg_heart_rate")),
        max_heart_rate=_optional_int(_message_get(session, "max_heart_rate")),
        average_cadence=_optional_float(
            _message_get(session, "avg_running_cadence") or _message_get(session, "avg_cadence")
        ),
        elevation_gain=_optional_float(_message_get(session, "total_ascent")),
        calories=_optional_float(_message_get(session, "total_calories")),
        samples=tuple(samples),
    )


def compute_provider_activity_id(
    *,
    started_at: datetime | None,
    activity_type: str | None,
    duration_seconds: int | None,
    distance_meters: float | None,
    payload: bytes,
) -> str:
    if started_at is not None:
        started = started_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        duration = "" if duration_seconds is None else str(duration_seconds)
        distance = "" if distance_meters is None else str(int(round(distance_meters)))
        material = f"{started}|{activity_type or 'other'}|{duration}|{distance}"
        digest = hashlib.sha256(material.encode("ascii")).hexdigest()
        return f"session:{digest}"
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def map_fit_sport(sport: object, sub_sport: object | None = None) -> str:
    """Running (including treadmill) becomes ``run``; other sports keep their name."""
    del sub_sport
    sport_name = _norm_enum(sport)
    if sport_name in _RUN_SPORTS:
        return "run"
    if sport_name in _GENERIC_SPORTS:
        return "other"
    return sport_name


def _require_nonempty(data: bytes) -> bytes:
    if not data:
        raise FitParseError("EMPTY_FIT_FILE", "The FIT file was empty.")
    return data


def _maybe_decompress(data: bytes) -> bytes:
    if data[:2] != b"\x1f\x8b":
        if len(data) > MAX_FIT_BYTES:
            raise FitParseError(
                "FIT_FILE_TOO_LARGE",
                f"Each FIT file must be at most {MAX_FIT_BYTES} bytes.",
            )
        return data
    decoder = gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = decoder.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FIT_BYTES:
            raise FitParseError(
                "FIT_FILE_TOO_LARGE",
                f"Each FIT file must be at most {MAX_FIT_BYTES} bytes uncompressed.",
            )
        chunks.append(chunk)
    payload = b"".join(chunks)
    if not payload:
        raise FitParseError("EMPTY_FIT_FILE", "The compressed FIT file was empty.")
    return payload


def _require_fit_magic(data: bytes) -> None:
    if len(data) < 14 or data[8:12] != b".FIT":
        raise FitParseError("INVALID_FIT", "This file is not a valid FIT activity.")


def _decode_messages(data: bytes) -> dict[str, Any]:
    try:
        stream = Stream.from_byte_array(bytearray(data))
        decoder = Decoder(stream)
        messages, errors = decoder.read()
    except Exception as exc:
        raise FitParseError("INVALID_FIT", "This file is not a valid FIT activity.") from exc
    del errors
    decoded: dict[str, Any] = dict(messages)
    if not decoded.get("session_mesgs") and not decoded.get("record_mesgs"):
        raise FitParseError(
            "INVALID_FIT",
            "This FIT file has no activity session or samples.",
        )
    return decoded


def _samples_from_records(
    records: list[dict[str, Any]],
    session: dict[str, Any] | None,
) -> list[ProviderActivitySample]:
    started = _as_datetime(_message_get(session, "start_time"))
    by_elapsed: dict[int, ProviderActivitySample] = {}
    first_timestamp: datetime | None = None
    for record in records:
        safe = {key: value for key, value in record.items() if key not in GPS_FIELD_NAMES}
        timestamp = _as_datetime(safe.get("timestamp"))
        if timestamp is None:
            continue
        if first_timestamp is None:
            first_timestamp = timestamp
        origin = started or first_timestamp
        elapsed = max(0, int(round((timestamp - origin).total_seconds())))
        sample = ProviderActivitySample(
            timestamp=timestamp,
            elapsed_seconds=elapsed,
            distance_meters=_optional_float(safe.get("distance")),
            heart_rate=_optional_int(safe.get("heart_rate")),
            speed=_optional_float(safe.get("enhanced_speed") or safe.get("speed")),
            cadence=_optional_float(safe.get("cadence")),
            elevation=_optional_float(safe.get("enhanced_altitude") or safe.get("altitude")),
        )
        # Unique (activity, elapsed_seconds): keep the last sample in each second.
        by_elapsed[elapsed] = sample
    return [by_elapsed[key] for key in sorted(by_elapsed)]


def _started_at(
    session: dict[str, Any] | None,
    samples: list[ProviderActivitySample],
) -> datetime | None:
    started = _as_datetime(_message_get(session, "start_time"))
    if started is not None:
        return started
    if samples:
        return samples[0].timestamp
    return None


def _duration_seconds(
    session: dict[str, Any] | None,
    samples: list[ProviderActivitySample],
    started_at: datetime,
) -> int | None:
    for field_name in ("total_timer_time", "total_elapsed_time"):
        value = _optional_float(_message_get(session, field_name))
        if value is not None:
            return int(round(value))
    if samples:
        return max(0, int(round((samples[-1].timestamp - started_at).total_seconds())))
    return None


def _distance_meters(
    session: dict[str, Any] | None,
    samples: list[ProviderActivitySample],
) -> float | None:
    value = _optional_float(_message_get(session, "total_distance"))
    if value is not None:
        return value
    for sample in reversed(samples):
        if sample.distance_meters is not None:
            return sample.distance_meters
    return None


def _first(values: object) -> dict[str, Any] | None:
    if not isinstance(values, list) or not values:
        return None
    first = values[0]
    if isinstance(first, dict):
        return first
    return None


def _message_get(message: dict[str, Any] | None, key: str) -> object:
    if not message:
        return None
    return message.get(key)


def _norm_enum(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _as_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return None


def _optional_int(value: object) -> int | None:
    number = _optional_float(value)
    if number is None:
        return None
    return int(round(number))


def _optional_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
