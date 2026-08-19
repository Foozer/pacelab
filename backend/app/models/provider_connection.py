"""Per-user activity provider sync state.

This is not an OAuth token store. `last_sync_at` is last mock sync, last FIT import,
or last successful Strava pull. Encrypted Strava tokens live on `strava_connections`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ProviderConnection(Base):
    __tablename__ = "provider_connections"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "provider",
            name="uq_provider_connections_user_provider",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    user: Mapped[User] = relationship(back_populates="provider_connections")
