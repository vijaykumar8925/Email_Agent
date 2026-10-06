"""Repository for persisting immutable audit log records."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from mailagent.audit.models import AuditLog


class AuditRepository:
    """Async repository for append-only AuditLog entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        action: str,
        target_id: uuid.UUID,
        target_type: str = "draft",
        user_id: uuid.UUID | None = None,
        content_sha256: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Insert a tamper-evident audit record."""
        log = AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            content_sha256=content_sha256,
            details=details or {},
        )
        self._session.add(log)
        await self._session.flush()
        return log
