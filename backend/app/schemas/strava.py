"""Public Strava connection status. Never includes tokens."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StravaStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configured: bool
    connected: bool
    needs_reconnect: bool
    last_sync_at: datetime | None
