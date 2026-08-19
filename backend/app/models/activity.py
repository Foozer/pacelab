"""Normalised running activities owned by a PaceLab user.

GPS coordinates are intentionally omitted: location data is sensitive and is not
required for MVP pace/heart-rate analytics.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Activity(Base):
    __tablename__ = "activities"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider",
            "provider_activity_id",
            name="uq_activities_user_provider_activity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32))
    provider_activity_id: Mapped[str] = mapped_column(String(128))
    activity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_cadence: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
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

    user: Mapped[User] = relationship(back_populates="activities")
    samples: Mapped[list[ActivitySample]] = relationship(
        back_populates="activity",
        cascade="all, delete-orphan",
        order_by="ActivitySample.elapsed_seconds",
    )


class ActivitySample(Base):
    __tablename__ = "activity_samples"
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "elapsed_seconds",
            name="uq_activity_samples_activity_elapsed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    activity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    elapsed_seconds: Mapped[int] = mapped_column(Integer)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    cadence: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation: Mapped[float | None] = mapped_column(Float, nullable=True)

    activity: Mapped[Activity] = relationship(back_populates="samples")
