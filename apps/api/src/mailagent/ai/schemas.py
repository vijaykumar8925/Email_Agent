"""Pydantic schemas and enums for the AI Engine.

Defines domain contracts for email classification, triage evaluation,
draft reply generation, and Ollama integration.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmailCategory(StrEnum):
    """Categorization labels for incoming emails."""

    WORK = "work"
    FINANCE = "finance"
    PERSONAL = "personal"
    NEWSLETTERS = "newsletters"
    PROMOTIONS = "promotions"
    ALERTS = "alerts"
    OTHER = "other"


class DraftTone(StrEnum):
    """Tone options for AI-assisted draft reply generation."""

    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CONCISE = "concise"
    WARM = "warm"


class TriageEmailInput(BaseModel):
    """Input payload to analyze and classify an incoming email."""

    model_config = ConfigDict(extra="ignore")

    subject: str = Field(..., min_length=1, max_length=1000, description="Email subject line")
    sender: str = Field(..., min_length=1, max_length=500, description="Sender name or email address")
    recipient: str = Field(default="", max_length=500, description="Recipient email address")
    date: str = Field(default="", max_length=100, description="Email date header")
    body: str = Field(..., min_length=1, description="Sanitized email body text")
    thread_history: list[str] = Field(default_factory=list, description="Prior messages in thread")


class EmailTriageResult(BaseModel):
    """Structured output returned by email classification."""

    model_config = ConfigDict(extra="ignore")

    category: EmailCategory = Field(..., description="High-level email classification category")
    importance: int = Field(
        ...,
        ge=1,
        le=5,
        description="Importance score from 1 (lowest/spam/promo) to 5 (urgent/critical)",
    )
    needs_reply: bool = Field(
        ...,
        description="True if the message expects or warrants an explicit response",
    )
    summary: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Concise 1-2 sentence executive summary of the email",
    )
    suggested_action: str = Field(
        default="review",
        description="Suggested triage action: reply, archive, review, flag_urgent",
    )
    reasoning_short: str = Field(
        default="",
        description="Brief justification for the assigned category and importance",
    )
    model_used: str = Field(default="", description="The specific LLM that produced this result")
    latency_ms: float = Field(default=0.0, description="Inference time in milliseconds")


class GenerateDraftInput(BaseModel):
    """Input parameters for generating an email draft reply."""

    model_config = ConfigDict(extra="ignore")

    email_subject: str = Field(..., min_length=1, max_length=1000, description="Original email subject")
    email_sender: str = Field(..., min_length=1, max_length=500, description="Original sender")
    email_body: str = Field(..., min_length=1, description="Original email content")
    user_instructions: str = Field(
        default="",
        max_length=1000,
        description="Optional human steering guidance (e.g. 'Accept meeting for Thursday')",
    )
    tone: DraftTone = Field(default=DraftTone.PROFESSIONAL, description="Tone style for the draft")
    sender_name: str = Field(default="", max_length=100, description="Name of the user sending the reply")
    thread_history: list[str] = Field(default_factory=list, description="Prior thread context")


class DraftReplyResult(BaseModel):
    """Generated reply draft produced by the AI Engine."""

    model_config = ConfigDict(extra="ignore")

    subject: str = Field(..., description="Subject line for the reply")
    body: str = Field(..., description="Full text body for the suggested reply")
    tone: str = Field(default="professional", description="Applied tone style")
    model_used: str = Field(default="", description="Model used to generate draft")
    latency_ms: float = Field(default=0.0, description="Inference latency in milliseconds")


class OllamaModelInfo(BaseModel):
    """Summary information for an Ollama model installed locally."""

    name: str
    size_bytes: int = 0
    size_formatted: str = ""
    modified_at: str = ""


class AIHealthResponse(BaseModel):
    """System health and connectivity status for the AI subsystem."""

    provider: str
    status: str
    base_url: str
    classifier_model: str
    drafter_model: str
    available_models: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
