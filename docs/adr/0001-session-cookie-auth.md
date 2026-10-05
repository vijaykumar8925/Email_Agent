# ADR 0001: HttpOnly Session Cookie Authentication & Same-Origin API Proxy

## Status
Accepted

## Context
The application needs secure user authentication for interacting with Gmail inboxes. We need to prevent:
1. Cross-Site Scripting (XSS) token exfiltration.
2. Cross-Site Request Forgery (CSRF).
3. Leakage of raw Google OAuth credentials to the client browser.

## Decision
1. **HttpOnly, Secure, SameSite=Lax Session Cookies**: The browser never holds Gmail access tokens or refresh tokens. After Google OAuth code exchange, the server issues a signed session cookie.
2. **Signed Session Tokens**: Session tokens are cryptographically signed using `itsdangerous.URLSafeTimedSerializer` with the application secret key and a configured expiration time.
3. **Same-Origin Reverse Proxy**: Next.js App Router proxies `/api/*` requests to the FastAPI backend service. This eliminates CORS complexities, ensures cookies are first-party (`same-origin`), and provides unified routing.
4. **CSRF Protection**: State-changing requests (POST, PATCH, DELETE) require an `X-Requested-With` or `X-CSRF-Token` header, and origin checks against allowed domains.

## Consequences
- Tokens cannot be stolen via JavaScript XSS.
- Frontend code remains clean and simple, interacting with `/api/v1` as local endpoints.
- Cookie expiration is automatically validated on each backend request.
