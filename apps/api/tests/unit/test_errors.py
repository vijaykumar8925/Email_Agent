"""Tests for the error handling system and exception handlers."""

from __future__ import annotations

from mailagent.core.errors import (
    ContentTamperError,
    InvalidStateTransitionError,
    MailAgentError,
    NotFoundError,
    _build_problem_detail,
)


class TestDomainExceptions:
    """Tests for domain exception classes."""

    def test_base_error_defaults(self) -> None:
        """MailAgentError has sensible defaults."""
        error = MailAgentError()
        assert error.code == "INTERNAL_ERROR"
        assert error.status_code == 500
        assert "unexpected error" in error.detail

    def test_not_found_error_with_entity(self) -> None:
        """NotFoundError includes entity details."""
        error = NotFoundError(entity="Email", entity_id="abc-123")
        assert error.code == "NOT_FOUND"
        assert error.status_code == 404
        assert "Email" in error.detail
        assert "abc-123" in error.detail

    def test_invalid_state_transition(self) -> None:
        """InvalidStateTransitionError includes state and action."""
        error = InvalidStateTransitionError(
            entity="Draft",
            current_state="DRAFTED",
            attempted_action="send",
        )
        assert error.code == "INVALID_STATE_TRANSITION"
        assert "DRAFTED" in error.detail
        assert "send" in error.detail

    def test_content_tamper_error(self) -> None:
        """ContentTamperError signals content modification after approval."""
        error = ContentTamperError(detail="Content hash mismatch")
        assert error.code == "CONTENT_TAMPER_DETECTED"
        assert error.status_code == 409


class TestProblemDetail:
    """Tests for RFC 7807 Problem Detail response building."""

    def test_basic_problem_detail(self) -> None:
        """Problem detail includes required fields."""
        body = _build_problem_detail(404, "NOT_FOUND", "Email not found")
        assert body["status"] == 404
        assert body["code"] == "NOT_FOUND"
        assert body["detail"] == "Email not found"
        assert body["type"] == "urn:mailagent:error:not_found"

    def test_problem_detail_filters_extra_keys(self) -> None:
        """Only safe keys appear in the extra field."""
        body = _build_problem_detail(
            409,
            "INVALID_STATE_TRANSITION",
            "Bad transition",
            extra={
                "current_state": "DRAFTED",
                "attempted_action": "send",
                "secret_data": "should-not-appear",
            },
        )
        assert "current_state" in body["extra"]
        assert "attempted_action" in body["extra"]
        assert "secret_data" not in body["extra"]

    def test_problem_detail_no_extra(self) -> None:
        """Problem detail works without extra fields."""
        body = _build_problem_detail(500, "INTERNAL_ERROR", "Something broke")
        assert "extra" not in body
