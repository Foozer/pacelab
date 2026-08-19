"""Activity provider protocol and transport-neutral DTOs.

Providers return these dataclasses. Persistence and HTTP schemas live elsewhere
so a future Garmin implementation can map official API payloads without the
rest of the app depending on Garmin field names.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderActivitySample:
    timestamp: datetime
    elapsed_seconds: int
    distance_meters: float | None = None
    heart_rate: int | None = None
    speed: float | None = None
    cadence: float | None = None
    elevation: float | None = None


@dataclass(frozen=True, slots=True)
class ProviderActivity:
    provider: str
    provider_activity_id: str
    activity_type: str | None
    started_at: datetime | None
    duration_seconds: int | None = None
    distance_meters: float | None = None
    average_speed: float | None = None
    average_heart_rate: int | None = None
    max_heart_rate: int | None = None
    average_cadence: float | None = None
    elevation_gain: float | None = None
    calories: float | None = None
    samples: tuple[ProviderActivitySample, ...] = field(default_factory=tuple)


class ActivityProvider(Protocol):
    """Source of running activities for a PaceLab user.

    Implementations must not accept Garmin usernames or passwords. Live Garmin
    OAuth is deferred until the official Connect Developer Program accepts new
    apps. Garmin-recorded runs enter PaceLab today via FIT-file upload, not
    this protocol. Official Strava OAuth is a per-user connection
    (`StravaActivityProvider`), not ACTIVITY_PROVIDER.
    """

    provider_name: str

    async def get_activities(
        self,
        user_id: uuid.UUID,
        *,
        after: datetime | None = None,
    ) -> Sequence[ProviderActivity]: ...

    async def get_activity(
        self,
        user_id: uuid.UUID,
        provider_activity_id: str,
    ) -> ProviderActivity: ...

    async def sync_activities(self, user_id: uuid.UUID) -> Sequence[ProviderActivity]: ...
