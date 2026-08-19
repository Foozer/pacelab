"""Build small FIT activity payloads for tests. Not used in production."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from garmin_fit_sdk import FIT_EPOCH_S, Encoder, Profile

FIXTURE_START = datetime(2026, 4, 1, 7, 30, tzinfo=UTC)
FIXTURE_DURATION_SECONDS = 110
FIXTURE_DISTANCE_METERS = 1100.0


def encode_activity(
    *,
    start: datetime = FIXTURE_START,
    sport: str = "running",
    sub_sport: str = "generic",
    include_gps: bool = True,
    sample_count: int = 12,
    interval_seconds: int = 10,
) -> bytes:
    start_fit = int(start.timestamp()) - FIT_EPOCH_S
    duration = (sample_count - 1) * interval_seconds
    end_fit = start_fit + duration
    encoder = Encoder()
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["FILE_ID"],
            "type": "activity",
            "manufacturer": "development",
            "product": 0,
            "time_created": start_fit,
            "serial_number": 1,
        }
    )
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["EVENT"],
            "timestamp": start_fit,
            "event": "timer",
            "event_type": "start",
        }
    )
    for index in range(sample_count):
        record: dict[str, Any] = {
            "mesg_num": Profile["mesg_num"]["RECORD"],
            "timestamp": start_fit + index * interval_seconds,
            "distance": index * 100,
            "enhanced_speed": 2.5,
            "heart_rate": 140 + index,
            "cadence": 170,
            "enhanced_altitude": 10 + index,
        }
        if include_gps:
            record["position_lat"] = 500000000
            record["position_long"] = 100000000 + index
        encoder.write_mesg(record)
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["EVENT"],
            "timestamp": end_fit,
            "event": "timer",
            "event_type": "stop",
        }
    )
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["SESSION"],
            "message_index": 0,
            "timestamp": end_fit,
            "start_time": start_fit,
            "total_elapsed_time": float(duration),
            "total_timer_time": float(duration),
            "total_distance": float((sample_count - 1) * 100),
            "sport": sport,
            "sub_sport": sub_sport,
            "avg_heart_rate": 145,
            "max_heart_rate": 140 + sample_count - 1,
            "avg_speed": 2.5,
            "avg_cadence": 170,
            "total_ascent": 12,
            "total_calories": 80,
        }
    )
    encoder.write_mesg(
        {
            "mesg_num": Profile["mesg_num"]["ACTIVITY"],
            "timestamp": end_fit,
            "num_sessions": 1,
            "total_timer_time": float(duration),
        }
    )
    return bytes(encoder.close())
