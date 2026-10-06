"""FastAPI router exposing AI triage and draft generation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from mailagent.ai.schemas import (
    AIHealthResponse,
    DraftReplyResult,
    EmailTriageResult,
    GenerateDraftInput,
    TriageEmailInput,
)
from mailagent.ai.service import AIService
from mailagent.core.deps import get_optional_current_user, get_settings_dep
from mailagent.core.logging import get_logger
from mailagent.users.models import User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


def get_ai_service() -> AIService:
    """Dependency provider for AIService."""
    return AIService()


@router.get(
    "/status",
    response_model=AIHealthResponse,
    summary="Check AI subsystem health and provider status",
)
async def ai_status(
    service: AIService = Depends(get_ai_service),
) -> AIHealthResponse:
    """Return AI health, provider (Ollama/Anthropic), and available models."""
    return await service.get_health()


@router.get(
    "/models",
    response_model=list[str],
    summary="List available AI models from active provider",
)
async def list_ai_models(
    service: AIService = Depends(get_ai_service),
) -> list[str]:
    """Return names of models installed locally in Ollama or configured in Anthropic."""
    health = await service.get_health()
    return health.available_models


@router.post(
    "/triage",
    response_model=EmailTriageResult,
    summary="Analyze and categorize incoming email",
)
async def triage_email(
    payload: TriageEmailInput,
    service: AIService = Depends(get_ai_service),
    _user: User | None = Depends(get_optional_current_user),
) -> EmailTriageResult:
    """Run AI classification on email text, returning importance, category, and summary."""
    return await service.triage_email(payload)


@router.post(
    "/draft",
    response_model=DraftReplyResult,
    summary="Generate suggested email reply draft",
)
async def generate_draft(
    payload: GenerateDraftInput,
    service: AIService = Depends(get_ai_service),
    _user: User | None = Depends(get_optional_current_user),
) -> DraftReplyResult:
    """Generate a context-aware email reply draft in DRAFTED status."""
    # If sender_name wasn't explicitly supplied, populate with signed-in user's name if available
    if not payload.sender_name and _user and _user.display_name:
        payload.sender_name = _user.display_name

    return await service.generate_draft(payload)
