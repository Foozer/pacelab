"""Official Strava activity provider.

Maps Strava JSON to ProviderActivity. Persistence stays in sync_user_activities.
Does not store GPS. Sync window (this module):

- First sync: activities with `start_date` after now−90 days, at most 3 list pages
  of 30 (90 summaries). Streams are fetched for at most 40 of those activities
  so one click cannot exhaust Strava’s non-upload 15-minute budget.
- Incremental sync: `after` is the later of last successful `last_sync_at` and
  the newest stored Strava `started_at` for this user (passed in by the service).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import Any

from app.core.errors import AppError
from app.integrations.exceptions import ProviderActivityNotFoundError
from app.integrations.protocol import ProviderActivity
from app.integrations.strava.client import StravaApiClient, StravaAuthError
from app.integrations.strava.mapping import activity_from_strava

logger = logging.getLogger(__name__)

FIRST_SYNC_MAX_PAGES = 3
LIST_PER_PAGE = 30
MAX_STREAM_FETCHES = 40


class StravaActivityProvider:
    provider_name = "strava"

    def __init__(
        self,
        client: StravaApiClient,
        *,
        access_token: str,
        after: datetime | None = None,
        on_auth_failure: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._client = client
        self._access_token = access_token
        self._after = after
        self._on_auth_failure = on_auth_failure

    async def get_activities(
        self,
        user_id: uuid.UUID,
        *,
        after: datetime | None = None,
    ) -> Sequence[ProviderActivity]:
        del user_id
        cutoff = after if after is not None else self._after
        summaries: list[dict[str, Any]] = []
        try:
            for page in range(1, FIRST_SYNC_MAX_PAGES + 1):
                batch = await self._client.list_athlete_activities(
                    self._access_token,
                    after=cutoff,
                    page=page,
                    per_page=LIST_PER_PAGE,
                )
                summaries.extend(batch)
                if len(batch) < LIST_PER_PAGE:
                    break
        except StravaAuthError:
            await self._notify_auth_failure()
            raise

        results: list[ProviderActivity] = []
        stream_fetches = 0
        for summary in summaries:
            activity_id = summary.get("id")
            streams: dict[str, Any] = {}
            if activity_id is not None and stream_fetches < MAX_STREAM_FETCHES:
                try:
                    streams = await self._client.get_activity_streams(
                        self._access_token,
                        str(int(activity_id))
                        if isinstance(activity_id, (int, float))
                        else str(activity_id),
                    )
                    stream_fetches += 1
                except StravaAuthError:
                    await self._notify_auth_failure()
                    raise
                except AppError:
                    logger.info("Skipping Strava streams for one activity after a non-auth failure")
                    streams = {}
            results.append(activity_from_strava(summary, streams=streams))
        logger.info("Fetched %s Strava activities (streams for %s)", len(results), stream_fetches)
        return results

    async def get_activity(
        self,
        user_id: uuid.UUID,
        provider_activity_id: str,
    ) -> ProviderActivity:
        del user_id
        raise ProviderActivityNotFoundError(self.provider_name, provider_activity_id)

    async def sync_activities(self, user_id: uuid.UUID) -> Sequence[ProviderActivity]:
        return await self.get_activities(user_id, after=self._after)

    async def _notify_auth_failure(self) -> None:
        callback = self._on_auth_failure
        if callable(callback):
            await callback()
