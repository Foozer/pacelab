"""Authenticated activity routes. Identity always comes from the session cookie."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_activity_provider, get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.integrations.protocol import ActivityProvider
from app.models.user import User
from app.schemas.activity import (
    ActivityCreate,
    ActivityDetail,
    ActivityListResponse,
    ActivitySummary,
    ActivitySyncResponse,
)
from app.services import activities as activity_service
from app.services.activity_sync import sync_user_activities

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: ActivityProvider = Depends(get_activity_provider),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    activity_type: str | None = Query(default=None, min_length=1, max_length=64),
) -> ActivityListResponse:
    items, total = await activity_service.list_activities_for_user(
        db,
        user_id=user.id,
        limit=limit,
        offset=offset,
        started_on_or_after=from_date,
        started_on_or_before=to_date,
        activity_type=activity_type,
    )
    last_sync_at = await activity_service.get_last_sync_at(
        db,
        user_id=user.id,
        provider=provider.provider_name,
    )
    activity_types = await activity_service.list_activity_types_for_user(db, user_id=user.id)
    return ActivityListResponse(
        items=[ActivitySummary.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        last_sync_at=last_sync_at,
        activity_types=activity_types,
    )


@router.post("/sync", response_model=ActivitySyncResponse)
async def sync_activities(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    provider: ActivityProvider = Depends(get_activity_provider),
) -> ActivitySyncResponse:
    result = await sync_user_activities(db, user_id=user.id, provider=provider)
    return ActivitySyncResponse(
        provider=result.provider,
        created=result.created,
        updated=result.updated,
        total=result.total,
        last_sync_at=result.last_sync_at,
    )


@router.post("", response_model=ActivityDetail, status_code=status.HTTP_201_CREATED)
async def create_activity(
    payload: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityDetail:
    activity = await activity_service.create_activity_for_user(
        db,
        user_id=user.id,
        payload=payload,
    )
    loaded = await activity_service.get_activity_for_user(
        db,
        user_id=user.id,
        activity_id=activity.id,
    )
    if loaded is None:
        raise AppError("ACTIVITY_NOT_FOUND", "Activity not found", status_code=404)
    return ActivityDetail.model_validate(loaded)


@router.get("/{activity_id}", response_model=ActivityDetail)
async def read_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ActivityDetail:
    activity = await activity_service.get_activity_for_user(
        db,
        user_id=user.id,
        activity_id=activity_id,
    )
    if activity is None:
        raise AppError("ACTIVITY_NOT_FOUND", "Activity not found", status_code=404)
    return ActivityDetail.model_validate(activity)
