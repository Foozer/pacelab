"""Version 1 API router."""

from fastapi import APIRouter

from app.api.v1 import auth, users

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth.router)
api_v1_router.include_router(users.router)
