"""User account model.

One row per authenticated Google user. The email column is used for display
only; all Google API calls use the stored OAuth tokens in the linked
OAuthCredential record.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mailagent.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Authenticated Google user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        nullable=False,
        index=True,
        comment="Gmail address - used for display only",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Full name returned by Google",
    )
    picture_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Profile photo URL from Google",
    )
    google_sub: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Stable Google identity subject identifier",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    oauth_credential: Mapped[OAuthCredential | None] = relationship(
        "OAuthCredential",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    mailboxes: Mapped[list[Mailbox]] = relationship(
        "Mailbox",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class OAuthCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Encrypted Google OAuth 2.0 tokens for a user.

    Access and refresh tokens are stored encrypted-at-rest using the
    application's Fernet key(s). They are never stored in plaintext.
    """

    __tablename__ = "oauth_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="FK to users.id",
    )
    encrypted_access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Fernet-encrypted Google access token",
    )
    encrypted_refresh_token: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Fernet-encrypted Google refresh token",
    )
    token_type: Mapped[str] = mapped_column(
        String(32),
        default="Bearer",
        nullable=False,
    )
    scopes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Space-separated OAuth scopes granted",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC expiry of the access token",
    )
    token_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="oauth_credential")

    def __repr__(self) -> str:
        return f"<OAuthCredential user_id={self.user_id}>"


class Mailbox(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A watched Gmail mailbox belonging to a user.

    Tracks the Gmail history ID and Pub/Sub watch state so we can
    efficiently fetch only new messages via the Gmail History API.
    """

    __tablename__ = "mailboxes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to users.id",
    )
    gmail_address: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        comment="Gmail address associated with this mailbox",
    )
    history_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Last processed Gmail history ID for incremental sync",
    )
    watch_expiry: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the Gmail Pub/Sub watch expires (renewed periodically)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="mailboxes")

    def __repr__(self) -> str:
        return f"<Mailbox id={self.id} address={self.gmail_address!r}>"
