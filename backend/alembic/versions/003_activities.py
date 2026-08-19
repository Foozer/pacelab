"""Activities, samples, and provider sync state.

Revision ID: 003_activities
Revises: 002_users_sessions
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_activities"
down_revision: str | None = "002_users_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_provider_connections_user_provider"),
    )
    op.create_index(
        op.f("ix_provider_connections_user_id"),
        "provider_connections",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_activity_id", sa.String(length=128), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("average_speed", sa.Float(), nullable=True),
        sa.Column("average_heart_rate", sa.Integer(), nullable=True),
        sa.Column("max_heart_rate", sa.Integer(), nullable=True),
        sa.Column("average_cadence", sa.Float(), nullable=True),
        sa.Column("elevation_gain", sa.Float(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "provider",
            "provider_activity_id",
            name="uq_activities_user_provider_activity",
        ),
    )
    op.create_index(op.f("ix_activities_user_id"), "activities", ["user_id"], unique=False)
    op.create_index(
        "ix_activities_user_started_at",
        "activities",
        ["user_id", "started_at"],
        unique=False,
    )

    op.create_table(
        "activity_samples",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("cadence", sa.Float(), nullable=True),
        sa.Column("elevation", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "activity_id",
            "elapsed_seconds",
            name="uq_activity_samples_activity_elapsed",
        ),
    )
    op.create_index(
        op.f("ix_activity_samples_activity_id"),
        "activity_samples",
        ["activity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_activity_samples_activity_id"), table_name="activity_samples")
    op.drop_table("activity_samples")
    op.drop_index("ix_activities_user_started_at", table_name="activities")
    op.drop_index(op.f("ix_activities_user_id"), table_name="activities")
    op.drop_table("activities")
    op.drop_index(op.f("ix_provider_connections_user_id"), table_name="provider_connections")
    op.drop_table("provider_connections")
