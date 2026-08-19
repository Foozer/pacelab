"""Encrypted Strava OAuth tokens and CSRF state for official OAuth.

Revision ID: 004_strava_connections
Revises: 003_activities
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_strava_connections"
down_revision: str | None = "003_activities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strava_connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider_athlete_id", sa.String(length=64), nullable=False),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scopes", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.UniqueConstraint("user_id", name="uq_strava_connections_user_id"),
    )
    op.create_index(
        op.f("ix_strava_connections_user_id"),
        "strava_connections",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "strava_oauth_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state_hash"),
    )
    op.create_index(
        op.f("ix_strava_oauth_states_user_id"),
        "strava_oauth_states",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_strava_oauth_states_user_id"), table_name="strava_oauth_states")
    op.drop_table("strava_oauth_states")
    op.drop_index(op.f("ix_strava_connections_user_id"), table_name="strava_connections")
    op.drop_table("strava_connections")
