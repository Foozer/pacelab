"""Authenticated dashboard. Identity always comes from the session cookie."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services import analytics as analytics_service
from app.services.dashboard import get_dashboard_for_user
from app.services.running_metrics import (
    DEFAULT_EASY_HEART_RATE_MAX,
    DEFAULT_EASY_HEART_RATE_MIN,
    HEART_RATE_QUERY_MAX,
    HEART_RATE_QUERY_MIN,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def read_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    hr_min: int = Query(
        default=DEFAULT_EASY_HEART_RATE_MIN,
        ge=HEART_RATE_QUERY_MIN,
        le=HEART_RATE_QUERY_MAX,
    ),
    hr_max: int = Query(
        default=DEFAULT_EASY_HEART_RATE_MAX,
        ge=HEART_RATE_QUERY_MIN,
        le=HEART_RATE_QUERY_MAX,
    ),
) -> DashboardResponse:
    try:
        analytics_service.parse_heart_rate_band(hr_min, hr_max)
    except ValueError as exc:
        raise AppError("VALIDATION_ERROR", str(exc), status_code=422) from exc
    return await get_dashboard_for_user(
        db,
        user_id=user.id,
        hr_min=hr_min,
        hr_max=hr_max,
    )
