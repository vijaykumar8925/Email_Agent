"""Database model for email reply drafts and the approval state machine."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mailagent.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from mailagent.emails.models import EmailMessage
    from mailagent.users.models import Mailbox, User


class DraftStatus(StrEnum):
    """Lifecycle statuses for the draft state machine."""

    DRAFTED = "DRAFTED"
    APPROVED = "APPROVED"
    SENDING = "SENDING"
    SENT = "SENT"


def compute_content_sha256(subject: str, body: str) -> str:
    """Compute the authoritative cryptographic SHA-256 hash of draft content."""
    content = f"{subject}\n\n{body}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class Draft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Suggested or human-edited reply draft with domain approval state."""

    __tablename__ = "drafts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Author or owner user",
    )
    mailbox_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mailboxes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated mailbox",
    )
    email_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Original incoming email being replied to (if reply)",
    )
    gmail_thread_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Target Gmail thread for in-thread delivery",
    )
    to_email: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Recipient email address",
    )
    subject: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    tone: Mapped[str] = mapped_column(
        String(32),
        default="professional",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=DraftStatus.DRAFTED.value,
        nullable=False,
        index=True,
        comment="DRAFTED -> APPROVED -> SENDING -> SENT",
    )

    # --- Approval & Cryptographic Hash Verification ---
    approved_content_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 sealed upon human approval",
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
    )

    # --- Idempotency & Send Results ---
    send_idempotency_key: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
        comment="Unique key guaranteeing at-most-once delivery under retries",
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    gmail_message_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Gmail message ID assigned after dispatch",
    )

    # Relationships
    user: Mapped[User] = relationship("User")
    mailbox: Mapped[Mailbox] = relationship("Mailbox")
    email: Mapped[EmailMessage | None] = relationship("EmailMessage", back_populates="drafts")

    def __repr__(self) -> str:
        return f"<Draft id={self.id} status={self.status} to={self.to_email!r}>"
