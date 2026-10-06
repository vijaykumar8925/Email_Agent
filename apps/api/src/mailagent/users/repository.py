"""User, OAuthCredential, and Mailbox database repository.

Encapsulates all database operations using parameterized SQLAlchemy 2.0
async queries according to Clean Architecture / Layering principles.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mailagent.users.models import Mailbox, OAuthCredential, User


class UserRepository:
    """Repository for user accounts, credentials, and mailboxes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key with relations eagerly loaded."""
        stmt = (
            select(User)
            .options(
                selectinload(User.oauth_credential),
                selectinload(User.mailboxes),
            )
            .where(User.id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by email."""
        stmt = (
            select(User)
            .options(
                selectinload(User.oauth_credential),
                selectinload(User.mailboxes),
            )
            .where(User.email == email)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        """Fetch user by Google subject ID."""
        stmt = (
            select(User)
            .options(
                selectinload(User.oauth_credential),
                selectinload(User.mailboxes),
            )
            .where(User.google_sub == google_sub)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_user(
        self,
        *,
        email: str,
        google_sub: str,
        display_name: str | None = None,
        picture_url: str | None = None,
    ) -> User:
        """Create or update a user record upon Google authentication."""
        user = await self.get_by_google_sub(google_sub)
        now = datetime.now(UTC)

        if user is None:
            # Check by email in case google_sub wasn't recorded previously
            user = await self.get_by_email(email)

        if user is not None:
            user.google_sub = google_sub
            if display_name is not None:
                user.display_name = display_name
            if picture_url is not None:
                user.picture_url = picture_url
            user.last_login_at = now
            user.is_active = True
        else:
            user = User(
                email=email,
                google_sub=google_sub,
                display_name=display_name,
                picture_url=picture_url,
                last_login_at=now,
                is_active=True,
            )
            self.session.add(user)

        await self.session.flush()
        return user

    async def get_oauth_credential(self, user_id: uuid.UUID) -> OAuthCredential | None:
        """Fetch OAuth 2.0 credential for a user."""
        stmt = select(OAuthCredential).where(OAuthCredential.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_oauth_credential(
        self,
        *,
        user_id: uuid.UUID,
        encrypted_access_token: str,
        encrypted_refresh_token: str | None,
        scopes: str,
        expires_at: datetime | None,
        token_type: str = "Bearer",  # noqa: S107
    ) -> OAuthCredential:
        """Create or update OAuth 2.0 credential for a user."""
        stmt = select(OAuthCredential).where(OAuthCredential.user_id == user_id)
        result = await self.session.execute(stmt)
        cred = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if cred is not None:
            cred.encrypted_access_token = encrypted_access_token
            # Preserve existing refresh token if new response did not contain one
            if encrypted_refresh_token:
                cred.encrypted_refresh_token = encrypted_refresh_token
            cred.scopes = scopes
            cred.expires_at = expires_at
            cred.token_type = token_type
            cred.token_refreshed_at = now
        else:
            cred = OAuthCredential(
                user_id=user_id,
                encrypted_access_token=encrypted_access_token,
                encrypted_refresh_token=encrypted_refresh_token,
                scopes=scopes,
                expires_at=expires_at,
                token_type=token_type,
                token_refreshed_at=now,
            )
            self.session.add(cred)

        await self.session.flush()
        return cred

    async def upsert_mailbox(
        self,
        *,
        user_id: uuid.UUID,
        gmail_address: str,
    ) -> Mailbox:
        """Create or fetch default mailbox for a user."""
        stmt = select(Mailbox).where(
            Mailbox.user_id == user_id,
            Mailbox.gmail_address == gmail_address,
        )
        result = await self.session.execute(stmt)
        mailbox = result.scalar_one_or_none()

        if mailbox is None:
            mailbox = Mailbox(
                user_id=user_id,
                gmail_address=gmail_address,
                is_active=True,
            )
            self.session.add(mailbox)
            await self.session.flush()

        return mailbox

    async def get_mailbox_by_address(self, gmail_address: str) -> Mailbox | None:
        """Fetch mailbox by its gmail address."""
        stmt = select(Mailbox).where(Mailbox.gmail_address == gmail_address)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_mailbox_for_user(self, user_id: uuid.UUID) -> Mailbox | None:
        """Fetch the first active mailbox for a user."""
        stmt = select(Mailbox).where(Mailbox.user_id == user_id, Mailbox.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_mailbox(self, user_id: uuid.UUID, gmail_address: str) -> Mailbox:
        """Create a new mailbox for a user."""
        return await self.upsert_mailbox(user_id=user_id, gmail_address=gmail_address)

