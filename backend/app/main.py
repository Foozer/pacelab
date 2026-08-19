"""PaceLab FastAPI application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.v1.router import api_v1_router
from app.core.config import Settings, get_settings
from app.core.csrf import CSRFMiddleware
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import SecurityHeadersMiddleware
from app.core.rate_limit import InMemoryRateLimiter
from app.db.session import create_engine, create_session_factory
from app.integrations.factory import build_activity_provider
from app.services.email import RecordingEmailSender


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    configure_logging(settings)
    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    yield
    await engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    app = FastAPI(
        title="PaceLab API",
        summary="Running analytics platform",
        version=resolved.app_version,
        lifespan=lifespan,
        docs_url="/docs" if not resolved.is_production else None,
        redoc_url="/redoc" if not resolved.is_production else None,
        openapi_url="/openapi.json" if not resolved.is_production else None,
    )
    app.state.settings = resolved
    app.state.debug = resolved.debug
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.email_sender = RecordingEmailSender()
    app.state.activity_provider = build_activity_provider(resolved)

    app.add_middleware(CSRFMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    if resolved.is_production:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=resolved.allowed_hosts_list)

    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(api_v1_router)

    return app


app = create_app()
