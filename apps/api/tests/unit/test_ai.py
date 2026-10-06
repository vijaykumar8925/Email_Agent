"""Unit tests for the AI Engine (triage classification, drafting, and router)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from mailagent.ai.client import BaseAIClient, extract_json_from_text
from mailagent.ai.schemas import (
    DraftTone,
    EmailCategory,
    GenerateDraftInput,
    TriageEmailInput,
)
from mailagent.ai.service import AIService


class DummyAIClient(BaseAIClient):
    """Dummy AI client for controlled deterministic testing."""

    def __init__(self, response_text: str = "{}") -> None:
        self.response_text = response_text
        self.last_messages: list[dict[str, str]] = []

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
    ) -> str:
        self.last_messages = messages
        return self.response_text

    async def list_models(self) -> list[str]:
        return ["phi4-mini:latest", "qwen3:4b", "qwen3:0.6b"]

    async def health_check(self) -> dict[str, str]:
        return {"provider": "ollama", "status": "healthy"}


class TestAIJsonExtractor:
    """Tests for extract_json_from_text utility."""

    def test_parses_plain_json(self) -> None:
        raw = '{"category": "work", "importance": 4}'
        data = extract_json_from_text(raw)
        assert data["category"] == "work"
        assert data["importance"] == 4

    def test_parses_markdown_json_block(self) -> None:
        raw = """Here is the result:
```json
{
  "category": "finance",
  "importance": 5,
  "needs_reply": true
}
```
Hope this helps!"""
        data = extract_json_from_text(raw)
        assert data["category"] == "finance"
        assert data["importance"] == 5
        assert data["needs_reply"] is True

    def test_parses_markdown_block_without_tag(self) -> None:
        raw = """```
{"summary": "A meeting invite"}
```"""
        data = extract_json_from_text(raw)
        assert data["summary"] == "A meeting invite"

    def test_parses_raw_text_containing_braces(self) -> None:
        raw = 'Some text before {"category": "alerts"} some text after'
        data = extract_json_from_text(raw)
        assert data["category"] == "alerts"

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="Could not parse valid JSON"):
            extract_json_from_text("This is definitely not json")


class TestAIService:
    """Tests for AIService triage and draft generation."""

    @pytest.mark.asyncio
    async def test_triage_email_success(self) -> None:
        mock_response = json.dumps({
            "category": "work",
            "importance": 4,
            "needs_reply": True,
            "summary": "Project status review meeting scheduled for tomorrow.",
            "suggested_action": "reply",
            "reasoning_short": "Direct meeting invitation from manager.",
        })
        client = DummyAIClient(response_text=mock_response)
        service = AIService(client=client)

        payload = TriageEmailInput(
            subject="Project Sync Tomorrow",
            sender="manager@example.com",
            body="Hey, can you attend the project sync tomorrow at 10 AM?",
        )

        result = await service.triage_email(payload)

        assert result.category == EmailCategory.WORK
        assert result.importance == 4
        assert result.needs_reply is True
        assert "Project status review" in result.summary
        assert result.suggested_action == "reply"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_triage_email_clamps_importance_and_defaults_category(self) -> None:
        mock_response = json.dumps({
            "category": "unknown_future_category",
            "importance": 99,  # Out of 1..5 range
            "needs_reply": False,
            "summary": "Newsletter digest",
        })
        client = DummyAIClient(response_text=mock_response)
        service = AIService(client=client)

        payload = TriageEmailInput(
            subject="Weekly Digest",
            sender="digest@example.com",
            body="Here are top stories of the week.",
        )

        result = await service.triage_email(payload)

        assert result.category == EmailCategory.OTHER
        assert result.importance == 5  # Clamped to maximum 5
        assert result.needs_reply is False

    @pytest.mark.asyncio
    async def test_generate_draft_success(self) -> None:
        mock_response = json.dumps({
            "subject": "Re: Project Sync Tomorrow",
            "body": "Hi,\n\nI confirm I will be there at 10 AM.\n\nBest,\nVijay",
        })
        client = DummyAIClient(response_text=mock_response)
        service = AIService(client=client)

        payload = GenerateDraftInput(
            email_subject="Project Sync Tomorrow",
            email_sender="manager@example.com",
            email_body="Can you attend the project sync tomorrow at 10 AM?",
            user_instructions="Confirm attendance at 10 AM",
            tone=DraftTone.PROFESSIONAL,
            sender_name="Vijay",
        )

        result = await service.generate_draft(payload)

        assert result.subject == "Re: Project Sync Tomorrow"
        assert "confirm I will be there" in result.body
        assert result.tone == "professional"
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_get_health(self) -> None:
        client = DummyAIClient()
        service = AIService(client=client)

        health = await service.get_health()

        assert health.provider == "ollama"
        assert health.status == "healthy"
        assert "phi4-mini:latest" in health.available_models


class TestAIRouter:
    """Integration-style tests for AI endpoints via test client."""

    @pytest.mark.asyncio
    async def test_get_ai_status(self, client: AsyncClient, app: Any) -> None:
        from mailagent.ai.router import get_ai_service
        from mailagent.ai.schemas import AIHealthResponse

        mock_service = AsyncMock()
        mock_service.get_health.return_value = AIHealthResponse(
            provider="ollama",
            status="healthy",
            base_url="http://localhost:11434",
            classifier_model="phi4-mini:latest",
            drafter_model="phi4-mini:latest",
            available_models=["phi4-mini:latest", "qwen3:4b"],
        )
        app.dependency_overrides[get_ai_service] = lambda: mock_service

        res = await client.get("/api/v1/ai/status")
        assert res.status_code == 200
        data = res.json()
        assert data["provider"] == "ollama"
        assert data["classifier_model"] == "phi4-mini:latest"
        assert "phi4-mini:latest" in data["available_models"]

    @pytest.mark.asyncio
    async def test_get_ai_models(self, client: AsyncClient, app: Any) -> None:
        from mailagent.ai.router import get_ai_service
        from mailagent.ai.schemas import AIHealthResponse

        mock_service = AsyncMock()
        mock_service.get_health.return_value = AIHealthResponse(
            provider="ollama",
            status="healthy",
            base_url="http://localhost:11434",
            classifier_model="phi4-mini:latest",
            drafter_model="phi4-mini:latest",
            available_models=["phi4-mini:latest", "qwen3:4b"],
        )
        app.dependency_overrides[get_ai_service] = lambda: mock_service

        res = await client.get("/api/v1/ai/models")
        assert res.status_code == 200
        models = res.json()
        assert "phi4-mini:latest" in models

    @pytest.mark.asyncio
    async def test_post_ai_triage(self, client: AsyncClient, app: Any) -> None:
        from mailagent.ai.router import get_ai_service
        from mailagent.ai.schemas import EmailTriageResult

        mock_service = AsyncMock()
        mock_service.triage_email.return_value = EmailTriageResult(
            category=EmailCategory.WORK,
            importance=4,
            needs_reply=True,
            summary="Client contract review request",
            suggested_action="reply",
            reasoning_short="Client deadline mentioned",
            model_used="phi4-mini:latest",
            latency_ms=120.0,
        )
        app.dependency_overrides[get_ai_service] = lambda: mock_service

        res = await client.post(
            "/api/v1/ai/triage",
            json={
                "subject": "Contract Review",
                "sender": "client@enterprise.com",
                "body": "Please review the attached contract by Friday.",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["category"] == "work"
        assert data["importance"] == 4
        assert data["needs_reply"] is True
        assert data["suggested_action"] == "reply"

    @pytest.mark.asyncio
    async def test_post_ai_draft(self, client: AsyncClient, app: Any) -> None:
        from mailagent.ai.router import get_ai_service
        from mailagent.ai.schemas import DraftReplyResult

        mock_service = AsyncMock()
        mock_service.generate_draft.return_value = DraftReplyResult(
            subject="Re: Contract Review",
            body="Thank you. I have reviewed the contract and it looks good.",
            tone="professional",
            model_used="phi4-mini:latest",
            latency_ms=150.0,
        )
        app.dependency_overrides[get_ai_service] = lambda: mock_service

        res = await client.post(
            "/api/v1/ai/draft",
            json={
                "email_subject": "Contract Review",
                "email_sender": "client@enterprise.com",
                "email_body": "Please review the attached contract by Friday.",
                "user_instructions": "Confirm review and express approval",
                "tone": "professional",
                "sender_name": "Vijay",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["subject"] == "Re: Contract Review"
        assert "reviewed the contract" in data["body"]
