"""Liveness and readiness health checks."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

DatabaseStatus = Literal["connected", "disconnected"]


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        503: {"model": HealthResponse, "description": "Application is up but a dependency is down"},
    },
)
async def health(request: Request) -> HealthResponse | JSONResponse:
    """Verify the API process and PostgreSQL connectivity."""
    engine: AsyncEngine = request.app.state.engine
    settings = request.app.state.settings

    database_status: DatabaseStatus = "disconnected"
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        logger.exception("Health check could not reach PostgreSQL")

    payload = HealthResponse(
        status="ok" if database_status == "connected" else "unhealthy",
        database=database_status,
        version=settings.app_version,
        environment=settings.environment,
    )
    if payload.status != "ok":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )
    return payload
