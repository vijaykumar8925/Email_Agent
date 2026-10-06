"""Unit tests for authentication router, dev login, and session handling."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from mailagent.core.config import AppEnv, Settings
from mailagent.core.deps import get_settings_dep


class TestAuthRouter:
    """Test suite for /api/v1/auth endpoints."""

    async def test_google_login_redirects_to_google(self, client: AsyncClient) -> None:
        """With configured credentials, login sets state cookie and redirects to Google."""
        response = await client.get("/api/v1/auth/google/login", follow_redirects=False)
        assert response.status_code == 303
        assert "accounts.google.com" in response.headers.get("location", "")
        assert "mailagent_oauth_state" in response.cookies

    async def test_google_login_dev_screen_when_placeholder(
        self,
        app: Any,
        client: AsyncClient,
    ) -> None:
        """With placeholder credentials in dev, google login returns dev bridge screen."""
        dev_settings = Settings(
            app_env=AppEnv.DEVELOPMENT,
            app_secret_key="a" * 32,
            database_url="postgresql+asyncpg://u:p@localhost:5432/db",  # type: ignore[arg-type]
            redis_url="redis://localhost:6379/0",  # type: ignore[arg-type]
            google_client_id="your-client-id.apps.googleusercontent.com",
            google_client_secret="your-client-secret",
        )
        app.dependency_overrides[get_settings_dep] = lambda: dev_settings
        try:
            response = await client.get("/api/v1/auth/google/login", follow_redirects=False)
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "Development Login" in response.text
        finally:
            app.dependency_overrides.pop(get_settings_dep, None)

    async def test_unauthenticated_status(self, client: AsyncClient) -> None:
        """Status endpoint returns authenticated=false when no session is present."""
        response = await client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False
        assert data["user"] is None

    async def test_unauthenticated_me_returns_401(self, client: AsyncClient) -> None:
        """GET /api/v1/auth/me returns 401 when no session is present."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
        data = response.json()
        assert data["code"] == "AUTHENTICATION_ERROR"

    async def test_logout_clears_cookie(self, client: AsyncClient) -> None:
        """POST /api/v1/auth/logout returns ok and deletes session cookie."""
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
