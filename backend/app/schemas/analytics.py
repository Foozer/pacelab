"""Public analytics schemas. ORM models are never returned."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UnavailableMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: Literal[False] = False
    label: str
    headline: str
    note: str


class FiveKEstimateAvailable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: Literal[True] = True
    label: str = "5K estimate"
    headline: str
    note: str
    estimated_seconds: int
    qualifying_run_count: int


class EasyPaceAvailable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: Literal[True] = True
    label: str = "Easy pace"
    headline: str
    note: str
    pace_seconds_per_km: float
    comparable_pace_seconds_per_km: float
    average_heart_rate: float
    run_count: int
    heart_rate_min: int
    heart_rate_max: int


class AerobicEfficiencyAvailable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: Literal[True] = True
    label: str = "Aerobic efficiency"
    headline: str
    note: str
    direction: Literal["improving", "stable", "declining", "not_enough_data"]
    direction_label: str
    score: float | None = None
    relative_change_percent: float | None = None
    qualifying_run_count: int


FiveKEstimateMetric = FiveKEstimateAvailable | UnavailableMetric
EasyPaceMetric = EasyPaceAvailable | UnavailableMetric
AerobicEfficiencyMetric = AerobicEfficiencyAvailable | UnavailableMetric


class EasyRunningPointPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: UUID | None = None
    started_at: datetime
    pace_seconds_per_km: float
    heart_rate: float
    comparable_pace_seconds_per_km: float
    distance_meters: float


class EasyRunningResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heart_rate_min: int
    heart_rate_max: int
    run_count: int
    distance_meters: float
    average_pace_seconds_per_km: float | None
    average_heart_rate: float | None
    comparable_pace_seconds_per_km: float | None
    headline: str
    note: str
    points: list[EasyRunningPointPublic]


class AerobicPointPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: UUID | None = None
    started_at: datetime
    score: float
    pace_seconds_per_km: float
    heart_rate: float


class AerobicEfficiencyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: AerobicEfficiencyMetric
    points: list[AerobicPointPublic] = Field(default_factory=list)


class TrendActivityPointPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: UUID | None = None
    started_at: datetime
    pace_seconds_per_km: float | None
    average_heart_rate: float | None
    distance_meters: float | None
    comparable_pace_seconds_per_km: float | None


class WeeklyTrendPointPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    week_start: datetime
    distance_meters: float
    run_count: int


class TrendsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range_key: str
    period_start: datetime | None
    period_end: datetime
    heart_rate_min: int
    heart_rate_max: int
    points: list[TrendActivityPointPublic]
    weekly: list[WeeklyTrendPointPublic]
