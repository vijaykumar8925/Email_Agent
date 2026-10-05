"""Tests for application configuration and settings validation.

Verifies that Settings validates required fields, applies defaults,
enforces production constraints, and fails fast on invalid values.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mailagent.core.config import AppEnv, Settings


class TestSettings:
    """Test suite for the Settings configuration class."""

    def test_valid_minimal_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings loads successfully with all required fields provided."""
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.app_env == AppEnv.DEVELOPMENT
        assert settings.app_debug is False
        assert settings.database_pool_size == 10

    def test_missing_secret_key_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings raises ValidationError when APP_SECRET_KEY is missing."""
        monkeypatch.delenv("APP_SECRET_KEY", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_short_secret_key_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings rejects secret keys shorter than 32 characters."""
        monkeypatch.setenv("APP_SECRET_KEY", "too-short")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_missing_database_url_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings raises ValidationError when DATABASE_URL is missing."""
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_missing_redis_url_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings raises ValidationError when REDIS_URL is missing."""
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.delenv("REDIS_URL", raising=False)

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_production_requires_debug_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Production mode rejects debug=True."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "true")
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 64)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        with pytest.raises(ValidationError, match="app_debug must be False"):
            Settings()  # type: ignore[call-arg]

    def test_production_requires_long_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Production mode requires secret key of at least 64 characters."""
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("APP_DEBUG", "false")
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        with pytest.raises(ValidationError, match="at least 64 chars"):
            Settings()  # type: ignore[call-arg]

    def test_comma_separated_values_parsed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Comma-separated env vars are correctly split into lists."""
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("APP_ALLOWED_HOSTS", "example.com, api.example.com")
        monkeypatch.setenv("APP_CORS_ORIGINS", "https://example.com,https://app.example.com")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.app_allowed_hosts == ["example.com", "api.example.com"]
        assert settings.app_cors_origins == ["https://example.com", "https://app.example.com"]

    def test_environment_helpers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Property helpers correctly identify the environment."""
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("APP_ENV", "test")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.is_test is True
        assert settings.is_development is False
        assert settings.is_production is False

    def test_database_url_str_property(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """database_url_str returns a plain string for SQLAlchemy."""
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

        settings = Settings()  # type: ignore[call-arg]

        assert isinstance(settings.database_url_str, str)
        assert "postgresql+asyncpg" in settings.database_url_str

    def test_invalid_pool_size_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Pool size outside valid range is rejected."""
        monkeypatch.setenv("APP_SECRET_KEY", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        monkeypatch.setenv("DATABASE_POOL_SIZE", "0")

        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]
