"""Official Strava OAuth routes. Identity always comes from the session cookie.

The OAuth callback is GET (Strava cannot send CSRF). Protection is the
unguessable `state` bound to this PaceLab user.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_strava_client
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import get_db
from app.integrations.strava.client import StravaApiClient
from app.models.user import User
from app.schemas.activity import ActivitySyncResponse
from app.schemas.strava import StravaStatusResponse
from app.services import strava as strava_service

router = APIRouter(prefix="/strava", tags=["strava"])


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


@router.get("/status", response_model=StravaStatusResponse)
async def strava_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StravaStatusResponse:
    return await strava_service.strava_status(
        db, user_id=user.id, settings=_settings(request)
    )


@router.get("/connect")
async def strava_connect(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RedirectResponse:
    url = await strava_service.start_connect(db, user=user, settings=_settings(request))
    return RedirectResponse(url=url, status_code=302)


@router.get("/callback")
async def strava_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    client: StravaApiClient = Depends(get_strava_client),
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    scope: str | None = Query(default=None),
) -> RedirectResponse:
    settings = _settings(request)
    try:
        await strava_service.complete_callback(
            db,
            user=user,
            settings=settings,
            client=client,
            code=code,
            state=state,
            error=error,
            scope=scope,
        )
    except AppError as exc:
        if exc.code == "STRAVA_OAUTH_DENIED":
            return RedirectResponse(
                url=strava_service.settings_redirect(settings, result="denied"),
                status_code=302,
            )
        raise
    return RedirectResponse(
        url=strava_service.settings_redirect(settings, result="connected"),
        status_code=302,
    )


@router.post("/sync", response_model=ActivitySyncResponse)
async def strava_sync(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    client: StravaApiClient = Depends(get_strava_client),
) -> ActivitySyncResponse:
    result = await strava_service.sync_strava_activities(
        db,
        user=user,
        settings=_settings(request),
        client=client,
    )
    return ActivitySyncResponse(
        provider=result.provider,
        created=result.created,
        updated=result.updated,
        total=result.total,
        last_sync_at=result.last_sync_at,
    )
