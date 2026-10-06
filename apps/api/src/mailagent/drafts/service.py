"""Domain service implementing human approval state machine and idempotent sending."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from mailagent.ai.schemas import DraftTone, GenerateDraftInput
from mailagent.ai.service import AIService
from mailagent.audit.repository import AuditRepository
from mailagent.core.config import Settings, get_settings
from mailagent.core.errors import (
    AuthorizationError,
    ContentTamperError,
    InvalidStateTransitionError,
    NotFoundError,
)
from mailagent.core.logging import get_logger
from mailagent.core.security import TokenVault
from mailagent.drafts.models import Draft, DraftStatus, compute_content_sha256
from mailagent.drafts.repository import DraftRepository
from mailagent.drafts.schemas import DraftListResponse, DraftResponse
from mailagent.emails.repository import EmailRepository
from mailagent.providers.gmail.client import GmailClient
from mailagent.users.repository import UserRepository

logger = get_logger(__name__)


class DraftService:
    """Service enforcing ADR 0003: domain approval state machine & cryptographic send verification."""

    def __init__(
        self,
        session: AsyncSession,
        draft_repo: DraftRepository,
        email_repo: EmailRepository,
        user_repo: UserRepository,
        audit_repo: AuditRepository,
        token_vault: TokenVault,
        ai_service: AIService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._draft_repo = draft_repo
        self._email_repo = email_repo
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._token_vault = token_vault
        self._ai_service = ai_service or AIService()
        self._settings = settings or get_settings()

    async def generate_draft_for_email(
        self,
        user_id: uuid.UUID,
        email_id: uuid.UUID,
        user_instructions: str = "",
        tone: str = "professional",
    ) -> Draft:
        """Generate a suggested reply draft using local Ollama AI in DRAFTED status."""
        email = await self._email_repo.get_message_by_id(email_id)
        if email is None:
            raise NotFoundError("Email message not found")

        mailbox = await self._user_repo.get_default_mailbox_for_user(user_id)
        if mailbox is None or email.mailbox_id != mailbox.id:
            raise AuthorizationError("Access denied to target email")

        user = await self._user_repo.get_by_id(user_id)
        sender_name = user.display_name if user and user.display_name else ""

        # AI Generation
        ai_input = GenerateDraftInput(
            email_subject=email.subject,
            email_sender=email.sender,
            email_body=email.body_text,
            user_instructions=user_instructions,
            tone=DraftTone(tone) if tone in {t.value for t in DraftTone} else DraftTone.PROFESSIONAL,
            sender_name=sender_name,
        )

        ai_res = await self._ai_service.generate_draft(ai_input)

        draft = await self._draft_repo.create(
            user_id=user_id,
            mailbox_id=mailbox.id,
            email_id=email.id,
            gmail_thread_id=email.gmail_thread_id,
            to_email=email.sender,
            subject=ai_res.subject,
            body=ai_res.body,
            tone=tone,
            status=DraftStatus.DRAFTED.value,
        )

        await self._audit_repo.record(
            action="DRAFT_CREATED",
            target_id=draft.id,
            user_id=user_id,
            details={"email_id": str(email_id), "tone": tone, "model_used": ai_res.model_used},
        )
        await self._session.commit()
        return draft

    async def update_draft(
        self,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
        subject: str | None = None,
        body: str | None = None,
        tone: str | None = None,
    ) -> Draft:
        """Edit draft contents. If draft was APPROVED, automatically reset status to DRAFTED."""
        draft = await self._draft_repo.get_by_id(draft_id)
        if draft is None:
            raise NotFoundError("Draft not found")
        if draft.user_id != user_id:
            raise AuthorizationError("Access denied to draft")
        if draft.status in {DraftStatus.SENDING.value, DraftStatus.SENT.value}:
            raise InvalidStateTransitionError("Draft", draft.status, "EDIT")

        was_approved = draft.status == DraftStatus.APPROVED.value

        if subject is not None:
            draft.subject = subject
        if body is not None:
            draft.body = body
        if tone is not None:
            draft.tone = tone

        # HARD SAFETY RULE: Any modification clears approval and resets status to DRAFTED
        if was_approved:
            draft.status = DraftStatus.DRAFTED.value
            draft.approved_content_sha256 = None
            draft.approved_at = None
            draft.approved_by_user_id = None
            logger.info("draft_approval_reset_due_to_edit", draft_id=str(draft.id))

        await self._audit_repo.record(
            action="DRAFT_RESET_TO_DRAFTED" if was_approved else "DRAFT_EDITED",
            target_id=draft.id,
            user_id=user_id,
            details={"reset_from_approved": was_approved},
        )
        await self._session.commit()
        return draft

    async def approve_draft(
        self,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
    ) -> Draft:
        """Explicit human approval. Seals the cryptographic SHA-256 hash in database."""
        draft = await self._draft_repo.get_by_id(draft_id)
        if draft is None:
            raise NotFoundError("Draft not found")
        if draft.user_id != user_id:
            raise AuthorizationError("Access denied to draft")
        if draft.status != DraftStatus.DRAFTED.value:
            raise InvalidStateTransitionError("Draft", draft.status, "APPROVE")

        # Compute authoritative hash of subject and body
        content_hash = compute_content_sha256(draft.subject, draft.body)

        draft.status = DraftStatus.APPROVED.value
        draft.approved_content_sha256 = content_hash
        draft.approved_at = datetime.now(UTC)
        draft.approved_by_user_id = user_id

        await self._audit_repo.record(
            action="DRAFT_APPROVED",
            target_id=draft.id,
            user_id=user_id,
            content_sha256=content_hash,
            details={"approved_by": str(user_id)},
        )
        await self._session.commit()
        logger.info("draft_approved_and_sealed", draft_id=str(draft.id), sha256=content_hash[:16])
        return draft

    async def send_draft(
        self,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
        idempotency_key: str | None = None,
    ) -> Draft:
        """Verify cryptographic hash seal and send draft to Gmail with row-level idempotency lock."""
        # Acquire row lock: SELECT ... FOR UPDATE
        draft = await self._draft_repo.get_for_update(draft_id)
        if draft is None:
            raise NotFoundError("Draft not found")
        if draft.user_id != user_id:
            raise AuthorizationError("Access denied to draft")

        # Idempotent re-send protection: if already sent, return immediately
        if draft.status == DraftStatus.SENT.value:
            logger.info("draft_already_sent_idempotent_return", draft_id=str(draft_id))
            return draft

        # Domain Invariant: Must be APPROVED
        if draft.status != DraftStatus.APPROVED.value:
            raise InvalidStateTransitionError(
                entity="Draft",
                current_state=draft.status,
                attempted_action="SEND",
            )

        # Cryptographic Hash Seal Verification
        current_hash = compute_content_sha256(draft.subject, draft.body)
        if current_hash != draft.approved_content_sha256:
            await self._audit_repo.record(
                action="CONTENT_TAMPER_DETECTED",
                target_id=draft.id,
                user_id=user_id,
                content_sha256=current_hash,
                details={
                    "expected_sha256": draft.approved_content_sha256,
                    "computed_sha256": current_hash,
                },
            )
            await self._session.commit()
            raise ContentTamperError(
                "Draft content does not match approved cryptographic SHA-256 seal! "
                "Sending aborted for safety."
            )

        # Transition to SENDING
        draft.status = DraftStatus.SENDING.value
        draft.send_idempotency_key = idempotency_key or str(uuid.uuid4())
        await self._session.flush()

        # Send via Gmail API
        cred = await self._user_repo.get_oauth_credential(user_id)
        if cred is None:
            raise AuthorizationError("No connected Google OAuth credentials to dispatch email.")

        gmail_client = GmailClient(
            credential=cred,
            token_vault=self._token_vault,
            user_repo=self._user_repo,
            settings=self._settings,
        )

        try:
            resp = await gmail_client.send_message(
                to=draft.to_email,
                subject=draft.subject,
                body=draft.body,
                thread_id=draft.gmail_thread_id,
            )
            sent_msg_id = resp.get("id", "")

            # Transition to SENT
            draft.status = DraftStatus.SENT.value
            draft.sent_at = datetime.now(UTC)
            draft.gmail_message_id = sent_msg_id

            await self._audit_repo.record(
                action="DRAFT_SENT",
                target_id=draft.id,
                user_id=user_id,
                content_sha256=current_hash,
                details={"gmail_message_id": sent_msg_id},
            )
            await self._session.commit()
            logger.info("draft_successfully_sent", draft_id=str(draft.id), gmail_id=sent_msg_id)
            return draft

        except Exception as err:
            logger.error("draft_send_dispatch_error", draft_id=str(draft.id), error=str(err))
            draft.status = DraftStatus.APPROVED.value  # Rollback state so user can retry
            await self._session.commit()
            raise

    async def list_drafts(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DraftListResponse:
        """List drafts for the current user."""
        items = await self._draft_repo.list_drafts(user_id=user_id, status=status, limit=limit, offset=offset)
        total = await self._draft_repo.count_drafts(user_id=user_id, status=status)
        return DraftListResponse(
            items=[DraftResponse.model_validate(d) for d in items],
            total=total,
        )

    async def get_draft(self, user_id: uuid.UUID, draft_id: uuid.UUID) -> Draft:
        """Get single draft by ID with ownership verification."""
        draft = await self._draft_repo.get_by_id(draft_id)
        if draft is None:
            raise NotFoundError("Draft not found")
        if draft.user_id != user_id:
            raise AuthorizationError("Access denied to draft")
        return draft
