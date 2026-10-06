"""Drafts module — draft model, approval state machine, send service, schemas, router."""

from mailagent.drafts.models import Draft, DraftStatus, compute_content_sha256
from mailagent.drafts.repository import DraftRepository
from mailagent.drafts.router import router as draft_router
from mailagent.drafts.schemas import (
    CreateDraftRequest,
    DraftListResponse,
    DraftResponse,
    SendDraftRequest,
    UpdateDraftRequest,
)
from mailagent.drafts.service import DraftService

__all__ = [
    "CreateDraftRequest",
    "Draft",
    "DraftListResponse",
    "DraftRepository",
    "DraftResponse",
    "DraftService",
    "DraftStatus",
    "SendDraftRequest",
    "UpdateDraftRequest",
    "compute_content_sha256",
    "draft_router",
]
