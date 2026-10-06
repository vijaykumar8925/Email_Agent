"""Application configuration loaded from environment variables.

Uses pydantic-settings for validation with fail-fast behavior:
if any required variable is missing or invalid, the app refuses to start
with a clear error message.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_LIST_FIELDS = {"app_allowed_hosts", "app_cors_origins", "token_encryption_keys"}


class _CustomEnvSettingsSource(EnvSettingsSource):
    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        if field_name in _LIST_FIELDS:
            return value
        return super().decode_complex_value(field_name, field, value)


class _CustomDotEnvSettingsSource(DotEnvSettingsSource):
    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        if field_name in _LIST_FIELDS:
            return value
        return super().decode_complex_value(field_name, field, value)


class AppEnv(StrEnum):
    """Supported application environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class Settings(BaseSettings):
    """Application settings validated at startup.

    All values come from environment variables. Defaults are provided only
    for non-sensitive settings with safe fallbacks. Sensitive values (keys,
    credentials) have no defaults and will raise immediately if missing.
    """

    # Resolve .env from apps/api and repo root (except in test mode)
    _api_env = Path(__file__).resolve().parents[3] / ".env"
    _root_env = Path(__file__).resolve().parents[5] / ".env"
    _env_candidates = [p for p in (_root_env, _api_env) if p.is_file()]
    _env_tuple = tuple(str(p) for p in _env_candidates) if os.getenv("APP_ENV") != "test" else ()
    model_config = SettingsConfigDict(
        env_file=_env_tuple if _env_tuple else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        env_file = settings_cls.model_config.get("env_file")
        if os.getenv("APP_ENV") == "test":
            env_file = None
        return (
            init_settings,
            _CustomEnvSettingsSource(settings_cls),
            _CustomDotEnvSettingsSource(settings_cls, env_file=env_file),
            file_secret_settings,
        )

    # --- Application ---
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_debug: bool = False
    app_secret_key: str = Field(..., min_length=32)
    app_log_level: str = "INFO"
    app_allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    app_cors_origins: list[str] = ["http://localhost:3000"]

    # --- Database ---
    database_url: PostgresDsn
    database_pool_size: int = Field(default=10, ge=1, le=100)
    database_pool_max_overflow: int = Field(default=20, ge=0, le=100)

    # --- Redis ---
    redis_url: RedisDsn

    # --- Google OAuth ---
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # --- Google Pub/Sub ---
    google_pubsub_topic: str = ""
    google_pubsub_verification_token: str = ""

    # --- Token Encryption ---
    token_encryption_keys: list[str] = Field(default_factory=list)

    # --- AI Settings ---
    ai_provider: str = "ollama"

    # --- Ollama (Local Private LLM) ---
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_classifier: str = "phi4-mini:latest"
    ollama_model_drafter: str = "phi4-mini:latest"
    ollama_timeout_seconds: int = Field(default=120, ge=1)
    ollama_temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    # --- Anthropic (Cloud Optional) ---
    anthropic_api_key: str = ""
    anthropic_model_classifier: str = "claude-sonnet-4-20250514"
    anthropic_model_drafter: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens_classifier: int = Field(default=1024, ge=1)
    anthropic_max_tokens_drafter: int = Field(default=2048, ge=1)
    anthropic_timeout_seconds: int = Field(default=30, ge=1)
    anthropic_max_concurrent: int = Field(default=5, ge=1)

    # --- Session ---
    session_cookie_name: str = "mailagent_session"
    session_max_age_seconds: int = Field(default=86400, ge=300)

    # --- Rate Limiting ---
    rate_limit_auth: str = "10/minute"
    rate_limit_ai: str = "20/minute"
    rate_limit_send: str = "5/minute"

    # --- Sentry ---
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = Field(default=0.1, ge=0.0, le=1.0)

    # --- Data Retention ---
    email_body_retention_days: int = Field(default=30, ge=0)

    @field_validator(
        "app_allowed_hosts", "app_cors_origins", "token_encryption_keys", mode="before"
    )
    @classmethod
    def split_comma_separated(cls, v: object) -> object:
        """Parse comma-separated strings into lists."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_requirements(self) -> Self:
        """Enforce stricter validation for production deployments."""
        if self.app_env == AppEnv.PRODUCTION:
            if self.app_debug:
                raise ValueError("app_debug must be False in production")
            if len(self.app_secret_key) < 64:
                raise ValueError("app_secret_key must be at least 64 chars in production")
        return self

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == AppEnv.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == AppEnv.PRODUCTION

    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.app_env == AppEnv.TEST

    @property
    def database_url_str(self) -> str:
        """Return database URL as a string for SQLAlchemy."""
        return str(self.database_url)

    @property
    def redis_url_str(self) -> str:
        """Return Redis URL as a string."""
        return str(self.redis_url)


def get_settings() -> Settings:
    """Create and validate settings from environment.

    Raises ValidationError with clear messages if required variables
    are missing or invalid, ensuring fail-fast startup.
    """
    return Settings()
