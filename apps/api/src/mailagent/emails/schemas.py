"""Pydantic schemas for email responses and mailbox synchronization."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailMessageResponse(BaseModel):
    """Public representation of an ingested and triaged email."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gmail_message_id: str
    gmail_thread_id: str
    sender: str
    recipient: str
    subject: str
    snippet: str
    body_text: str
    received_at: datetime
    is_unread: bool
    labels: list[str] = Field(default_factory=list)

    # AI Triage Fields
    category: str
    importance: int
    needs_reply: bool
    summary: str | None = None
    suggested_action: str | None = None
    triaged_at: datetime | None = None


class EmailListResponse(BaseModel):
    """Paginated list of emails."""

    items: list[EmailMessageResponse]
    total: int


class SyncMailboxResult(BaseModel):
    """Result summary of on-demand Gmail sync and AI triage."""

    mailbox_id: uuid.UUID
    gmail_address: str
    synced_count: int
    new_messages: int
    triaged_count: int
    duration_ms: float
