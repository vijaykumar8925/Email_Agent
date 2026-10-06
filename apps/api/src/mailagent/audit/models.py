"""Immutable audit log model recording human approvals, tampering rejects, and sends."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mailagent.db.base import Base, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only audit trail for compliance and safety verification."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        nullable=True,
        index=True,
        comment="Acting user, if authenticated",
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="Action performed: DRAFT_CREATED, DRAFT_APPROVED, DRAFT_RESET, DRAFT_SENT, TAMPER_DETECTED",
    )
    target_type: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
        comment="ID of the affected entity",
    )
    content_sha256: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Cryptographic content hash at the time of the action",
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Structured metadata describing the event",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} target_id={self.target_id}>"
