"""AI module — Ollama (local private) and Anthropic integration.

Exposes triage classification, reply drafting, and router endpoints.
"""

from mailagent.ai.client import BaseAIClient, OllamaClient, extract_json_from_text, get_ai_client
from mailagent.ai.router import router as ai_router
from mailagent.ai.schemas import (
    AIHealthResponse,
    DraftReplyResult,
    DraftTone,
    EmailCategory,
    EmailTriageResult,
    GenerateDraftInput,
    TriageEmailInput,
)
from mailagent.ai.service import AIService

__all__ = [
    "AIHealthResponse",
    "AIService",
    "BaseAIClient",
    "DraftReplyResult",
    "DraftTone",
    "EmailCategory",
    "EmailTriageResult",
    "GenerateDraftInput",
    "OllamaClient",
    "TriageEmailInput",
    "ai_router",
    "extract_json_from_text",
    "get_ai_client",
]
