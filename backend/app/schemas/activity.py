"""Activity API schemas. ORM models are never returned directly."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActivitySamplePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    timestamp: datetime
    elapsed_seconds: int
    distance_meters: float | None
    heart_rate: int | None
    speed: float | None
    cadence: float | None
    elevation: float | None


class ActivitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    provider: str
    provider_activity_id: str
    activity_type: str | None
    started_at: datetime | None
    duration_seconds: int | None
    distance_meters: float | None
    average_speed: float | None
    average_heart_rate: int | None
    max_heart_rate: int | None
    average_cadence: float | None
    elevation_gain: float | None
    calories: float | None
    created_at: datetime
    updated_at: datetime


class ActivityDetail(ActivitySummary):
    samples: list[ActivitySamplePublic]


class ActivitySampleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    elapsed_seconds: int = Field(ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    heart_rate: int | None = Field(default=None, ge=0, le=400)
    speed: float | None = Field(default=None, ge=0)
    cadence: float | None = Field(default=None, ge=0)
    elevation: float | None = None


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=32)
    provider_activity_id: str = Field(min_length=1, max_length=128)
    activity_type: str | None = Field(default=None, max_length=64)
    started_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    average_speed: float | None = Field(default=None, ge=0)
    average_heart_rate: int | None = Field(default=None, ge=0, le=400)
    max_heart_rate: int | None = Field(default=None, ge=0, le=400)
    average_cadence: float | None = Field(default=None, ge=0)
    elevation_gain: float | None = Field(default=None, ge=0)
    calories: float | None = Field(default=None, ge=0)
    samples: list[ActivitySampleCreate] = Field(default_factory=list)


class ActivityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ActivitySummary]
    total: int
    limit: int
    offset: int
    last_sync_at: datetime | None


class ActivitySyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    created: int
    updated: int
    total: int
    last_sync_at: datetime
