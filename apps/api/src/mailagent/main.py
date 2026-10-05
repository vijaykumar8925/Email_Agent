"""FastAPI application factory with lifespan management.

The create_app() factory initializes all subsystems (config validation,
logging, database, Redis, middleware, exception handlers) and exposes
health/readiness endpoints.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mailagent.core.config import get_settings
from mailagent.core.errors import register_exception_handlers
from mailagent.core.logging import get_logger, setup_logging
from mailagent.core.middleware import register_middleware
from mailagent.db.session import close_db, get_engine, init_db

logger = get_logger(__name__)

# Module-level Redis client, set during lifespan
_redis_client: aioredis.Redis[Any] | None = None


def get_redis() -> aioredis.Redis[Any]:
    """Return the initialized Redis client.

    Raises:
        RuntimeError: If the application has not started yet.
    """
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Application not started.")
    return _redis_client


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup and shutdown.

    On startup:
    - Validates all settings (fail-fast on misconfiguration)
    - Configures structured logging
    - Initializes the database engine and connection pool
    - Connects to Redis
    - Initializes Sentry (if configured)

    On shutdown:
    - Closes database connections
    - Closes Redis connection
    """
    global _redis_client

    settings = get_settings()

    # Configure structured logging
    json_format = not settings.is_development
    setup_logging(log_level=settings.app_log_level, json_format=json_format)

    logger.info(
        "application_starting",
        env=settings.app_env.value,
        debug=settings.app_debug,
    )

    # Initialize database
    init_db(settings)
    logger.info("database_initialized")

    # Initialize Redis
    _redis_client = aioredis.from_url(
        settings.redis_url_str,
        decode_responses=True,
    )
    logger.info("redis_connected")

    # Initialize Sentry if configured
    if settings.sentry_dsn:
        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=settings.sentry_traces_sample_rate,
                environment=settings.app_env.value,
            )
            logger.info("sentry_initialized")
        except Exception:
            logger.warning("sentry_init_failed")

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("application_shutting_down")

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("redis_disconnected")

    await close_db()
    logger.info("database_disconnected")
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title="Mail Agent API",
        description="AI-powered email management assistant for Gmail",
        version="0.1.0",
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
        openapi_url="/api/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS — strict by default, configured via environment
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["*"],
    )

    # Custom middleware (request ID, security headers)
    register_middleware(app, enable_hsts=settings.is_production)

    # Exception handlers (RFC 7807 responses)
    register_exception_handlers(app)

    # Health endpoints
    app.add_api_route("/api/v1/healthz", _healthz, methods=["GET"], tags=["health"])
    app.add_api_route("/api/v1/readyz", _readyz, methods=["GET"], tags=["health"])

    return app


async def _healthz() -> dict[str, str]:
    """Liveness probe — returns OK if the process is running.

    This endpoint does not check external dependencies. Use /readyz
    for a full readiness check.
    """
    return {"status": "ok"}


async def _readyz() -> dict[str, Any]:
    """Readiness probe — checks that the database and Redis are reachable.

    Returns 200 with component statuses if all checks pass.
    Returns 503 if any dependency is unhealthy.
    """
    from fastapi.responses import JSONResponse

    checks: dict[str, str] = {}
    all_healthy = True

    # Check database
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unhealthy"
        all_healthy = False

    # Check Redis
    try:
        redis = get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unhealthy"
        all_healthy = False

    response_data: dict[str, Any] = {
        "status": "ok" if all_healthy else "unhealthy",
        "checks": checks,
    }

    if not all_healthy:
        return JSONResponse(status_code=503, content=response_data)  # type: ignore[return-value]

    return response_data


# Create the default app instance for uvicorn
app = create_app()
