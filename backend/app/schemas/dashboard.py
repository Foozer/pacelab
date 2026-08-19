"""Dashboard API schemas. Phase 5 metrics are explicit placeholders, not zeros."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.activity import ActivitySummary


class UpcomingMetric(BaseModel):
    """A metric that has a dashboard slot but is not calculated until a later phase."""

    model_config = ConfigDict(extra="forbid")

    available: Literal[False] = False
    label: str
    note: str


class WeeklyVolumePublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_count: int
    distance_meters: float
    duration_seconds: int
    period_start: datetime
    period_end: datetime


class PaceHeartRatePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: UUID
    started_at: datetime
    pace_seconds_per_km: float | None
    average_heart_rate: int | None
    distance_meters: float | None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekly: WeeklyVolumePublic
    recent_activities: list[ActivitySummary]
    pace_heart_rate_trend: list[PaceHeartRatePoint]
    five_k_estimate: UpcomingMetric
    easy_pace: UpcomingMetric
    aerobic_efficiency: UpcomingMetric
