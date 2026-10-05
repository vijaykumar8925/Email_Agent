"""Tests for health and readiness endpoints.

The /healthz endpoint always returns 200.
The /readyz endpoint checks database and Redis connectivity.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for the /api/v1/healthz liveness probe."""

    @pytest.mark.asyncio
    async def test_healthz_returns_ok(self, client: AsyncClient) -> None:
        """Liveness probe returns 200 with status ok."""
        response = await client.get("/api/v1/healthz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestReadinessEndpoint:
    """Tests for the /api/v1/readyz readiness probe."""

    @pytest.mark.asyncio
    async def test_readyz_healthy_when_deps_available(self, client: AsyncClient) -> None:
        """Readiness probe returns 200 when both DB and Redis are up.

        Mocks the DB engine and Redis client to simulate healthy dependencies.
        """
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(return_value=mock_conn)

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with (
            patch("mailagent.main.get_engine", return_value=mock_engine),
            patch("mailagent.main.get_redis", return_value=mock_redis),
        ):
            response = await client.get("/api/v1/readyz")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["checks"]["database"] == "ok"
        assert data["checks"]["redis"] == "ok"

    @pytest.mark.asyncio
    async def test_readyz_unhealthy_when_db_down(self, client: AsyncClient) -> None:
        """Readiness probe returns 503 when the database is unreachable."""
        with (
            patch("mailagent.main.get_engine", side_effect=RuntimeError("not initialized")),
            patch("mailagent.main.get_redis", return_value=AsyncMock(ping=AsyncMock())),
        ):
            response = await client.get("/api/v1/readyz")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_readyz_unhealthy_when_redis_down(self, client: AsyncClient) -> None:
        """Readiness probe returns 503 when Redis is unreachable."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(return_value=mock_conn)

        with (
            patch("mailagent.main.get_engine", return_value=mock_engine),
            patch("mailagent.main.get_redis", side_effect=RuntimeError("not initialized")),
        ):
            response = await client.get("/api/v1/readyz")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["redis"] == "unhealthy"
