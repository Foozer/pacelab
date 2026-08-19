"""Unit tests for running analytics and 5K estimation (Phase 5)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.services.performance_prediction import estimate_5k_time, riegel_equivalent_seconds
from app.services.running_analytics import (
    ActivityObservation,
    SampleObservation,
    calculate_aerobic_efficiency,
    calculate_easy_pace_trend,
    calculate_trends,
    calculate_weekly_distance,
    moving_effort_from_activity,
    parse_trend_range,
    valid_moving_samples,
)
from app.services.running_metrics import (
    HeartRateBand,
    VolumeRow,
    calculate_pace,
    calculate_pace_at_heart_rate,
    calculate_training_volume,
    is_run_activity,
)


def _run(
    *,
    started: datetime,
    distance_meters: float,
    duration_seconds: int,
    heart_rate: int,
    activity_type: str = "run",
    samples: tuple[SampleObservation, ...] = (),
) -> ActivityObservation:
    return ActivityObservation(
        id=uuid4(),
        activity_type=activity_type,
        started_at=started,
        distance_meters=distance_meters,
        duration_seconds=duration_seconds,
        average_heart_rate=heart_rate,
        samples=samples,
    )


def test_heart_rate_band_rejects_inverted_and_implausible() -> None:
    with pytest.raises(ValueError):
        HeartRateBand(minimum=150, maximum=140)
    with pytest.raises(ValueError):
        HeartRateBand(minimum=150, maximum=150)
    with pytest.raises(ValueError):
        HeartRateBand(minimum=10, maximum=140)
    with pytest.raises(ValueError):
        HeartRateBand(minimum=140, maximum=400)


def test_pace_at_heart_rate_scales_linearly() -> None:
    comparable = calculate_pace_at_heart_rate(
        pace_seconds_per_km=360.0,
        heart_rate=150,
        reference_heart_rate=145,
    )
    assert comparable == pytest.approx(360.0 * 150 / 145)


def test_valid_moving_samples_drop_pauses_and_nonsense_hr() -> None:
    samples = (
        SampleObservation(heart_rate=0, speed=2.8),
        SampleObservation(heart_rate=145, speed=0.0),
        SampleObservation(heart_rate=40, speed=2.8),
        SampleObservation(heart_rate=145, speed=2.7),
        SampleObservation(heart_rate=None, speed=2.7),
        SampleObservation(heart_rate=148, speed=None),
    )
    kept = valid_moving_samples(samples)
    assert len(kept) == 1
    assert kept[0].heart_rate == 145


def test_non_run_types_are_excluded_from_effort() -> None:
    ride = _run(
        started=datetime(2026, 6, 1, tzinfo=UTC),
        distance_meters=20000,
        duration_seconds=3600,
        heart_rate=140,
        activity_type="ride",
    )
    assert is_run_activity("ride") is False
    assert moving_effort_from_activity(ride) is None


def test_hr_band_filter_uses_activity_average_without_samples() -> None:
    band = HeartRateBand(minimum=140, maximum=150)
    origin = datetime(2026, 6, 1, tzinfo=UTC)
    in_band = _run(
        started=origin,
        distance_meters=5000,
        duration_seconds=1900,
        heart_rate=145,
    )
    out_of_band = _run(
        started=origin + timedelta(days=1),
        distance_meters=5000,
        duration_seconds=1600,
        heart_rate=168,
    )
    result = calculate_easy_pace_trend([in_band, out_of_band], band)
    assert result.run_count == 1
    assert result.average_heart_rate == 145
    assert result.average_pace_seconds_per_km == pytest.approx(380.0)


def test_easy_pace_trend_reads_as_improving() -> None:
    band = HeartRateBand(minimum=140, maximum=150)
    origin = datetime(2026, 4, 1, tzinfo=UTC)
    activities = [
        _run(
            started=origin + timedelta(days=index * 7),
            distance_meters=6000,
            duration_seconds=int(6000 / 1000 * (390 - index * 8)),
            heart_rate=146,
        )
        for index in range(6)
    ]
    result = calculate_easy_pace_trend(activities, band)
    assert result.run_count == 6
    assert result.headline == "Your easy pace is improving"
    assert result.points[0].comparable_pace_seconds_per_km > (
        result.points[-1].comparable_pace_seconds_per_km
    )


def test_aerobic_efficiency_improves_when_faster_at_similar_hr() -> None:
    origin = datetime(2026, 4, 1, tzinfo=UTC)
    activities = [
        _run(
            started=origin + timedelta(days=index * 7),
            distance_meters=7000,
            duration_seconds=int(7000 / 1000 * (380 - index * 10)),
            heart_rate=148,
        )
        for index in range(6)
    ]
    result = calculate_aerobic_efficiency(activities)
    assert result.direction == "improving"
    assert result.headline == "Your easy pace is improving"
    assert result.qualifying_run_count == 6
    assert result.score is not None
    assert result.points[0].score < result.points[-1].score


def test_aerobic_efficiency_drops_pauses_and_hard_efforts() -> None:
    origin = datetime(2026, 5, 1, tzinfo=UTC)
    paused = _run(
        started=origin,
        distance_meters=5000,
        duration_seconds=1800,
        heart_rate=145,
        samples=(
            SampleObservation(heart_rate=145, speed=0.0),
            SampleObservation(heart_rate=0, speed=2.8),
            SampleObservation(heart_rate=145, speed=2.7),
            SampleObservation(heart_rate=146, speed=2.71),
            SampleObservation(heart_rate=144, speed=2.69),
        ),
    )
    interval = _run(
        started=origin + timedelta(days=1),
        distance_meters=5000,
        duration_seconds=1200,
        heart_rate=178,
    )
    result = calculate_aerobic_efficiency([paused, interval])
    assert result.qualifying_run_count == 1
    assert result.direction == "not_enough_data"
    assert result.points[0].heart_rate == pytest.approx(145.0, abs=1.5)


def test_aerobic_efficiency_insufficient_data() -> None:
    only = _run(
        started=datetime(2026, 6, 1, tzinfo=UTC),
        distance_meters=5000,
        duration_seconds=1800,
        heart_rate=145,
    )
    result = calculate_aerobic_efficiency([only])
    assert result.direction == "not_enough_data"
    assert "enough data" in result.headline.lower()


def test_weekly_volume_helper_still_counts_window() -> None:
    period_start = datetime(2026, 8, 12, tzinfo=UTC)
    period_end = datetime(2026, 8, 19, tzinfo=UTC)
    rows = [
        VolumeRow(
            started_at=datetime(2026, 8, 18, 7, 0, tzinfo=UTC),
            distance_meters=5000,
            duration_seconds=1800,
        ),
        VolumeRow(
            started_at=datetime(2026, 8, 11, 7, 0, tzinfo=UTC),
            distance_meters=8000,
            duration_seconds=2400,
        ),
    ]
    volume = calculate_training_volume(rows, period_start=period_start, period_end=period_end)
    assert volume.run_count == 1
    assert volume.distance_meters == 5000


def test_weekly_distance_groups_by_monday() -> None:
    origin = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)  # Monday
    activities = [
        _run(started=origin, distance_meters=5000, duration_seconds=1800, heart_rate=145),
        _run(
            started=origin + timedelta(days=2),
            distance_meters=7000,
            duration_seconds=2400,
            heart_rate=145,
        ),
        _run(
            started=origin + timedelta(days=7),
            distance_meters=4000,
            duration_seconds=1500,
            heart_rate=145,
        ),
    ]
    weekly = calculate_weekly_distance(
        activities,
        started_after=origin,
        period_end=origin + timedelta(days=8),
    )
    assert weekly[0].week_start.date().isoformat() == "2026-08-10"
    assert weekly[0].distance_meters == 12000
    assert weekly[0].run_count == 2
    assert weekly[1].distance_meters == 4000
    assert weekly[1].run_count == 1


def test_riegel_and_5k_estimate_are_deterministic() -> None:
    scaled = riegel_equivalent_seconds(duration_seconds=1800, distance_meters=5000)
    assert scaled == pytest.approx(1800.0)
    longer = riegel_equivalent_seconds(duration_seconds=3600, distance_meters=10000)
    assert longer > 1700
    assert longer < 1800

    now = datetime(2026, 8, 19, tzinfo=UTC)
    activities = [
        _run(
            started=now - timedelta(days=3),
            distance_meters=5000,
            duration_seconds=1800,
            heart_rate=160,
        ),
        _run(
            started=now - timedelta(days=10),
            distance_meters=8000,
            duration_seconds=3000,
            heart_rate=155,
        ),
        _run(
            started=now - timedelta(days=80),
            distance_meters=5000,
            duration_seconds=1500,
            heart_rate=160,
        ),
    ]
    estimate = estimate_5k_time(activities, now=now)
    assert estimate.available is True
    assert estimate.estimated_seconds is not None
    assert estimate.qualifying_run_count == 2
    again = estimate_5k_time(activities, now=now)
    assert again.estimated_seconds == estimate.estimated_seconds
    assert "estimate" in estimate.note.lower()
    assert "race prediction" in estimate.note.lower()


def test_5k_estimate_unavailable_when_thin() -> None:
    now = datetime(2026, 8, 19, tzinfo=UTC)
    only = _run(
        started=now - timedelta(days=1),
        distance_meters=5000,
        duration_seconds=1800,
        heart_rate=150,
    )
    estimate = estimate_5k_time([only], now=now)
    assert estimate.available is False
    assert estimate.estimated_seconds is None

    too_short = _run(
        started=now - timedelta(days=1),
        distance_meters=1500,
        duration_seconds=400,
        heart_rate=150,
    )
    empty = estimate_5k_time([too_short, only], now=now)
    assert empty.available is False


def test_trends_range_and_pace_series() -> None:
    now = datetime(2026, 8, 19, tzinfo=UTC)
    band = HeartRateBand(minimum=140, maximum=150)
    activities = [
        _run(
            started=now - timedelta(days=10),
            distance_meters=5000,
            duration_seconds=1900,
            heart_rate=145,
        ),
        _run(
            started=now - timedelta(days=40),
            distance_meters=6000,
            duration_seconds=2400,
            heart_rate=144,
        ),
        _run(
            started=now - timedelta(days=40),
            distance_meters=20000,
            duration_seconds=3600,
            heart_rate=130,
            activity_type="ride",
        ),
    ]
    eight = calculate_trends(activities, band, range_key="4w", now=now)
    assert len(eight.points) == 1
    assert eight.points[0].pace_seconds_per_km == pytest.approx(calculate_pace(
        distance_meters=5000,
        duration_seconds=1900,
    ) or 0)
    assert eight.points[0].comparable_pace_seconds_per_km is not None
    all_time = calculate_trends(activities, band, range_key="all", now=now)
    assert len(all_time.points) == 2


def test_parse_trend_range_rejects_unknown() -> None:
    assert parse_trend_range("8w") == "8w"
    with pytest.raises(ValueError):
        parse_trend_range("2d")
