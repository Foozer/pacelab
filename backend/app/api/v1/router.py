"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1 import activities, analytics, auth, dashboard, privacy, users

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(dashboard.router)
api_v1_router.include_router(activities.router)
api_v1_router.include_router(analytics.router)
api_v1_router.include_router(privacy.router)
