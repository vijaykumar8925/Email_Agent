"""Shared pytest fixtures for the Mail Agent test suite.

Provides a test-configured FastAPI app, HTTP client, and environment
setup for unit and integration tests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set minimal environment variables required by Settings.

    This runs before every test to ensure config validation passes.
    Values here are safe test defaults — no real credentials.
    """
    env_vars: dict[str, str] = {
        "APP_ENV": "test",
        "APP_DEBUG": "false",
        "APP_SECRET_KEY": "test-secret-key-that-is-at-least-thirty-two-characters-long",
        "APP_LOG_LEVEL": "WARNING",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost:5432/mailagent_test",
        "REDIS_URL": "redis://localhost:6379/0",
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "TOKEN_ENCRYPTION_KEYS": "",
        "ANTHROPIC_API_KEY": "sk-ant-test-key",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
async def app() -> AsyncGenerator[Any, None]:
    """Create a test FastAPI application with mocked external dependencies.

    The database and Redis are mocked for unit tests. Integration tests
    use real services via docker-compose.
    """
    # Import here so env vars are set by the autouse fixture first
    from mailagent.main import create_app

    test_app = create_app()

    # Override lifespan-managed dependencies for unit tests
    yield test_app


@pytest.fixture
async def client(app: Any) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client for the FastAPI application.

    Uses httpx's ASGITransport to call the app directly without
    starting a real server.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac
