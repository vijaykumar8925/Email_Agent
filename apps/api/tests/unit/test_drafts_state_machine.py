"""Unit tests for the Draft Approval State Machine and Cryptographic Content Sealing."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from mailagent.core.errors import ContentTamperError, InvalidStateTransitionError
from mailagent.drafts.models import Draft, DraftStatus, compute_content_sha256
from mailagent.drafts.service import DraftService


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_draft_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_email_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_audit_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_vault() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def draft_service(
    mock_session: AsyncMock,
    mock_draft_repo: AsyncMock,
    mock_email_repo: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_audit_repo: AsyncMock,
    mock_vault: AsyncMock,
) -> DraftService:
    return DraftService(
        session=mock_session,
        draft_repo=mock_draft_repo,
        email_repo=mock_email_repo,
        user_repo=mock_user_repo,
        audit_repo=mock_audit_repo,
        token_vault=mock_vault,
    )


class TestDraftApprovalStateMachine:
    """Tests enforcing domain invariants from ADR 0003."""

    def test_compute_content_sha256_deterministic(self) -> None:
        subject = "Meeting Tomorrow"
        body = "Hi team, see you at 10 AM."
        hash1 = compute_content_sha256(subject, body)
        hash2 = compute_content_sha256(subject, body)
        assert hash1 == hash2
        assert len(hash1) == 64

    @pytest.mark.asyncio
    async def test_approve_draft_seals_hash_and_transitions_state(
        self,
        draft_service: DraftService,
        mock_draft_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        draft_id = uuid.uuid4()
        draft = Draft(
            id=draft_id,
            user_id=user_id,
            mailbox_id=uuid.uuid4(),
            to_email="client@example.com",
            subject="Project Proposal",
            body="Here is our proposal for Q4.",
            status=DraftStatus.DRAFTED.value,
        )
        mock_draft_repo.get_by_id.return_value = draft

        approved_draft = await draft_service.approve_draft(user_id=user_id, draft_id=draft_id)

        assert approved_draft.status == DraftStatus.APPROVED.value
        assert approved_draft.approved_content_sha256 is not None
        assert approved_draft.approved_at is not None
        assert approved_draft.approved_by_user_id == user_id

        # Verify audit log
        mock_audit_repo.record.assert_called_once()
        call_kwargs = mock_audit_repo.record.call_args.kwargs
        assert call_kwargs["action"] == "DRAFT_APPROVED"
        assert call_kwargs["content_sha256"] == approved_draft.approved_content_sha256

    @pytest.mark.asyncio
    async def test_editing_approved_draft_resets_status_to_drafted(
        self,
        draft_service: DraftService,
        mock_draft_repo: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        draft_id = uuid.uuid4()
        sealed_hash = compute_content_sha256("Subject", "Original Body")
        draft = Draft(
            id=draft_id,
            user_id=user_id,
            mailbox_id=uuid.uuid4(),
            to_email="client@example.com",
            subject="Subject",
            body="Original Body",
            status=DraftStatus.APPROVED.value,
            approved_content_sha256=sealed_hash,
        )
        mock_draft_repo.get_by_id.return_value = draft

        updated_draft = await draft_service.update_draft(
            user_id=user_id,
            draft_id=draft_id,
            body="Modified Body After Approval",
        )

        # Invariant check: MUST reset to DRAFTED and clear the cryptographic seal
        assert updated_draft.status == DraftStatus.DRAFTED.value
        assert updated_draft.approved_content_sha256 is None
        assert updated_draft.approved_at is None

    @pytest.mark.asyncio
    async def test_cannot_send_unapproved_draft(
        self,
        draft_service: DraftService,
        mock_draft_repo: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        draft_id = uuid.uuid4()
        draft = Draft(
            id=draft_id,
            user_id=user_id,
            mailbox_id=uuid.uuid4(),
            to_email="client@example.com",
            subject="Contract",
            body="Review attached",
            status=DraftStatus.DRAFTED.value,  # NOT APPROVED
        )
        mock_draft_repo.get_for_update.return_value = draft

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            await draft_service.send_draft(user_id=user_id, draft_id=draft_id)

        assert "Cannot perform 'SEND' on Draft in state 'DRAFTED'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tampered_content_aborts_send_with_content_tamper_error(
        self,
        draft_service: DraftService,
        mock_draft_repo: AsyncMock,
        mock_audit_repo: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        draft_id = uuid.uuid4()
        approved_subject = "Original Subject"
        approved_body = "Original Body"
        sealed_hash = compute_content_sha256(approved_subject, approved_body)

        # Simulating out-of-band tampering directly in the DB
        draft = Draft(
            id=draft_id,
            user_id=user_id,
            mailbox_id=uuid.uuid4(),
            to_email="client@example.com",
            subject=approved_subject,
            body="Maliciously modified body bypass",
            status=DraftStatus.APPROVED.value,
            approved_content_sha256=sealed_hash,
        )
        mock_draft_repo.get_for_update.return_value = draft

        with pytest.raises(ContentTamperError) as exc_info:
            await draft_service.send_draft(user_id=user_id, draft_id=draft_id)

        assert "CONTENT_TAMPER_DETECTED" in exc_info.value.code

        # Tamper event must be audited
        mock_audit_repo.record.assert_called_once()
        assert mock_audit_repo.record.call_args.kwargs["action"] == "CONTENT_TAMPER_DETECTED"

    @pytest.mark.asyncio
    async def test_idempotent_re_send_returns_without_dispatch(
        self,
        draft_service: DraftService,
        mock_draft_repo: AsyncMock,
    ) -> None:
        user_id = uuid.uuid4()
        draft_id = uuid.uuid4()
        draft = Draft(
            id=draft_id,
            user_id=user_id,
            mailbox_id=uuid.uuid4(),
            to_email="client@example.com",
            subject="Sent Subject",
            body="Sent Body",
            status=DraftStatus.SENT.value,
            gmail_message_id="msg_12345",
        )
        mock_draft_repo.get_for_update.return_value = draft

        res = await draft_service.send_draft(user_id=user_id, draft_id=draft_id)
        assert res.status == DraftStatus.SENT.value
        assert res.gmail_message_id == "msg_12345"
