"""Emails module — email models, repository, service, router, schemas."""

from mailagent.emails.models import EmailMessage, EmailThread
from mailagent.emails.repository import EmailRepository
from mailagent.emails.router import router as email_router
from mailagent.emails.schemas import EmailListResponse, EmailMessageResponse, SyncMailboxResult
from mailagent.emails.service import EmailService

__all__ = [
    "EmailListResponse",
    "EmailMessage",
    "EmailMessageResponse",
    "EmailRepository",
    "EmailService",
    "EmailThread",
    "SyncMailboxResult",
    "email_router",
]
