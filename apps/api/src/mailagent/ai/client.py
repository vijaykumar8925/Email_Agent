"""AI client implementations for Ollama (local) and Anthropic (cloud).

Provides unified async chat completion interface with structured JSON mode,
timeout handling, retry resilience, and model introspection.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from mailagent.core.config import Settings, get_settings
from mailagent.core.errors import ExternalServiceError
from mailagent.core.logging import get_logger

logger = get_logger(__name__)


def extract_json_from_text(text: str) -> dict[str, Any]:
    """Extract and parse JSON from raw LLM output even if surrounded by markdown code blocks."""
    trimmed = text.strip()
    if not trimmed:
        raise ValueError("Empty response from AI model")

    # If it directly parses as JSON:
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        pass

    # Try removing markdown code blocks: ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", trimmed)
    if match:
        code_block = match.group(1).strip()
        try:
            return json.loads(code_block)
        except json.JSONDecodeError:
            pass

    # Try finding the first '{' and last '}'
    first_brace = trimmed.find("{")
    last_brace = trimmed.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = trimmed[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse valid JSON from AI output: {trimmed[:200]}")


class BaseAIClient(ABC):
    """Abstract interface for AI chat completion providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
    ) -> str:
        """Execute chat completion and return response text."""
        ...

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Return list of models available from the provider."""
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform connectivity and health check against the provider."""
        ...


class OllamaClient(BaseAIClient):
    """Client for local Ollama server running on http://localhost:11434."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base_url = self._settings.ollama_base_url.rstrip("/")
        self._timeout = float(self._settings.ollama_timeout_seconds)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
    ) -> str:
        """Call Ollama /api/chat endpoint."""
        url = f"{self._base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code != 200:
                    logger.error(
                        "ollama_api_error",
                        status_code=response.status_code,
                        response=response.text[:500],
                        model=model,
                    )
                    raise ExternalServiceError(
                        f"Ollama returned HTTP {response.status_code}: {response.text[:200]}"
                    )

                data = response.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise ExternalServiceError("Ollama returned an empty response message content")
                return content

        except httpx.ConnectError as err:
            logger.error("ollama_connection_failed", base_url=self._base_url, error=str(err))
            raise ExternalServiceError(
                f"Cannot connect to Ollama at {self._base_url}. Ensure Ollama is running (`ollama serve`)."
            ) from err
        except httpx.TimeoutException as err:
            logger.error("ollama_request_timeout", timeout=self._timeout, model=model)
            raise ExternalServiceError(
                f"Ollama request timed out after {self._timeout}s for model {model}."
            ) from err
        except Exception as err:
            if isinstance(err, ExternalServiceError):
                raise
            logger.error("ollama_unexpected_error", error=str(err))
            raise ExternalServiceError(f"Unexpected error communicating with Ollama: {err}") from err

    async def list_models(self) -> list[str]:
        """Fetch list of local installed models from Ollama."""
        url = f"{self._base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", []) if "name" in m]
                    return models
                return []
        except Exception as err:
            logger.warning("ollama_list_models_failed", error=str(err))
            return []

    async def health_check(self) -> dict[str, Any]:
        """Verify Ollama is reachable and responsive."""
        try:
            models = await self.list_models()
            return {
                "provider": "ollama",
                "status": "healthy" if models else "degraded",
                "base_url": self._base_url,
                "available_models": models,
            }
        except Exception as err:
            return {
                "provider": "ollama",
                "status": "unhealthy",
                "base_url": self._base_url,
                "error": str(err),
            }


class AnthropicClient(BaseAIClient):
    """Client for Anthropic Claude API."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        json_mode: bool = True,
        temperature: float = 0.2,
    ) -> str:
        """Call Anthropic Messages API."""
        if not self._settings.anthropic_api_key or self._settings.anthropic_api_key.startswith("sk-ant-your"):
            raise ExternalServiceError("Anthropic API key is not configured.")

        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        system_content = ""
        user_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
            else:
                user_messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            response = await client.messages.create(
                model=model,
                max_tokens=self._settings.anthropic_max_tokens_classifier,
                temperature=temperature,
                system=system_content if system_content else None,  # type: ignore[arg-type]
                messages=user_messages,  # type: ignore[arg-type]
            )
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            return "".join(text_blocks)
        except Exception as err:
            logger.error("anthropic_api_error", error=str(err))
            raise ExternalServiceError(f"Anthropic API call failed: {err}") from err

    async def list_models(self) -> list[str]:
        return [
            self._settings.anthropic_model_classifier,
            self._settings.anthropic_model_drafter,
        ]

    async def health_check(self) -> dict[str, Any]:
        has_key = bool(self._settings.anthropic_api_key and not self._settings.anthropic_api_key.startswith("sk-ant-your"))
        return {
            "provider": "anthropic",
            "status": "healthy" if has_key else "unconfigured",
            "configured": has_key,
        }


def get_ai_client(settings: Settings | None = None) -> BaseAIClient:
    """Factory creating the configured AI client based on application settings."""
    cfg = settings or get_settings()
    if cfg.ai_provider.lower() == "anthropic":
        return AnthropicClient(cfg)
    return OllamaClient(cfg)
