"""Repository managing database persistence and row locks for Draft models."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mailagent.drafts.models import Draft, DraftStatus


class DraftRepository:
    """Async repository for Draft entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, draft_id: uuid.UUID) -> Draft | None:
        """Fetch draft by primary key."""
        stmt = select(Draft).where(Draft.id == draft_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_for_update(self, draft_id: uuid.UUID) -> Draft | None:
        """Fetch draft with an exclusive database row lock (SELECT ... FOR UPDATE)."""
        stmt = select(Draft).where(Draft.id == draft_id).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        mailbox_id: uuid.UUID,
        email_id: uuid.UUID | None,
        gmail_thread_id: str | None,
        to_email: str,
        subject: str,
        body: str,
        tone: str = "professional",
        status: str = DraftStatus.DRAFTED.value,
    ) -> Draft:
        """Create and persist a new Draft."""
        draft = Draft(
            user_id=user_id,
            mailbox_id=mailbox_id,
            email_id=email_id,
            gmail_thread_id=gmail_thread_id,
            to_email=to_email,
            subject=subject,
            body=body,
            tone=tone,
            status=status,
        )
        self._session.add(draft)
        await self._session.flush()
        return draft

    async def list_drafts(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Draft]:
        """List drafts belonging to a user, optionally filtered by status."""
        stmt = select(Draft).where(Draft.user_id == user_id)
        if status:
            stmt = stmt.where(Draft.status == status)

        stmt = stmt.order_by(Draft.updated_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_drafts(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
    ) -> int:
        """Count total drafts matching criteria."""
        stmt = select(func.count(Draft.id)).where(Draft.user_id == user_id)
        if status:
            stmt = stmt.where(Draft.status == status)

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0
