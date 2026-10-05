"""Domain exceptions and FastAPI exception handlers.

All domain errors inherit from MailAgentError and carry a machine-readable
`code` field. Exception handlers convert these into RFC 7807-style
Problem Detail JSON responses.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class MailAgentError(Exception):
    """Base exception for all domain errors.

    Every domain exception carries a machine-readable `code` for clients
    and a human-readable `detail` for debugging.
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = 500

    def __init__(self, detail: str = "An unexpected error occurred", **kwargs: Any) -> None:
        self.detail = detail
        self.extra = kwargs
        super().__init__(detail)


class NotFoundError(MailAgentError):
    """Raised when a requested resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404

    def __init__(self, entity: str = "Resource", entity_id: str = "") -> None:
        detail = f"{entity} not found"
        if entity_id:
            detail = f"{entity} '{entity_id}' not found"
        super().__init__(detail=detail, entity=entity, entity_id=entity_id)


class ConflictError(MailAgentError):
    """Raised when an operation conflicts with the current state."""

    code = "CONFLICT"
    status_code = 409


class ValidationError(MailAgentError):
    """Raised when domain-level validation fails (not HTTP input validation)."""

    code = "VALIDATION_ERROR"
    status_code = 422


class AuthenticationError(MailAgentError):
    """Raised when authentication fails or a session is invalid."""

    code = "AUTHENTICATION_ERROR"
    status_code = 401


class AuthorizationError(MailAgentError):
    """Raised when the user lacks permission for the requested action."""

    code = "AUTHORIZATION_ERROR"
    status_code = 403


class RateLimitError(MailAgentError):
    """Raised when a rate limit is exceeded."""

    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429


class ExternalServiceError(MailAgentError):
    """Raised when an external service (Gmail, Anthropic) call fails."""

    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502


class InvalidStateTransitionError(MailAgentError):
    """Raised when a state-machine transition is illegal.

    Used by the draft approval workflow to enforce valid transitions.
    """

    code = "INVALID_STATE_TRANSITION"
    status_code = 409

    def __init__(self, entity: str, current_state: str, attempted_action: str) -> None:
        detail = f"Cannot perform '{attempted_action}' on {entity} in state '{current_state}'"
        super().__init__(
            detail=detail,
            current_state=current_state,
            attempted_action=attempted_action,
        )


class ContentTamperError(MailAgentError):
    """Raised when content hash verification fails before sending.

    This is a critical safety error: the approved content has been
    modified since approval.
    """

    code = "CONTENT_TAMPER_DETECTED"
    status_code = 409


def _build_problem_detail(
    status: int,
    code: str,
    detail: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an RFC 7807 Problem Detail response body.

    Args:
        status: HTTP status code.
        code: Machine-readable error code.
        detail: Human-readable description.
        extra: Additional context (never includes sensitive data).

    Returns:
        A dictionary suitable for JSON serialization.
    """
    body: dict[str, Any] = {
        "type": f"urn:mailagent:error:{code.lower()}",
        "status": status,
        "code": code,
        "detail": detail,
    }
    if extra:
        # Only include safe, non-sensitive extra fields
        safe_keys = {"entity", "entity_id", "current_state", "attempted_action"}
        body["extra"] = {k: v for k, v in extra.items() if k in safe_keys}
    return body


async def mailagent_error_handler(request: Request, exc: MailAgentError) -> JSONResponse:
    """Handle all MailAgentError subclasses with consistent RFC 7807 responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_problem_detail(
            status=exc.status_code,
            code=exc.code,
            detail=exc.detail,
            extra=exc.extra if exc.extra else None,
        ),
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors without leaking internal details.

    In production, returns a generic error message. In development,
    includes the exception type for debugging.
    """
    from mailagent.core.logging import get_logger

    logger = get_logger(__name__)
    logger.exception("unhandled_exception", exc_type=type(exc).__name__)

    return JSONResponse(
        status_code=500,
        content=_build_problem_detail(
            status=500,
            code="INTERNAL_ERROR",
            detail="An unexpected error occurred",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application.

    Called during app factory initialization to ensure consistent
    error responses across all endpoints.
    """
    app.add_exception_handler(MailAgentError, mailagent_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
