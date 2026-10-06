"""Email domain service orchestrating Gmail sync, database persistence, and AI triage."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from mailagent.ai.schemas import TriageEmailInput
from mailagent.ai.service import AIService
from mailagent.core.config import Settings, get_settings
from mailagent.core.errors import AuthorizationError, NotFoundError
from mailagent.core.logging import get_logger
from mailagent.core.security import TokenVault
from mailagent.emails.models import EmailMessage
from mailagent.emails.repository import EmailRepository
from mailagent.emails.schemas import EmailListResponse, EmailMessageResponse, SyncMailboxResult
from mailagent.providers.gmail.client import GmailClient
from mailagent.users.repository import UserRepository

logger = get_logger(__name__)


class EmailService:
    """Business service for email ingestion, inbox sync, and local triage."""

    def __init__(
        self,
        session: AsyncSession,
        email_repo: EmailRepository,
        user_repo: UserRepository,
        token_vault: TokenVault,
        ai_service: AIService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._email_repo = email_repo
        self._user_repo = user_repo
        self._token_vault = token_vault
        self._ai_service = ai_service or AIService()
        self._settings = settings or get_settings()

    async def sync_mailbox(
        self,
        user_id: uuid.UUID,
        max_messages: int = 10,
        query: str = "label:INBOX",
    ) -> SyncMailboxResult:
        """Fetch latest messages from Gmail, ingest them, and run local AI triage."""
        start_time = time.monotonic()

        # Retrieve user and credential
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")

        cred = await self._user_repo.get_oauth_credential(user_id)
        if cred is None:
            raise AuthorizationError("No connected Google account found for user. Please sign in with Google.")

        # Ensure mailbox exists
        mailbox = await self._user_repo.get_mailbox_by_address(user.email)
        if mailbox is None:
            mailbox = await self._user_repo.create_mailbox(user_id=user.id, gmail_address=user.email)

        # Initialize Gmail Client
        gmail_client = GmailClient(
            credential=cred,
            token_vault=self._token_vault,
            user_repo=self._user_repo,
            settings=self._settings,
        )

        logger.info("mailbox_sync_started", user_email=user.email, max_messages=max_messages)

        # List message IDs
        msg_summaries = await gmail_client.list_messages(query=query, max_results=max_messages)

        synced_count = 0
        new_messages = 0
        triaged_count = 0
        newly_created_msgs: list[EmailMessage] = []

        for item in msg_summaries:
            msg_id = item["id"]
            synced_count += 1

            try:
                raw_msg = await gmail_client.get_message(msg_id)
                parsed = gmail_client.parse_message(raw_msg)

                # Upsert thread
                thread = await self._email_repo.upsert_thread(
                    mailbox_id=mailbox.id,
                    gmail_thread_id=parsed.gmail_thread_id,
                    subject=parsed.subject,
                    snippet=parsed.snippet,
                    last_message_at=parsed.received_at,
                    is_unread="UNREAD" in parsed.labels,
                )

                # Upsert message
                msg, is_created = await self._email_repo.upsert_message(
                    mailbox_id=mailbox.id,
                    thread_id=thread.id,
                    gmail_message_id=parsed.gmail_message_id,
                    gmail_thread_id=parsed.gmail_thread_id,
                    sender=parsed.sender,
                    recipient=parsed.recipient,
                    subject=parsed.subject,
                    snippet=parsed.snippet,
                    body_text=parsed.body_text,
                    body_html=parsed.body_html,
                    received_at=parsed.received_at,
                    is_unread="UNREAD" in parsed.labels,
                    labels=parsed.labels,
                )

                if is_created:
                    new_messages += 1
                    newly_created_msgs.append(msg)

            except Exception as err:
                logger.error("email_fetch_error", msg_id=msg_id, error=str(err))

        mailbox.last_synced_at = datetime.now(UTC)
        # Commit ingested emails immediately so they are visible right away
        await self._session.commit()

        # Run Local Ollama AI Triage on the first 2 new messages immediately
        # Remaining messages are triaged asynchronously in the background to prevent proxy timeouts
        immediate_triage_limit = 2
        for i, msg in enumerate(newly_created_msgs):
            if i >= immediate_triage_limit:
                break
            try:
                triage_input = TriageEmailInput(
                    subject=msg.subject,
                    sender=msg.sender,
                    recipient=msg.recipient,
                    body=msg.body_text,
                )
                triage_res = await self._ai_service.triage_email(triage_input)

                await self._email_repo.update_message_triage(
                    message_id=msg.id,
                    category=triage_res.category.value,
                    importance=triage_res.importance,
                    needs_reply=triage_res.needs_reply,
                    summary=triage_res.summary,
                    suggested_action=triage_res.suggested_action,
                    triaged_at=datetime.now(UTC),
                )
                await self._session.commit()
                triaged_count += 1
            except Exception as err:
                logger.warning(
                    "email_triage_failed_for_message",
                    gmail_id=msg.gmail_message_id,
                    error=str(err),
                )

        # Trigger background triage for any remaining messages
        remaining_msgs = newly_created_msgs[immediate_triage_limit:]
        if remaining_msgs:
            import asyncio
            remaining_ids = [m.id for m in remaining_msgs]
            asyncio.create_task(self._run_background_triage(remaining_ids))

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)
        logger.info(
            "mailbox_sync_completed",
            user_email=user.email,
            synced_count=synced_count,
            new_messages=new_messages,
            triaged_count=triaged_count,
            duration_ms=duration_ms,
        )

        return SyncMailboxResult(
            mailbox_id=mailbox.id,
            gmail_address=mailbox.gmail_address,
            synced_count=synced_count,
            new_messages=new_messages,
            triaged_count=triaged_count,
            duration_ms=duration_ms,
        )

    async def _run_background_triage(self, message_ids: list[uuid.UUID]) -> None:
        """Background coroutine to triage remaining messages with independent DB session."""
        try:
            from mailagent.db.session import get_session_factory
            factory = get_session_factory()
            async with factory() as session:
                repo = EmailRepository(session)
                for mid in message_ids:
                    msg = await repo.get_message_by_id(mid)
                    if not msg or msg.triaged_at is not None:
                        continue
                    try:
                        triage_input = TriageEmailInput(
                            subject=msg.subject,
                            sender=msg.sender,
                            recipient=msg.recipient,
                            body=msg.body_text,
                        )
                        triage_res = await self._ai_service.triage_email(triage_input)
                        await repo.update_message_triage(
                            message_id=msg.id,
                            category=triage_res.category.value,
                            importance=triage_res.importance,
                            needs_reply=triage_res.needs_reply,
                            summary=triage_res.summary,
                            suggested_action=triage_res.suggested_action,
                            triaged_at=datetime.now(UTC),
                        )
                        await session.commit()
                        logger.info("background_email_triage_completed", email_id=str(mid))
                    except Exception as err:
                        logger.warning("background_email_triage_failed", email_id=str(mid), error=str(err))
        except Exception as err:
            logger.error("background_triage_task_error", error=str(err))

    async def triage_message(self, user_id: uuid.UUID, email_id: uuid.UUID) -> EmailMessage:
        """Run or refresh local AI triage on an email message."""
        msg = await self.get_email(user_id=user_id, email_id=email_id)
        triage_input = TriageEmailInput(
            subject=msg.subject,
            sender=msg.sender,
            recipient=msg.recipient,
            body=msg.body_text,
        )
        triage_res = await self._ai_service.triage_email(triage_input)
        updated = await self._email_repo.update_message_triage(
            message_id=msg.id,
            category=triage_res.category.value,
            importance=triage_res.importance,
            needs_reply=triage_res.needs_reply,
            summary=triage_res.summary,
            suggested_action=triage_res.suggested_action,
            triaged_at=datetime.now(UTC),
        )
        await self._session.commit()
        return updated or msg


    async def list_emails(
        self,
        user_id: uuid.UUID,
        category: str | None = None,
        min_importance: int | None = None,
        needs_reply: bool | None = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> EmailListResponse:
        """List triaged emails for the authenticated user's mailbox."""
        mailbox = await self._user_repo.get_default_mailbox_for_user(user_id)
        if mailbox is None:
            return EmailListResponse(items=[], total=0)

        items = await self._email_repo.list_messages(
            mailbox_id=mailbox.id,
            category=category,
            min_importance=min_importance,
            needs_reply=needs_reply,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
        total = await self._email_repo.count_messages(
            mailbox_id=mailbox.id,
            category=category,
            min_importance=min_importance,
            unread_only=unread_only,
        )

        responses = [EmailMessageResponse.model_validate(m) for m in items]
        return EmailListResponse(items=responses, total=total)

    async def get_email(self, user_id: uuid.UUID, email_id: uuid.UUID) -> EmailMessage:
        """Retrieve a specific email message ensuring user ownership."""
        msg = await self._email_repo.get_message_by_id(email_id)
        if msg is None:
            raise NotFoundError("Email message not found")

        mailbox = await self._user_repo.get_default_mailbox_for_user(user_id)
        if mailbox is None or msg.mailbox_id != mailbox.id:
            raise AuthorizationError("Access denied to this email message")

        return msg
