"""Unit tests for simple running aggregates (Phase 4)."""

from datetime import UTC, datetime

import pytest

from app.services.running_metrics import (
    VolumeRow,
    calculate_pace,
    calculate_pace_from_speed,
    calculate_training_volume,
)


def test_calculate_pace_for_five_k() -> None:
    pace = calculate_pace(distance_meters=5000, duration_seconds=1800)
    assert pace == 360.0


def test_calculate_pace_rejects_unusable_inputs() -> None:
    assert calculate_pace(distance_meters=None, duration_seconds=1800) is None
    assert calculate_pace(distance_meters=5000, duration_seconds=None) is None
    assert calculate_pace(distance_meters=0, duration_seconds=1800) is None
    assert calculate_pace(distance_meters=5000, duration_seconds=0) is None


def test_calculate_pace_from_speed() -> None:
    assert calculate_pace_from_speed(2.5) == 400.0
    assert calculate_pace_from_speed(0) is None
    assert calculate_pace_from_speed(None) is None


def test_training_volume_counts_only_rows_in_window() -> None:
    period_start = datetime(2026, 8, 12, tzinfo=UTC)
    period_end = datetime(2026, 8, 19, tzinfo=UTC)
    rows = [
        VolumeRow(
            started_at=datetime(2026, 8, 18, 7, 0, tzinfo=UTC),
            distance_meters=5000,
            duration_seconds=1800,
        ),
        VolumeRow(
            started_at=datetime(2026, 8, 13, 7, 0, tzinfo=UTC),
            distance_meters=10000,
            duration_seconds=3600,
        ),
        VolumeRow(
            started_at=datetime(2026, 8, 11, 7, 0, tzinfo=UTC),
            distance_meters=8000,
            duration_seconds=2400,
        ),
        VolumeRow(
            started_at=datetime(2026, 8, 19, 0, 0, tzinfo=UTC),
            distance_meters=1000,
            duration_seconds=300,
        ),
        VolumeRow(started_at=None, distance_meters=3000, duration_seconds=900),
        VolumeRow(
            started_at=datetime(2026, 8, 14, 7, 0, tzinfo=UTC),
            distance_meters=None,
            duration_seconds=None,
        ),
    ]
    volume = calculate_training_volume(rows, period_start=period_start, period_end=period_end)
    assert volume.run_count == 3
    assert volume.distance_meters == 15000
    assert volume.duration_seconds == 5400
    assert volume.period_start == period_start
    assert volume.period_end == period_end


def test_training_volume_rejects_inverted_period() -> None:
    start = datetime(2026, 8, 19, tzinfo=UTC)
    end = datetime(2026, 8, 12, tzinfo=UTC)
    with pytest.raises(ValueError):
        calculate_training_volume([], period_start=start, period_end=end)
