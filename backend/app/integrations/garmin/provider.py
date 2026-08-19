"""Garmin Connect provider stub.

Do not add HTTP clients, URLs, or unofficial Garmin libraries here. Official
OAuth 2.0 and Connect Developer Program endpoints arrive in Phase 7 when
credentials exist. Until then PaceLab uses MockActivityProvider.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import NoReturn

from app.integrations.exceptions import ProviderNotConfiguredError
from app.integrations.protocol import ProviderActivity

_MESSAGE = (
    "Live Garmin Connect import is not implemented. Official OAuth 2.0 will be "
    "added when Garmin developer credentials exist. PaceLab does not scrape "
    "Garmin or store Garmin usernames or passwords."
)


class GarminActivityProvider:
    provider_name = "garmin"

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
