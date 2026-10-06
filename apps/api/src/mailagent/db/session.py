"""Async SQLAlchemy engine and session factory.

Provides a configured async engine and a session factory that can be used
as a FastAPI dependency. Connection pool settings come from the application
config.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from mailagent.core.config import Settings

# Module-level references set during app startup via init_db()
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    """Initialize the async engine and session factory.

    Called once during application startup (in the lifespan context manager).
    Uses connection pooling with the configured pool size and overflow.

    Args:
        settings: Application settings containing the database URL
            and pool configuration.
    """
    global _engine, _session_factory

    _engine = create_async_engine(
        settings.database_url_str,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_pool_max_overflow,
        pool_pre_ping=True,
        echo=settings.app_debug,
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db() -> None:
    """Dispose of the async engine and release all connections.

    Called during application shutdown.
    """
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


def get_engine() -> AsyncEngine:
    """Return the initialized async engine.

    Raises:
        RuntimeError: If init_db() has not been called.
    """
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call init_db() first.")
    return _engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for use in FastAPI dependencies.

    The session is automatically closed when the request completes.
    Transactions are managed by the service layer, not here.

    Yields:
        An AsyncSession instance.

    Raises:
        RuntimeError: If init_db() has not been called.
    """
    if _session_factory is None:
        raise RuntimeError("Database session factory not initialized. Call init_db() first.")

    async with _session_factory() as session:
        yield session


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the database session factory for background tasks."""
    if _session_factory is None:
        raise RuntimeError("Database session factory not initialized. Call init_db() first.")
    return _session_factory

