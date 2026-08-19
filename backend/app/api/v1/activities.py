"""Authenticated activity routes. Identity always comes from the session cookie."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_rate_limit, get_activity_provider, get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.integrations.fit.parser import FitParseError
from app.integrations.protocol import ActivityProvider
from app.models.user import User
from app.schemas.activity import (
    ActivityCreate,
    ActivityDetail,
    ActivityListResponse,
    ActivitySummary,
    ActivitySyncResponse,
    FitImportErrorPublic,
    FitImportFileResult,
    FitImportResponse,
)
from app.services import activities as activity_service
from app.services import fit_import as fit_import_service
from app.services.activity_sync import sync_user_activities

router = APIRouter(prefix="/activities", tags=["activities"])


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
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
    last_sync_at = await activity_service.get_latest_sync_at(
        db,
        user_id=user.id,
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


@router.post("/import/fit", response_model=FitImportResponse)
async def import_fit_activities(
    request: Request,
    files: Annotated[list[UploadFile], File()],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FitImportResponse:
    enforce_rate_limit(
        request,
        "fit-import",
        limit=20,
        window_seconds=3600,
        identity=str(user.id),
    )
    if len(files) > fit_import_service.MAX_FIT_FILES_PER_REQUEST:
        raise AppError(
            "TOO_MANY_FIT_FILES",
            f"Upload at most {fit_import_service.MAX_FIT_FILES_PER_REQUEST} FIT files at a time.",
            status_code=422,
        )

    uploads: list[tuple[str, str | None, bytes]] = []
    for upload in files:
        filename = upload.filename or "upload.fit"
        try:
            payload = await upload.read(fit_import_service.MAX_FIT_FILE_BYTES + 1)
        finally:
            await upload.close()
        uploads.append((filename, upload.content_type, payload))

    try:
        result = await fit_import_service.import_fit_files(
            db,
            user_id=user.id,
            uploads=uploads,
        )
    except FitParseError as exc:
        status_code = 413 if exc.code == "FIT_FILE_TOO_LARGE" else 422
        raise AppError(exc.code, exc.message, status_code=status_code) from exc

    if result.created == 0 and result.updated == 0:
        details = [
            {
                "filename": item.filename,
                "error": {"code": item.error_code, "message": item.error_message},
            }
            for item in result.files
        ]
        codes = {item.error_code for item in result.files}
        status_code = 413 if codes == {"FIT_FILE_TOO_LARGE"} else 422
        raise AppError(
            "FIT_IMPORT_FAILED",
            "None of the files could be imported.",
            status_code=status_code,
            details=details,
        )

    return FitImportResponse(
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        failed=result.failed,
        last_sync_at=result.last_sync_at,
        files=[
            FitImportFileResult(
                filename=item.filename,
                status=item.status,
                activity_id=item.activity_id,
                provider_activity_id=item.provider_activity_id,
                error=(
                    FitImportErrorPublic(code=item.error_code, message=item.error_message)
                    if item.error_code and item.error_message
                    else None
                ),
            )
            for item in result.files
        ],
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
