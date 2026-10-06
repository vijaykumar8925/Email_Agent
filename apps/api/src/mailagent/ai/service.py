"""AI Service orchestrating email triage and reply drafting.

Coordinates prompt assembly, client invocations, structured parsing,
sanitization, and telemetry.
"""

from __future__ import annotations

import time
from typing import Any

from mailagent.ai.client import BaseAIClient, extract_json_from_text, get_ai_client
from mailagent.ai.prompts.classifier import CLASSIFIER_SYSTEM_PROMPT, build_triage_user_prompt
from mailagent.ai.prompts.drafter import DRAFTER_SYSTEM_PROMPT, build_draft_user_prompt
from mailagent.ai.schemas import (
    AIHealthResponse,
    DraftReplyResult,
    EmailCategory,
    EmailTriageResult,
    GenerateDraftInput,
    TriageEmailInput,
)
from mailagent.core.config import Settings, get_settings
from mailagent.core.logging import get_logger

logger = get_logger(__name__)


class AIService:
    """Core domain service for AI email processing."""

    def __init__(
        self,
        client: BaseAIClient | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or get_ai_client(self._settings)

    @property
    def classifier_model(self) -> str:
        """Get configured classifier model name."""
        if self._settings.ai_provider.lower() == "anthropic":
            return self._settings.anthropic_model_classifier
        return self._settings.ollama_model_classifier

    @property
    def drafter_model(self) -> str:
        """Get configured drafter model name."""
        if self._settings.ai_provider.lower() == "anthropic":
            return self._settings.anthropic_model_drafter
        return self._settings.ollama_model_drafter

    async def triage_email(self, payload: TriageEmailInput) -> EmailTriageResult:
        """Analyze an incoming email and produce structured classification metadata."""
        start_time = time.monotonic()
        model_name = self.classifier_model

        system_prompt = CLASSIFIER_SYSTEM_PROMPT
        user_prompt = build_triage_user_prompt(
            subject=payload.subject,
            sender=payload.sender,
            recipient=payload.recipient,
            date=payload.date,
            body=payload.body,
            thread_history=payload.thread_history,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(
            "ai_triage_started",
            provider=self._settings.ai_provider,
            model=model_name,
            subject=payload.subject[:60],
        )

        raw_output = await self._client.chat_completion(
            messages,
            model=model_name,
            json_mode=True,
            temperature=self._settings.ollama_temperature,
        )

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)
        parsed_json = extract_json_from_text(raw_output)

        # Normalize category
        raw_cat = str(parsed_json.get("category", "other")).lower().strip()
        valid_cats = {c.value for c in EmailCategory}
        category = EmailCategory(raw_cat) if raw_cat in valid_cats else EmailCategory.OTHER

        # Clamp importance score 1..5
        try:
            importance = int(parsed_json.get("importance", 3))
            importance = max(1, min(5, importance))
        except (ValueError, TypeError):
            importance = 3

        needs_reply = bool(parsed_json.get("needs_reply", False))
        summary = str(parsed_json.get("summary", payload.subject)).strip()
        suggested_action = str(parsed_json.get("suggested_action", "review")).strip()
        reasoning_short = str(parsed_json.get("reasoning_short", "")).strip()

        result = EmailTriageResult(
            category=category,
            importance=importance,
            needs_reply=needs_reply,
            summary=summary,
            suggested_action=suggested_action,
            reasoning_short=reasoning_short,
            model_used=model_name,
            latency_ms=duration_ms,
        )

        logger.info(
            "ai_triage_completed",
            category=result.category.value,
            importance=result.importance,
            needs_reply=result.needs_reply,
            latency_ms=duration_ms,
            model=model_name,
        )

        return result

    async def generate_draft(self, payload: GenerateDraftInput) -> DraftReplyResult:
        """Draft a suggested reply adhering to user guidelines and context."""
        start_time = time.monotonic()
        model_name = self.drafter_model

        system_prompt = DRAFTER_SYSTEM_PROMPT
        user_prompt = build_draft_user_prompt(
            email_subject=payload.email_subject,
            email_sender=payload.email_sender,
            email_body=payload.email_body,
            user_instructions=payload.user_instructions,
            tone=payload.tone.value,
            sender_name=payload.sender_name,
            thread_history=payload.thread_history,
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(
            "ai_draft_started",
            provider=self._settings.ai_provider,
            model=model_name,
            tone=payload.tone.value,
            subject=payload.email_subject[:60],
        )

        raw_output = await self._client.chat_completion(
            messages,
            model=model_name,
            json_mode=True,
            temperature=self._settings.ollama_temperature,
        )

        duration_ms = round((time.monotonic() - start_time) * 1000, 2)
        parsed_json = extract_json_from_text(raw_output)

        prefix = "Re: " if not payload.email_subject.lower().startswith("re:") else ""
        default_subject = f"{prefix}{payload.email_subject}".strip()

        subject = str(parsed_json.get("subject", default_subject)).strip()
        body = str(parsed_json.get("body", "")).strip()

        result = DraftReplyResult(
            subject=subject,
            body=body,
            tone=payload.tone.value,
            model_used=model_name,
            latency_ms=duration_ms,
        )

        logger.info(
            "ai_draft_completed",
            subject=result.subject[:60],
            latency_ms=duration_ms,
            model=model_name,
        )

        return result

    async def get_health(self) -> AIHealthResponse:
        """Check AI subsystem health and list available models."""
        client_health = await self._client.health_check()
        available_models = await self._client.list_models()

        return AIHealthResponse(
            provider=self._settings.ai_provider,
            status=client_health.get("status", "unknown"),
            base_url=self._settings.ollama_base_url if self._settings.ai_provider == "ollama" else "api.anthropic.com",
            classifier_model=self.classifier_model,
            drafter_model=self.drafter_model,
            available_models=available_models,
            details=client_health,
        )
