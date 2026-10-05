# Security Policy — Mail Agent

## Threat Model

Mail Agent handles sensitive data (Gmail tokens, email content, user sessions) and interfaces with external APIs (Google, Anthropic). The following threats are explicitly considered:

### 1. Token Theft

**Threat**: An attacker gains access to stored Gmail refresh tokens, enabling full mailbox access.

**Mitigations**:
- Refresh tokens are encrypted at rest using `MultiFernet` (AES-128-CBC via Fernet) with support for key rotation.
- Encryption keys are loaded from environment variables, never stored in the database or code.
- Access tokens are held only in memory or short-lived Redis cache; they are never persisted to disk.
- The `token_key_version` column enables key rotation without re-encrypting all tokens at once.
- Database access requires authentication; connection strings use strong credentials.
- The application runs as a non-root user in production containers.

### 2. Prompt Injection

**Threat**: A malicious email contains instructions that manipulate the AI model into performing unintended actions.

**Mitigations**:
- Email content is placed inside clearly delimited blocks labeled as "UNTRUSTED USER DATA" in all prompts.
- System prompts explicitly instruct the model to never follow instructions found within untrusted data blocks.
- The AI layer has **no tools** that can act on the mailbox—it produces text output only.
- Input sanitization strips hidden HTML, zero-width characters, and excessively long content before sending to the model.
- All AI outputs are validated against strict Pydantic schemas before being used.
- Model output is never rendered as HTML or executed as code.
- Token usage and input lengths are logged (without logging content) to detect anomalous behavior.

### 3. Unauthorized Send

**Threat**: A bug, race condition, or compromised component sends an email without the user's explicit approval.

**Mitigations**:
- The draft state machine enforces a strict lifecycle: `DRAFTED → APPROVED → SENDING → SENT`.
- Approval records the approver's user ID, timestamp, and a SHA-256 hash of the approved content.
- Before sending, the system re-verifies that the current content hash matches the `approved_content_sha256`. Any mismatch aborts the send.
- Sending uses `SELECT ... FOR UPDATE` on the draft row plus a unique `send_idempotency_key` to prevent double sends.
- The AI layer has no import path to the send function—enforced by module boundaries.
- All send operations are recorded in an append-only audit log.
- The send endpoint has its own rate limit.

### 4. Data Leakage

**Threat**: Email content or tokens are exposed via logs, error messages, API responses, or the AI provider.

**Mitigations**:
- Structured logging (structlog) is configured to redact sensitive fields. Email bodies and tokens are never logged at INFO level or above.
- Error responses follow RFC 7807 format and never include stack traces or internal details in production.
- API responses include only the data relevant to the request; no over-fetching of sensitive fields.
- `body_text` retention is configurable; a scheduled job purges email bodies after the configured TTL.
- A "delete all my data" endpoint revokes Google tokens and removes all user data.
- Anthropic API calls use HTTPS only; content sent to the AI is the minimum needed for the task.

### 5. Session Hijacking / CSRF

**Threat**: An attacker steals or forges a session to act on behalf of a user.

**Mitigations**:
- Sessions use `httpOnly`, `Secure`, `SameSite=Lax` cookies. No tokens are stored in localStorage or JavaScript-accessible storage.
- CSRF protection uses a double-submit pattern: state-changing requests require a custom header that the browser will not send in cross-origin requests.
- Session IDs are cryptographically random and rotated on login.
- Sessions have a configurable maximum age (default: 24 hours).
- OAuth flows use PKCE and `state` validation to prevent authorization code injection.

### 6. Infrastructure Attacks

**Threat**: Attacks on the application's infrastructure (containers, databases, network).

**Mitigations**:
- Docker containers run as non-root users with minimal base images.
- Security headers are set on all responses: CSP, HSTS, X-Content-Type-Options, X-Frame-Options.
- Database connections use parameterized queries exclusively—no string interpolation.
- Dependencies are audited in CI (`pip-audit`, `npm audit`) and monitored by Dependabot.
- Rate limiting is applied to authentication, AI, and send endpoints.

## Supported Versions

Only the latest version on the `main` branch is supported with security updates.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public issue.
2. Email the maintainers at `security@example.com` with a description of the vulnerability.
3. Include steps to reproduce, if possible.
4. We will acknowledge receipt within 48 hours and provide an estimated fix timeline.

## Security Checklist

- [ ] All environment variables are set and validated at startup
- [ ] Token encryption keys are rotated periodically
- [ ] OAuth scopes are minimal (`gmail.readonly`, `gmail.send`)
- [ ] Dependencies are up to date and audited
- [ ] Rate limits are configured for production load
- [ ] Logs do not contain sensitive data
- [ ] Backup and disaster recovery procedures are documented
