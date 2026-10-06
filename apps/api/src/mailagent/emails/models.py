"""Database models for email threads and messages with triage metadata."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mailagent.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from mailagent.drafts.models import Draft
    from mailagent.users.models import Mailbox


class EmailThread(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Aggregated Gmail conversation thread."""

    __tablename__ = "email_threads"

    mailbox_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mailboxes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to mailboxes.id",
    )
    gmail_thread_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Google Gmail thread identifier",
    )
    subject: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        default="",
    )
    snippet: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    message_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    is_unread: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Relationships
    mailbox: Mapped[Mailbox] = relationship("Mailbox")
    messages: Mapped[list[EmailMessage]] = relationship(
        "EmailMessage",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="EmailMessage.received_at",
    )

    def __repr__(self) -> str:
        return f"<EmailThread id={self.id} gmail_thread_id={self.gmail_thread_id!r}>"


class EmailMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Individual email message fetched from Gmail, augmented with AI triage analysis."""

    __tablename__ = "email_messages"

    mailbox_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("mailboxes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to mailboxes.id",
    )
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_threads.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to email_threads.id",
    )
    gmail_message_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique Gmail message ID",
    )
    gmail_thread_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Gmail thread ID",
    )
    sender: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Sender From header",
    )
    recipient: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="",
        comment="Recipient To header",
    )
    subject: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        default="",
    )
    snippet: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    body_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        comment="Sanitized plain text email body",
    )
    body_html: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional raw HTML content if present",
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Message date header / internal timestamp",
    )
    is_unread: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    labels: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
        comment="Gmail label identifiers, e.g. ['UNREAD', 'INBOX']",
    )

    # --- AI Triage Fields (Populated by Ollama Engine) ---
    category: Mapped[str] = mapped_column(
        String(32),
        default="other",
        nullable=False,
        index=True,
        comment="Triage category: work, finance, personal, newsletters, promotions, alerts, other",
    )
    importance: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
        index=True,
        comment="AI importance score: 1 (lowest) to 5 (urgent)",
    )
    needs_reply: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether the email requires a response",
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="1-2 sentence executive summary generated by AI",
    )
    suggested_action: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Suggested action: reply, review, flag_urgent, archive",
    )
    triaged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When AI classification was executed",
    )

    # Relationships
    mailbox: Mapped[Mailbox] = relationship("Mailbox")
    thread: Mapped[EmailThread | None] = relationship("EmailThread", back_populates="messages")
    drafts: Mapped[list[Draft]] = relationship("Draft", back_populates="email")

    def __repr__(self) -> str:
        return f"<EmailMessage id={self.id} subject={self.subject[:30]!r} category={self.category}>"
