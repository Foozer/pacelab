"""Session-scoped privacy routes. Identity always comes from the session cookie."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_rate_limit, get_current_user, get_strava_client
from app.core.security import clear_csrf_cookie, clear_session_cookie
from app.db.session import get_db
from app.integrations.strava.client import StravaApiClient
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.privacy import (
    PasswordConfirmRequest,
    ProviderConnectionListResponse,
    UserDataExport,
)
from app.services import privacy as privacy_service
from app.services import strava as strava_service

router = APIRouter(prefix="/privacy", tags=["privacy"])

_EXPORT_LIMIT = 10
_DESTRUCTIVE_LIMIT = 5
_WINDOW_SECONDS = 3600


@router.get("/export")
async def export_my_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    enforce_rate_limit(
        request,
        "privacy-export",
        limit=_EXPORT_LIMIT,
        window_seconds=_WINDOW_SECONDS,
        identity=str(user.id),
    )
    payload: UserDataExport = await privacy_service.build_export(db, user)
    return Response(
        content=payload.model_dump_json(),
        media_type="application/json; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="pacelab-data.json"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/connections", response_model=ProviderConnectionListResponse)
async def list_connections(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProviderConnectionListResponse:
    items = await privacy_service.list_provider_connections(db, user_id=user.id)
    return ProviderConnectionListResponse(items=items)


@router.post("/running-data/delete", response_model=MessageResponse)
async def delete_running_data(
    payload: PasswordConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    enforce_rate_limit(
        request,
        "privacy-delete-running",
        limit=_DESTRUCTIVE_LIMIT,
        window_seconds=_WINDOW_SECONDS,
        identity=str(user.id),
    )
    privacy_service.require_current_password(user, payload.password)
    await privacy_service.delete_running_data(db, user)
    return MessageResponse(message="Your running data has been deleted.")


@router.post("/account/delete", response_model=MessageResponse)
async def delete_account(
    payload: PasswordConfirmRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    enforce_rate_limit(
        request,
        "privacy-delete-account",
        limit=_DESTRUCTIVE_LIMIT,
        window_seconds=_WINDOW_SECONDS,
        identity=str(user.id),
    )
    privacy_service.require_current_password(user, payload.password)
    await privacy_service.delete_account(db, user)
    clear_session_cookie(response, request.app.state.settings)
    clear_csrf_cookie(response, request.app.state.settings)
    return MessageResponse(message="Your PaceLab account has been deleted.")


@router.post("/providers/{provider}/disconnect", response_model=MessageResponse)
async def disconnect_provider(
    payload: PasswordConfirmRequest,
    request: Request,
    provider: Annotated[str, Path(min_length=1, max_length=32)],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    strava_client: StravaApiClient = Depends(get_strava_client),
) -> MessageResponse:
    enforce_rate_limit(
        request,
        "privacy-disconnect",
        limit=_DESTRUCTIVE_LIMIT,
        window_seconds=_WINDOW_SECONDS,
        identity=str(user.id),
    )
    privacy_service.require_current_password(user, payload.password)
    if provider == "strava":
        await strava_service.disconnect_strava(
            db,
            user=user,
            settings=request.app.state.settings,
            client=strava_client,
        )
        return MessageResponse(
            message=(
                "Strava is disconnected. PaceLab still has your imported runs. "
                "This is not a Garmin disconnect."
            )
        )
    await privacy_service.disconnect_provider(db, user, provider)
    return MessageResponse(
        message=(
            "PaceLab no longer has a sync record for that provider. "
            "Your stored runs are kept."
        )
    )
