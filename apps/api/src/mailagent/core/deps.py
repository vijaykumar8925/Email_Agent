"""Shared FastAPI dependencies used across routers.

Dependencies are functions that FastAPI calls via Depends() to inject
common resources like database sessions, Redis connections, and the
current authenticated user.
"""

from __future__ import annotations

from mailagent.core.config import Settings, get_settings


async def get_settings_dep() -> Settings:
    """Provide the validated application settings as a dependency.

    This is a thin wrapper around get_settings() to support dependency
    injection and make testing easier (override via app.dependency_overrides).
    """
    return get_settings()
