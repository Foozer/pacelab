"""Initial schema baseline.

Revision ID: 001_initial
Revises:
Create Date: 2026-08-18

Phase 1 establishes the Alembic pipeline only. Domain tables (users, activities,
subscriptions, Garmin connections) are added in later phases.
"""

from collections.abc import Sequence

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
