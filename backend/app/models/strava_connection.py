"""Per-user official Strava OAuth connection.

Access and refresh tokens are Fernet-encrypted. They must never appear in API
responses, logs, or privacy export. This is not a Garmin connection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class StravaConnection(Base):
    __tablename__ = "strava_connections"
    __table_args__ = (UniqueConstraint("user_id", name="uq_strava_connections_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    provider_athlete_id: Mapped[str] = mapped_column(String(64))
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str] = mapped_column(Text)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="connected")
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship(back_populates="strava_connection")


class StravaOAuthState(Base):
    """One-time OAuth `state` bound to a PaceLab user (hashed at rest)."""

    __tablename__ = "strava_oauth_states"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    state_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
