"""Mock activity provider for development and tests.

Produces a fixed catalog of realistic runs. Identity is scoped per user in the
database unique constraint, so two accounts can import the same mock ids.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime

from app.integrations.exceptions import ProviderActivityNotFoundError
from app.integrations.mock.catalog import PROVIDER_NAME, build_mock_activities
from app.integrations.protocol import ProviderActivity


class MockActivityProvider:
    provider_name = PROVIDER_NAME

    def __init__(self, *, as_of: datetime | None = None) -> None:
        self._as_of = as_of

    async def get_activities(
        self,
        user_id: uuid.UUID,
        *,
        after: datetime | None = None,
    ) -> Sequence[ProviderActivity]:
        del user_id
        activities = build_mock_activities(as_of=self._as_of)
        if after is None:
            return activities
        return tuple(
            activity
            for activity in activities
            if activity.started_at is None or activity.started_at > after
        )

    async def get_activity(
        self,
        user_id: uuid.UUID,
        provider_activity_id: str,
    ) -> ProviderActivity:
        for activity in await self.get_activities(user_id):
            if activity.provider_activity_id == provider_activity_id:
                return activity
        raise ProviderActivityNotFoundError(self.provider_name, provider_activity_id)

    async def sync_activities(self, user_id: uuid.UUID) -> Sequence[ProviderActivity]:
        return await self.get_activities(user_id)
