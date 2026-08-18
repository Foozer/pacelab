"""Authenticated user account routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import SESSION_COOKIE_NAME
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import PasswordChangeRequest, UserPublic
from app.services import auth as auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_current_user(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/me/password", response_model=UserPublic)
async def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    await auth_service.change_password(
        db,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        current_session_token=request.cookies.get(SESSION_COOKIE_NAME),
    )
    return user
