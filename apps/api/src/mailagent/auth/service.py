"""Authentication service implementing Google OAuth 2.0 flow and sessions.

Handles state verification, token exchange, user profile retrieval,
MultiFernet token vault encryption, and session issuance.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from mailagent.core.config import Settings
from mailagent.core.errors import (
    AuthorizationError,
    ExternalServiceError,
    ValidationError,
)
from mailagent.core.logging import get_logger
from mailagent.core.security import SessionManager, TokenVault
from mailagent.users.models import User
from mailagent.users.repository import UserRepository

logger = get_logger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"  # noqa: S105
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

GMAIL_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class AuthService:
    """Authentication and session business logic."""

    def __init__(
        self,
        repository: UserRepository,
        settings: Settings,
        token_vault: TokenVault,
        session_manager: SessionManager,
    ) -> None:
        self.repo = repository
        self.settings = settings
        self.vault = token_vault
        self.session_manager = session_manager

    def create_authorization_url(self, prompt: str = "consent") -> tuple[str, str]:
        """Generate Google OAuth 2.0 authorization URL and CSRF state token.

        Returns:
            Tuple of (authorization_url, state_token).
        """
        state = secrets.token_urlsafe(32)
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": prompt,
            "state": state,
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return url, state

    async def handle_google_callback(
        self,
        code: str,
        state: str,
        expected_state: str | None,
    ) -> tuple[User, str]:
        """Exchange authorization code with Google and create an authenticated session.

        Args:
            code: The OAuth authorization code from Google.
            state: The state parameter received in the callback.
            expected_state: The state parameter saved before redirecting.

        Returns:
            Tuple of (User, signed_session_token).

        Raises:
            ValidationError: If state verification fails.
            ExternalServiceError: If Google token or userinfo request fails.
        """
        if not expected_state or state != expected_state:
            logger.warning("oauth_state_mismatch", received=state, expected=expected_state)
            raise ValidationError("Invalid OAuth state parameter. Possible CSRF attempt.")

        token_data = await self._exchange_code_for_tokens(code)
        access_token = str(token_data.get("access_token") or "")
        refresh_raw = token_data.get("refresh_token")
        refresh_token: str | None = str(refresh_raw) if refresh_raw else None
        expires_raw = token_data.get("expires_in")
        expires_in = int(expires_raw) if isinstance(expires_raw, (int, str)) else 3600
        scopes = str(token_data.get("scope") or " ".join(GMAIL_SCOPES))

        if not access_token:
            raise ExternalServiceError("Google OAuth response missing access_token")

        userinfo = await self._fetch_userinfo(access_token)
        google_sub = str(userinfo.get("sub") or "")
        email = str(userinfo.get("email") or "")
        display_name_raw = userinfo.get("name")
        display_name: str | None = str(display_name_raw) if display_name_raw else None
        picture_raw = userinfo.get("picture")
        picture_url: str | None = str(picture_raw) if picture_raw else None

        if not google_sub or not email:
            raise ExternalServiceError("Google userinfo missing required subject or email")

        expires_at = datetime.now(UTC) + timedelta(seconds=expires_in)

        # Encrypt tokens via MultiFernet
        encrypted_access = self.vault.encrypt(access_token)
        encrypted_refresh = self.vault.encrypt(refresh_token) if refresh_token else None

        # Upsert database records
        user = await self.repo.upsert_user(
            email=email,
            google_sub=google_sub,
            display_name=display_name,
            picture_url=picture_url,
        )

        await self.repo.upsert_oauth_credential(
            user_id=user.id,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            scopes=scopes,
            expires_at=expires_at,
        )

        await self.repo.upsert_mailbox(
            user_id=user.id,
            gmail_address=email,
        )

        await self.repo.session.commit()
        await self.repo.session.refresh(user)

        session_token = self.session_manager.create_session(str(user.id))
        logger.info("user_authenticated", user_id=str(user.id), email=email)
        return user, session_token

    async def _exchange_code_for_tokens(self, code: str) -> dict[str, object]:
        """POST authorization code to Google token endpoint."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "code": code,
                        "client_id": self.settings.google_client_id,
                        "client_secret": self.settings.google_client_secret,
                        "redirect_uri": self.settings.google_redirect_uri,
                        "grant_type": "authorization_code",
                    },
                    headers={"Accept": "application/json"},
                )
            except httpx.RequestError as exc:
                logger.error("google_token_exchange_network_error", error=str(exc))
                raise ExternalServiceError(
                    "Failed to communicate with Google OAuth servers"
                ) from exc

        if res.status_code != 200:
            logger.error(
                "google_token_exchange_failed",
                status_code=res.status_code,
                response=res.text,
            )
            raise ExternalServiceError(
                f"Google OAuth token exchange failed with status {res.status_code}"
            )

        return res.json()  # type: ignore[no-any-return]

    async def _fetch_userinfo(self, access_token: str) -> dict[str, object]:
        """Fetch Google account profile info using access token."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            except httpx.RequestError as exc:
                logger.error("google_userinfo_network_error", error=str(exc))
                raise ExternalServiceError("Failed to fetch Google user profile") from exc

        if res.status_code != 200:
            logger.error("google_userinfo_failed", status_code=res.status_code, response=res.text)
            raise ExternalServiceError("Failed to fetch Google user profile")

        return res.json()  # type: ignore[no-any-return]

    async def handle_dev_login(
        self,
        email: str = "demo.user@gmail.com",
        display_name: str = "Demo User",
    ) -> tuple[User, str]:
        """Provide instant local login for development and testing."""
        if not self.settings.is_development:
            raise AuthorizationError(
                "Development login is disabled in non-development environments"
            )

        google_sub = f"dev-sub-{uuid.uuid5(uuid.NAMESPACE_DNS, email)}"
        encrypted_access = self.vault.encrypt("mock-dev-access-token")
        encrypted_refresh = self.vault.encrypt("mock-dev-refresh-token")
        expires_at = datetime.now(UTC) + timedelta(days=30)

        user = await self.repo.upsert_user(
            email=email,
            google_sub=google_sub,
            display_name=display_name,
            picture_url="https://lh3.googleusercontent.com/a/default-user",
        )

        await self.repo.upsert_oauth_credential(
            user_id=user.id,
            encrypted_access_token=encrypted_access,
            encrypted_refresh_token=encrypted_refresh,
            scopes=" ".join(GMAIL_SCOPES),
            expires_at=expires_at,
        )

        await self.repo.upsert_mailbox(
            user_id=user.id,
            gmail_address=email,
        )

        await self.repo.session.commit()
        await self.repo.session.refresh(user)

        session_token = self.session_manager.create_session(str(user.id))
        logger.info("dev_user_authenticated", user_id=str(user.id), email=email)
        return user, session_token

    async def get_user_from_session(self, session_token: str | None) -> User | None:
        """Validate session token and return the User entity if valid."""
        if not session_token:
            return None

        session_data = self.session_manager.validate_session(session_token)
        if not session_data or "user_id" not in session_data:
            return None

        try:
            user_id = uuid.UUID(session_data["user_id"])
        except (ValueError, TypeError):
            return None

        user = await self.repo.get_by_id(user_id)
        if user and not user.is_active:
            return None

        return user
