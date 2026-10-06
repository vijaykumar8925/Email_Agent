"""Pydantic schemas for draft requests, responses, and state machine transitions."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DraftResponse(BaseModel):
    """Public representation of an email reply draft."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    mailbox_id: uuid.UUID
    email_id: uuid.UUID | None = None
    gmail_thread_id: str | None = None
    to_email: str
    subject: str
    body: str
    tone: str
    status: str
    approved_content_sha256: str | None = None
    approved_at: datetime | None = None
    send_idempotency_key: str | None = None
    sent_at: datetime | None = None
    gmail_message_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CreateDraftRequest(BaseModel):
    """Payload to generate an AI reply draft for an existing email."""

    email_id: uuid.UUID
    user_instructions: str = Field(default="", max_length=1000)
    tone: str = Field(default="professional", pattern="^(professional|casual|concise|warm)$")


class UpdateDraftRequest(BaseModel):
    """Payload to modify draft subject or body. Automatically resets status to DRAFTED."""

    subject: str | None = Field(default=None, min_length=1, max_length=1000)
    body: str | None = Field(default=None, min_length=1)
    tone: str | None = Field(default=None, pattern="^(professional|casual|concise|warm)$")


class SendDraftRequest(BaseModel):
    """Optional idempotency parameters when sending an approved draft."""

    idempotency_key: str | None = Field(default=None, max_length=64)


class DraftListResponse(BaseModel):
    """Paginated list of drafts."""

    items: list[DraftResponse]
    total: int
