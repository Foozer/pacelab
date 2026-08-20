"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets must come from the environment, never source control."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "PaceLab"
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "test"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    secret_key: str = Field(..., min_length=16)
    encryption_key: str = ""

    database_url: str
    frontend_url: str = "http://localhost:5173"
    allowed_hosts: str = "localhost,127.0.0.1"
    forwarded_allow_ips: str = "127.0.0.1"

    # Transactional SMTP. Empty in local/dev → recording sender. Required in production.
    # Prefer a provider (Resend, Postmark, Amazon SES) over a personal inbox.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Official Garmin OAuth — deferred (developer programme not accepting new apps
    # as of 2026-08). Unused at runtime. FIT upload is the Garmin-file path.
    garmin_client_id: str = ""
    garmin_client_secret: str = ""
    garmin_redirect_uri: str = ""
    # Official Strava OAuth (Phase 8). Empty values are fine: the app still boots.
    # Connecting Strava also requires ENCRYPTION_KEY so tokens can be stored encrypted.
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = ""
    activity_provider: Literal["mock", "garmin"] = "mock"

    @field_validator("database_url")
    @classmethod
    def require_async_postgres(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the SQLAlchemy asyncpg dialect "
                "(postgresql+asyncpg://...)"
            )
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def allowed_hosts_list(self) -> list[str]:
        hosts = [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]
        # Docker healthchecks hit 127.0.0.1 inside the container. Allow loopback in
        # production so TrustedHost does not mark a healthy API as unhealthy.
        for loopback in ("127.0.0.1", "localhost"):
            if loopback not in hosts:
                hosts.append(loopback)
        return hosts or ["localhost"]

    @property
    def session_cookie_secure(self) -> bool:
        return self.is_production or self.frontend_url.startswith("https://")

    @property
    def strava_client_configured(self) -> bool:
        return bool(
            self.strava_client_id.strip()
            and self.strava_client_secret.strip()
            and self.strava_redirect_uri.strip()
        )

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host.strip() and self.smtp_from.strip())

    @property
    def cors_origins(self) -> list[str]:
        origin = self.frontend_url.rstrip("/")
        origins = [origin]
        if "://localhost" in origin:
            origins.append(origin.replace("://localhost", "://127.0.0.1", 1))
        elif "://127.0.0.1" in origin:
            origins.append(origin.replace("://127.0.0.1", "://localhost", 1))
        return list(dict.fromkeys(origins))

    def validate_for_environment(self) -> None:
        """Fail fast on unsafe production configuration."""
        if not self.is_production:
            return
        if self.debug:
            raise ValueError("DEBUG must be false when ENVIRONMENT=production")
        placeholder_markers = ("change-me", "changeme", "placeholder", "dev-only")
        lowered = self.secret_key.lower()
        if any(marker in lowered for marker in placeholder_markers):
            raise ValueError("SECRET_KEY must not be a placeholder in production")
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        if not self.frontend_url.startswith("https://"):
            raise ValueError("FRONTEND_URL must be https when ENVIRONMENT=production")
        if not self.smtp_configured:
            raise ValueError(
                "SMTP_HOST and SMTP_FROM are required when ENVIRONMENT=production "
                "(do not use the in-memory recording outbox in production)"
            )
        if not self.smtp_username.strip() or not self.smtp_password.strip():
            raise ValueError(
                "SMTP_USERNAME and SMTP_PASSWORD are required when ENVIRONMENT=production"
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_for_environment()
    return settings
