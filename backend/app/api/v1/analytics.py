"""Session-scoped analytics. Identity never comes from a client user_id."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import AerobicEfficiencyResponse, EasyRunningResponse, TrendsResponse
from app.services import analytics as analytics_service
from app.services.running_metrics import (
    DEFAULT_EASY_HEART_RATE_MAX,
    DEFAULT_EASY_HEART_RATE_MIN,
    HEART_RATE_QUERY_MAX,
    HEART_RATE_QUERY_MIN,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _band_or_422(hr_min: int, hr_max: int) -> None:
    try:
        analytics_service.parse_heart_rate_band(hr_min, hr_max)
    except ValueError as exc:
        raise AppError("VALIDATION_ERROR", str(exc), status_code=422) from exc


def _range_or_422(range_key: str) -> None:
    try:
        analytics_service.parse_trend_range(range_key)
    except ValueError as exc:
        raise AppError("VALIDATION_ERROR", str(exc), status_code=422) from exc


@router.get("/easy-running", response_model=EasyRunningResponse)
async def read_easy_running(
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
) -> EasyRunningResponse:
    _band_or_422(hr_min, hr_max)
    return await analytics_service.get_easy_running_for_user(
        db,
        user_id=user.id,
        hr_min=hr_min,
        hr_max=hr_max,
    )


@router.get("/aerobic-efficiency", response_model=AerobicEfficiencyResponse)
async def read_aerobic_efficiency(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AerobicEfficiencyResponse:
    return await analytics_service.get_aerobic_efficiency_for_user(db, user_id=user.id)


@router.get("/trends", response_model=TrendsResponse)
async def read_trends(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    range_key: str = Query(default="8w", alias="range"),
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
) -> TrendsResponse:
    _band_or_422(hr_min, hr_max)
    _range_or_422(range_key)
    return await analytics_service.get_trends_for_user(
        db,
        user_id=user.id,
        range_key=range_key,
        hr_min=hr_min,
        hr_max=hr_max,
        now=datetime.now(UTC),
    )
