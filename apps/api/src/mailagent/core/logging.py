"""Structured JSON logging with structlog.

Configures structlog for consistent, machine-readable logs with
request-id binding for correlation across log entries.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any, cast

import structlog


def setup_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure structlog and stdlib logging for the application.

    Args:
        log_level: The minimum log level (DEBUG, INFO, WARNING, ERROR).
        json_format: If True, output JSON logs. If False, use console format
            (useful during local development).
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _redact_sensitive_fields,
    ]

    if json_format:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    # Quiet down noisy libraries
    for logger_name in ("uvicorn.access", "httpx", "httpcore", "asyncio"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# Fields that must never appear in logs
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "authorization",
        "cookie",
        "body_text",
        "email_body",
        "prompt",
    }
)


def _redact_sensitive_fields(
    logger: Any,
    method: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Redact sensitive fields from log output to prevent data leakage.

    Scans all keys in the event dict and replaces values of sensitive
    fields with '[REDACTED]'. This is a defense-in-depth measure—code
    should avoid logging sensitive data in the first place.
    """
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
    return event_dict


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a bound structlog logger with an optional name.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        A bound logger instance with request context automatically merged.
    """
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
