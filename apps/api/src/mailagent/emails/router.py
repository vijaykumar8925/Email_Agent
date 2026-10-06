"""FastAPI router for mailbox sync and email triage queries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from mailagent.ai.service import AIService
from mailagent.core.config import Settings
from mailagent.core.deps import (
    get_current_user,
    get_settings_dep,
    get_token_vault,
    get_user_repository,
)
from mailagent.core.logging import get_logger
from mailagent.core.security import TokenVault
from mailagent.db.session import get_db_session
from mailagent.emails.repository import EmailRepository
from mailagent.emails.schemas import EmailListResponse, EmailMessageResponse, SyncMailboxResult
from mailagent.emails.service import EmailService
from mailagent.users.models import User
from mailagent.users.repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["emails"])


def get_email_service(
    session: AsyncSession = Depends(get_db_session),
    user_repo: UserRepository = Depends(get_user_repository),
    vault: TokenVault = Depends(get_token_vault),
    settings: Settings = Depends(get_settings_dep),
) -> EmailService:
    """Dependency provider for EmailService."""
    email_repo = EmailRepository(session)
    ai_service = AIService(settings=settings)
    return EmailService(
        session=session,
        email_repo=email_repo,
        user_repo=user_repo,
        token_vault=vault,
        ai_service=ai_service,
        settings=settings,
    )


@router.post(
    "/mailboxes/sync",
    response_model=SyncMailboxResult,
    summary="Synchronize Gmail inbox and run local AI triage",
)
async def sync_mailbox(
    max_messages: int = Query(default=10, ge=1, le=50, description="Max messages to fetch"),
    user: User = Depends(get_current_user),
    service: EmailService = Depends(get_email_service),
) -> SyncMailboxResult:
    """Fetch unread Gmail messages, persist them, and run local Ollama triage classification."""
    return await service.sync_mailbox(user_id=user.id, max_messages=max_messages)


@router.get(
    "/emails",
    response_model=EmailListResponse,
    summary="List ingested and triaged emails",
)
async def list_emails(
    category: str | None = Query(default=None, description="Filter by category (e.g. work, finance, alerts)"),
    min_importance: int | None = Query(default=None, ge=1, le=5, description="Filter by minimum importance score"),
    needs_reply: bool | None = Query(default=None, description="Filter by needs_reply flag"),
    unread_only: bool = Query(default=False, description="Filter unread messages only"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: EmailService = Depends(get_email_service),
) -> EmailListResponse:
    """List triaged emails with category and importance filtering."""
    return await service.list_emails(
        user_id=user.id,
        category=category,
        min_importance=min_importance,
        needs_reply=needs_reply,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/emails/{email_id}",
    response_model=EmailMessageResponse,
    summary="Get single email message details",
)
async def get_email(
    email_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EmailService = Depends(get_email_service),
) -> EmailMessageResponse:
    """Retrieve full details of an email by internal UUID."""
    msg = await service.get_email(user_id=user.id, email_id=email_id)
    return EmailMessageResponse.model_validate(msg)


@router.post(
    "/emails/{email_id}/triage",
    response_model=EmailMessageResponse,
    summary="Run or refresh AI triage on an email",
)
async def triage_email(
    email_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: EmailService = Depends(get_email_service),
) -> EmailMessageResponse:
    """Run local Ollama triage on a specific email message."""
    msg = await service.triage_message(user_id=user.id, email_id=email_id)
    return EmailMessageResponse.model_validate(msg)

