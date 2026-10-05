"""HTTP middleware for request ID propagation, security headers, and rate limiting.

Each middleware is implemented as a pure ASGI middleware or a Starlette
BaseHTTPMiddleware for clarity. The request ID is stored in structlog
context vars for automatic inclusion in all log entries.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, ClassVar

import structlog
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp, Receive, Scope, Send

from mailagent.core.logging import get_logger

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request for log correlation.

    If the client sends an X-Request-ID header, it is used (after validation).
    Otherwise, a new UUID is generated. The ID is bound to structlog
    context vars and returned in the response headers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process the request, injecting a request ID."""
        request_id = request.headers.get("x-request-id", "")
        if not request_id or len(request_id) > 64:
            request_id = str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start_time) * 1000, 2)

        response.headers["X-Request-ID"] = request_id

        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response


class SecurityHeadersMiddleware:
    """Adds security headers to every response.

    Headers follow OWASP recommendations for defense-in-depth:
    - Content-Security-Policy restricts resource loading
    - HSTS enforces HTTPS
    - X-Content-Type-Options prevents MIME sniffing
    - X-Frame-Options prevents clickjacking
    - Referrer-Policy limits referrer leakage
    """

    SECURITY_HEADERS: ClassVar[dict[str, str]] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "0",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        ),
    }

    def __init__(self, app: ASGIApp, enable_hsts: bool = False) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            enable_hsts: Whether to add HSTS header (enable only behind TLS).
        """
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the ASGI request and inject security headers."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                raw_headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                for key, value in self.SECURITY_HEADERS.items():
                    raw_headers.append((key.lower().encode(), value.encode()))
                if self.enable_hsts:
                    raw_headers.append(
                        (b"strict-transport-security", b"max-age=63072000; includeSubDomains")
                    )
                message["headers"] = raw_headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


def register_middleware(app: FastAPI, *, enable_hsts: bool = False) -> None:
    """Register all middleware on the FastAPI application.

    Middleware is added in reverse order because Starlette processes
    middleware as a stack (last added = first executed).

    Args:
        app: The FastAPI application instance.
        enable_hsts: Whether to enable HSTS headers.
    """
    # Security headers (outermost — runs first)
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts)

    # Request ID (runs after security headers)
    app.add_middleware(RequestIdMiddleware)
