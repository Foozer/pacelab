"""Privacy API schemas. ORM models are never returned directly."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.activity import ActivityDetail


class PasswordConfirmRequest(BaseModel):
    """Current password for irreversible privacy actions."""

    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=128)


class ExportAccount(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    email: EmailStr
    email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ExportProviderConnection(BaseModel):
    """Sync record only. Encrypted Strava tokens are never exported."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    last_sync_at: datetime | None


class UserDataExport(BaseModel):
    """A copy of what PaceLab stores for the current user. Not a Garmin Connect dump."""

    model_config = ConfigDict(extra="forbid")

    exported_at: datetime
    account: ExportAccount
    activities: list[ActivityDetail]
    provider_connections: list[ExportProviderConnection]


class ProviderConnectionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExportProviderConnection]
