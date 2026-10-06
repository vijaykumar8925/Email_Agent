"""Repository encapsulating database operations for email threads and messages."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mailagent.emails.models import EmailMessage, EmailThread


class EmailRepository:
    """SQLAlchemy 2.0 async repository for EmailThread and EmailMessage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_thread_by_gmail_id(
        self,
        mailbox_id: uuid.UUID,
        gmail_thread_id: str,
    ) -> EmailThread | None:
        """Fetch existing thread by mailbox and Gmail thread ID."""
        stmt = select(EmailThread).where(
            EmailThread.mailbox_id == mailbox_id,
            EmailThread.gmail_thread_id == gmail_thread_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_thread(
        self,
        mailbox_id: uuid.UUID,
        gmail_thread_id: str,
        subject: str,
        snippet: str,
        last_message_at: datetime | None,
        is_unread: bool = True,
    ) -> EmailThread:
        """Find or create an EmailThread record."""
        thread = await self.get_thread_by_gmail_id(mailbox_id, gmail_thread_id)
        if thread is None:
            thread = EmailThread(
                mailbox_id=mailbox_id,
                gmail_thread_id=gmail_thread_id,
                subject=subject,
                snippet=snippet,
                last_message_at=last_message_at,
                is_unread=is_unread,
                message_count=1,
            )
            self._session.add(thread)
        else:
            thread.snippet = snippet
            if subject:
                thread.subject = subject
            if last_message_at:
                thread.last_message_at = last_message_at
            thread.is_unread = is_unread
            thread.message_count += 1
        await self._session.flush()
        return thread

    async def get_message_by_gmail_id(self, gmail_message_id: str) -> EmailMessage | None:
        """Find an existing email by its unique Gmail message ID."""
        stmt = select(EmailMessage).where(EmailMessage.gmail_message_id == gmail_message_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_message_by_id(self, message_id: uuid.UUID) -> EmailMessage | None:
        """Find an email by internal UUID primary key."""
        stmt = select(EmailMessage).where(EmailMessage.id == message_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_message(
        self,
        mailbox_id: uuid.UUID,
        thread_id: uuid.UUID | None,
        gmail_message_id: str,
        gmail_thread_id: str,
        sender: str,
        recipient: str,
        subject: str,
        snippet: str,
        body_text: str,
        body_html: str | None,
        received_at: datetime,
        is_unread: bool,
        labels: list[str],
        category: str = "other",
        importance: int = 3,
        needs_reply: bool = False,
        summary: str | None = None,
        suggested_action: str | None = None,
        triaged_at: datetime | None = None,
    ) -> tuple[EmailMessage, bool]:
        """Insert new email message or return existing one. Returns (message, is_created)."""
        existing = await self.get_message_by_gmail_id(gmail_message_id)
        if existing is not None:
            # Update read status & labels
            existing.is_unread = is_unread
            existing.labels = labels
            await self._session.flush()
            return existing, False

        msg = EmailMessage(
            mailbox_id=mailbox_id,
            thread_id=thread_id,
            gmail_message_id=gmail_message_id,
            gmail_thread_id=gmail_thread_id,
            sender=sender,
            recipient=recipient,
            subject=subject,
            snippet=snippet,
            body_text=body_text,
            body_html=body_html,
            received_at=received_at,
            is_unread=is_unread,
            labels=labels,
            category=category,
            importance=importance,
            needs_reply=needs_reply,
            summary=summary,
            suggested_action=suggested_action,
            triaged_at=triaged_at,
        )
        self._session.add(msg)
        await self._session.flush()
        return msg, True

    async def update_message_triage(
        self,
        message_id: uuid.UUID,
        category: str,
        importance: int,
        needs_reply: bool,
        summary: str,
        suggested_action: str,
        triaged_at: datetime,
    ) -> EmailMessage | None:
        """Update message with AI triage results."""
        msg = await self.get_message_by_id(message_id)
        if msg is not None:
            msg.category = category
            msg.importance = importance
            msg.needs_reply = needs_reply
            msg.summary = summary
            msg.suggested_action = suggested_action
            msg.triaged_at = triaged_at
            await self._session.flush()
        return msg

    async def list_messages(
        self,
        mailbox_id: uuid.UUID,
        category: str | None = None,
        min_importance: int | None = None,
        needs_reply: bool | None = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[EmailMessage]:
        """List messages filtered by triage status, ordered by received date descending."""
        stmt = select(EmailMessage).where(EmailMessage.mailbox_id == mailbox_id)
        if category:
            stmt = stmt.where(EmailMessage.category == category)
        if min_importance:
            stmt = stmt.where(EmailMessage.importance >= min_importance)
        if needs_reply is not None:
            stmt = stmt.where(EmailMessage.needs_reply == needs_reply)
        if unread_only:
            stmt = stmt.where(EmailMessage.is_unread.is_(True))

        stmt = stmt.order_by(EmailMessage.received_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_messages(
        self,
        mailbox_id: uuid.UUID,
        category: str | None = None,
        min_importance: int | None = None,
        unread_only: bool = False,
    ) -> int:
        """Count total messages matching criteria."""
        stmt = select(func.count(EmailMessage.id)).where(EmailMessage.mailbox_id == mailbox_id)
        if category:
            stmt = stmt.where(EmailMessage.category == category)
        if min_importance:
            stmt = stmt.where(EmailMessage.importance >= min_importance)
        if unread_only:
            stmt = stmt.where(EmailMessage.is_unread.is_(True))

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0
