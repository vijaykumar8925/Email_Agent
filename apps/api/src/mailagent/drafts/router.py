"""FastAPI router exposing draft management, approval, and send endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from mailagent.ai.service import AIService
from mailagent.audit.repository import AuditRepository
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
from mailagent.drafts.repository import DraftRepository
from mailagent.drafts.schemas import (
    CreateDraftRequest,
    DraftListResponse,
    DraftResponse,
    SendDraftRequest,
    UpdateDraftRequest,
)
from mailagent.drafts.service import DraftService
from mailagent.emails.repository import EmailRepository
from mailagent.users.models import User
from mailagent.users.repository import UserRepository
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/drafts", tags=["drafts"])


def get_draft_service(
    session: AsyncSession = Depends(get_db_session),
    user_repo: UserRepository = Depends(get_user_repository),
    vault: TokenVault = Depends(get_token_vault),
    settings: Settings = Depends(get_settings_dep),
) -> DraftService:
    """Dependency provider for DraftService."""
    draft_repo = DraftRepository(session)
    email_repo = EmailRepository(session)
    audit_repo = AuditRepository(session)
    ai_service = AIService(settings=settings)
    return DraftService(
        session=session,
        draft_repo=draft_repo,
        email_repo=email_repo,
        user_repo=user_repo,
        audit_repo=audit_repo,
        token_vault=vault,
        ai_service=ai_service,
        settings=settings,
    )


@router.post(
    "/generate",
    response_model=DraftResponse,
    summary="Generate AI reply draft for an email",
)
async def generate_draft(
    payload: CreateDraftRequest,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(get_draft_service),
) -> DraftResponse:
    """Create a suggested email reply draft using local AI in DRAFTED status."""
    draft = await service.generate_draft_for_email(
        user_id=user.id,
        email_id=payload.email_id,
        user_instructions=payload.user_instructions,
        tone=payload.tone,
    )
    return DraftResponse.model_validate(draft)


@router.get(
    "",
    response_model=DraftListResponse,
    summary="List drafts for authenticated user",
)
async def list_drafts(
    status: str | None = Query(default=None, description="Filter by status (DRAFTED, APPROVED, SENT)"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    service: DraftService = Depends(get_draft_service),
) -> DraftListResponse:
    """List drafts belonging to current user."""
    return await service.list_drafts(user_id=user.id, status=status, limit=limit, offset=offset)


@router.get(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Get draft details",
)
async def get_draft(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(get_draft_service),
) -> DraftResponse:
    """Retrieve draft details by UUID."""
    draft = await service.get_draft(user_id=user.id, draft_id=draft_id)
    return DraftResponse.model_validate(draft)


@router.patch(
    "/{draft_id}",
    response_model=DraftResponse,
    summary="Update draft subject or body (resets approval)",
)
async def update_draft(
    draft_id: uuid.UUID,
    payload: UpdateDraftRequest,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(get_draft_service),
) -> DraftResponse:
    """Edit draft. Invariant: If draft was APPROVED, status automatically resets to DRAFTED."""
    draft = await service.update_draft(
        user_id=user.id,
        draft_id=draft_id,
        subject=payload.subject,
        body=payload.body,
        tone=payload.tone,
    )
    return DraftResponse.model_validate(draft)


@router.post(
    "/{draft_id}/approve",
    response_model=DraftResponse,
    summary="Explicit human approval (seals SHA-256 hash)",
)
async def approve_draft(
    draft_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(get_draft_service),
) -> DraftResponse:
    """Transition draft to APPROVED status and seal SHA-256 content hash in database."""
    draft = await service.approve_draft(user_id=user.id, draft_id=draft_id)
    return DraftResponse.model_validate(draft)


@router.post(
    "/{draft_id}/send",
    response_model=DraftResponse,
    summary="Verify hash and send email via Gmail API",
)
async def send_draft(
    draft_id: uuid.UUID,
    payload: SendDraftRequest | None = None,
    user: User = Depends(get_current_user),
    service: DraftService = Depends(get_draft_service),
) -> DraftResponse:
    """Verify cryptographic SHA-256 seal, lock database row, and dispatch message to Gmail."""
    idempotency_key = payload.idempotency_key if payload else None
    draft = await service.send_draft(
        user_id=user.id,
        draft_id=draft_id,
        idempotency_key=idempotency_key,
    )
    return DraftResponse.model_validate(draft)
