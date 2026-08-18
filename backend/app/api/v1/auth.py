"""Authentication routes: register, login, logout, CSRF, email, password reset."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    enforce_rate_limit,
    get_current_user,
    get_email_sender,
    get_recording_email_sender,
)
from app.core.errors import AppError
from app.core.security import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    clear_session_cookie,
    set_csrf_cookie,
    set_session_cookie,
)
from app.core.tokens import generate_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    CsrfResponse,
    DevOutboxItem,
    DevOutboxResponse,
    EmailVerifyRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)
from app.schemas.user import UserPublic
from app.services import auth as auth_service
from app.services.email import EmailSender, RecordingEmailSender

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/csrf", response_model=CsrfResponse)
async def csrf(request: Request, response: Response) -> CsrfResponse:
    token = request.cookies.get(CSRF_COOKIE_NAME) or generate_token()
    set_csrf_cookie(response, token, request.app.state.settings)
    return CsrfResponse(csrf_token=token)


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> User:
    enforce_rate_limit(request, "register", limit=5, window_seconds=3600)
    user, raw_session = await auth_service.register_user(
        db,
        email=str(payload.email),
        password=payload.password,
        settings=request.app.state.settings,
        email_sender=email_sender,
    )
    set_session_cookie(response, raw_session, request.app.state.settings)
    return user


@router.post("/login", response_model=UserPublic)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    enforce_rate_limit(request, "login", limit=10, window_seconds=900)
    user = await auth_service.authenticate_user(
        db,
        email=str(payload.email),
        password=payload.password,
    )
    raw_session = await auth_service.create_session(db, user)
    set_session_cookie(response, raw_session, request.app.state.settings)
    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await auth_service.revoke_session(db, request.cookies.get(SESSION_COOKIE_NAME))
    clear_session_cookie(response, request.app.state.settings)
    return MessageResponse(message="Signed out")


@router.post("/email/verify", response_model=UserPublic)
async def verify_email(
    payload: EmailVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    return await auth_service.verify_email_token(db, payload.token)


@router.post("/email/resend", response_model=MessageResponse)
async def resend_verification(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    email_sender: EmailSender = Depends(get_email_sender),
) -> MessageResponse:
    await auth_service.issue_email_verification(
        db,
        user=user,
        settings=request.app.state.settings,
        email_sender=email_sender,
    )
    return MessageResponse(message="If this address needs confirming, a message has been queued")


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    email_sender: EmailSender = Depends(get_email_sender),
) -> MessageResponse:
    enforce_rate_limit(request, "password-reset", limit=5, window_seconds=3600)
    await auth_service.request_password_reset(
        db,
        email=str(payload.email),
        settings=request.app.state.settings,
        email_sender=email_sender,
    )
    return MessageResponse(
        message="If an account exists for that email, a reset message has been queued"
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await auth_service.confirm_password_reset(
        db,
        raw_token=payload.token,
        password=payload.password,
    )
    return MessageResponse(message="Password updated. You can sign in with your new password.")


@router.get("/dev/outbox", response_model=DevOutboxResponse)
async def development_outbox(
    request: Request,
    user: User = Depends(get_current_user),
    sender: RecordingEmailSender = Depends(get_recording_email_sender),
) -> DevOutboxResponse:
    if not request.app.state.settings.is_development:
        raise AppError("NOT_FOUND", "Not Found", status_code=404)
    emails = [
        DevOutboxItem(template=item.template, subject=item.subject, body=item.body)
        for item in sender.outbox
        if item.to == user.email
    ]
    return DevOutboxResponse(emails=emails)
