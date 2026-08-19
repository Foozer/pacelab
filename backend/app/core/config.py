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

    garmin_client_id: str = ""
    garmin_client_secret: str = ""
    garmin_redirect_uri: str = ""
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
        return hosts or ["localhost"]

    @property
    def session_cookie_secure(self) -> bool:
        return self.is_production or self.frontend_url.startswith("https://")

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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_for_environment()
    return settings
