"""Strava provider stub.

Do not add HTTP clients or unofficial Strava libraries here. Official OAuth
arrives in Phase 8. Until then PaceLab does not claim a Strava connection.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import NoReturn

from app.integrations.exceptions import ProviderNotConfiguredError
from app.integrations.protocol import ProviderActivity

_MESSAGE = (
    "Strava import is not implemented. Official Strava OAuth will be added in "
    "Phase 8. PaceLab does not call strava.com and does not store Strava "
    "usernames or passwords."
)


class StravaActivityProvider:
    provider_name = "strava"

    def _unavailable(self) -> NoReturn:
        raise ProviderNotConfiguredError(provider=self.provider_name, message=_MESSAGE)

    async def get_activities(
        self,
        user_id: uuid.UUID,
        *,
        after: datetime | None = None,
    ) -> Sequence[ProviderActivity]:
        del user_id, after
        self._unavailable()

    async def get_activity(
        self,
        user_id: uuid.UUID,
        provider_activity_id: str,
    ) -> ProviderActivity:
        del user_id, provider_activity_id
        self._unavailable()

    async def sync_activities(self, user_id: uuid.UUID) -> Sequence[ProviderActivity]:
        del user_id
        self._unavailable()
