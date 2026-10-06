"""Authentication router exposing Google OAuth 2.0 endpoints, sessions, and dev login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from mailagent.auth.schemas import AuthStatusResponse, UserResponse
from mailagent.auth.service import AuthService
from mailagent.core.config import Settings
from mailagent.core.deps import (
    get_auth_service,
    get_current_user,
    get_optional_current_user,
    get_settings_dep,
)
from mailagent.core.errors import AuthorizationError
from mailagent.core.logging import get_logger
from mailagent.users.models import User

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

OAUTH_STATE_COOKIE = "mailagent_oauth_state"


@router.get("/google/login", summary="Initiate Google OAuth 2.0 login flow")
async def google_login(
    request: Request,
    force: bool = Query(default=False, description="Force redirect to Google"),
    settings: Settings = Depends(get_settings_dep),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    """Redirect user to Google OAuth 2.0 consent screen.

    In development, if placeholder credentials are detected and 'force' is not set,
    displays a developer convenience screen offering either one-click dev login
    or proceeding to Google.
    """
    is_placeholder = (
        not settings.google_client_id
        or settings.google_client_id.startswith("your-client-id")
        or not settings.google_client_secret
        or settings.google_client_secret.startswith("your-client-secret")
    )

    if settings.is_development and is_placeholder and not force:
        # Provide interactive developer screen for quick local testing
        html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Mail Agent — Development Login</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      background: #090d16;
      color: #f1f5f9;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 1rem;
    }
    .card {
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 1rem;
      padding: 2rem;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    h1 { font-size: 1.25rem; font-weight: 700; margin-top: 0; color: #fff; }
    p { color: #94a3b8; font-size: 0.875rem; line-height: 1.5; }
    .badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      background: #312e81;
      color: #a5b4fc;
      border-radius: 0.375rem;
      font-size: 0.75rem;
      font-weight: 600;
      margin-bottom: 1rem;
    }
    .btn {
      display: block;
      width: 100%;
      text-align: center;
      padding: 0.75rem 1rem;
      border-radius: 0.5rem;
      font-weight: 600;
      font-size: 0.875rem;
      text-decoration: none;
      cursor: pointer;
      box-sizing: border-box;
      margin-top: 0.75rem;
      transition: all 0.2s;
    }
    .btn-primary {
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      color: #fff;
      border: none;
    }
    .btn-primary:hover { opacity: 0.95; transform: translateY(-1px); }
    .btn-secondary {
      background: #1e293b;
      color: #94a3b8;
      border: 1px solid #334155;
    }
    .btn-secondary:hover { color: #fff; border-color: #475569; }
    .footer { font-size: 0.75rem; color: #64748b; margin-top: 1.5rem; text-align: center; }
    code { background: #020617; padding: 0.15rem 0.35rem; border-radius: 0.25rem; color: #cbd5e1; }
  </style>
</head>
<body>
  <div class="card">
    <span class="badge">DEVELOPMENT ENVIRONMENT</span>
    <h1>Google OAuth Configuration</h1>
    <p>
      Your <code>.env</code> file currently has placeholder Google OAuth credentials
      (<code>GOOGLE_CLIENT_ID</code>).
    </p>
    <p>
      You can sign in immediately with a <strong>mock local test account</strong>
      to explore the full Mail Agent UI, or update <code>.env</code> with real credentials.
    </p>
    <a href="/api/v1/auth/dev/login" class="btn btn-primary">
      ⚡ Continue with Local Dev Account (One-Click)
    </a>
    <a href="/api/v1/auth/google/login?force=true" class="btn btn-secondary">
      Proceed to Google Anyway
    </a>
    <a href="/" class="btn btn-secondary">
      Back to Home
    </a>
    <div class="footer">
      To enable live Gmail sync, set valid OAuth credentials in <code>.env</code>.
    </div>
  </div>
</body>
</html>"""
        return HTMLResponse(content=html)

    auth_url, state = auth_service.create_authorization_url()
    response = RedirectResponse(url=auth_url, status_code=303)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    return response


@router.get("/google/callback", summary="Google OAuth 2.0 callback")
async def google_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    settings: Settings = Depends(get_settings_dep),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    """Handle callback from Google OAuth server with authorization code."""
    frontend_url = (
        settings.app_cors_origins[0] if settings.app_cors_origins else "http://localhost:3000"
    )
    redirect_target = f"{frontend_url.rstrip('/')}/"

    if error:
        logger.warning("google_oauth_error_callback", error=error)
        return RedirectResponse(url=f"{redirect_target}?auth_error={error}", status_code=303)

    if not code or not state:
        logger.warning("google_oauth_missing_parameters")
        return RedirectResponse(
            url=f"{redirect_target}?auth_error=missing_code_or_state", status_code=303
        )

    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)

    try:
        _user, session_token = await auth_service.handle_google_callback(
            code=code,
            state=state,
            expected_state=expected_state,
        )
    except Exception as exc:
        logger.error("google_auth_callback_failed", error=str(exc))
        return RedirectResponse(
            url=f"{redirect_target}?auth_error=authentication_failed", status_code=303
        )

    response = RedirectResponse(url=redirect_target, status_code=303)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path="/")
    return response


@router.get("/dev/login", summary="One-click development login")
async def dev_login(
    email: str = Query(default="demo.user@gmail.com"),
    name: str = Query(default="Demo User"),
    settings: Settings = Depends(get_settings_dep),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    """Sign in as a mock test user during local development."""
    if not settings.is_development:
        raise AuthorizationError("Dev login is only available in development mode")

    _user, session_token = await auth_service.handle_dev_login(email=email, display_name=name)

    frontend_url = (
        settings.app_cors_origins[0] if settings.app_cors_origins else "http://localhost:3000"
    )
    response = RedirectResponse(url=f"{frontend_url.rstrip('/')}/", status_code=303)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )
    return response


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user")
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return profile details for the currently authenticated user."""
    return UserResponse.from_user(current_user)


@router.get("/status", response_model=AuthStatusResponse, summary="Get authentication status")
async def get_auth_status(
    optional_user: User | None = Depends(get_optional_current_user),
) -> AuthStatusResponse:
    """Return whether the current request is authenticated and the user details if so."""
    if optional_user is None:
        return AuthStatusResponse(authenticated=False, user=None)
    return AuthStatusResponse(
        authenticated=True,
        user=UserResponse.from_user(optional_user),
    )


@router.post("/logout", summary="Log out and terminate current session")
async def logout(
    settings: Settings = Depends(get_settings_dep),
) -> Response:
    """Clear session cookie and invalidate login."""
    response = JSONResponse(content={"status": "ok", "message": "Successfully logged out"})
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
    )
    return response
