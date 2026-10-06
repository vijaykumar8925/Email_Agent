"""Shared FastAPI dependencies used across routers.

Dependencies are functions that FastAPI calls via Depends() to inject
common resources like database sessions, Redis connections, and the
current authenticated user.
"""

from __future__ import annotations

from cryptography.fernet import Fernet
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from mailagent.auth.service import AuthService
from mailagent.core.config import Settings, get_settings
from mailagent.core.errors import AuthenticationError
from mailagent.core.security import SessionManager, TokenVault
from mailagent.db.session import get_db_session
from mailagent.users.models import User
from mailagent.users.repository import UserRepository


async def get_settings_dep() -> Settings:
    """Provide the validated application settings as a dependency."""
    return get_settings()


def get_token_vault(settings: Settings = Depends(get_settings_dep)) -> TokenVault:
    """Provide TokenVault with configured encryption keys."""
    keys = settings.token_encryption_keys
    if not keys:
        keys = [Fernet.generate_key().decode()]
    return TokenVault(keys)


def get_session_manager(settings: Settings = Depends(get_settings_dep)) -> SessionManager:
    """Provide SessionManager configured with application secret."""
    return SessionManager(
        secret_key=settings.app_secret_key,
        max_age=settings.session_max_age_seconds,
    )


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UserRepository:
    """Provide UserRepository backed by request database session."""
    return UserRepository(session)


def get_auth_service(
    repo: UserRepository = Depends(get_user_repository),
    settings: Settings = Depends(get_settings_dep),
    vault: TokenVault = Depends(get_token_vault),
    session_manager: SessionManager = Depends(get_session_manager),
) -> AuthService:
    """Provide AuthService instance."""
    return AuthService(
        repository=repo,
        settings=settings,
        token_vault=vault,
        session_manager=session_manager,
    )


async def get_optional_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings_dep),
) -> User | None:
    """Return authenticated User if a valid session cookie exists, else None."""
    session_token = request.cookies.get(settings.session_cookie_name)
    return await auth_service.get_user_from_session(session_token)


async def get_current_user(
    user: User | None = Depends(get_optional_current_user),
) -> User:
    """Require an authenticated user; raises AuthenticationError (HTTP 401) if not."""
    if user is None:
        raise AuthenticationError("Not authenticated. Please sign in.")
    return user
