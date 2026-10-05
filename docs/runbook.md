# Mail Agent: Operations Runbook

## 1. Quick Start

### 1.1 Local Development
Prerequisites: Docker, Docker Compose, Python 3.12 with `uv`, Node.js 20+.

```bash
# Copy example configuration
cp .env.example .env

# Generate encryption keys and app secret:
# In python:
# >>> from cryptography.fernet import Fernet
# >>> Fernet.generate_key().decode()
# >>> import secrets; secrets.token_hex(32)

# Start all backing services (Postgres, Redis):
docker compose up -d postgres redis

# Run database migrations:
cd apps/api && uv run alembic upgrade head

# Run API dev server:
uv run uvicorn mailagent.main:app --reload --port 8000

# Run Web dev server:
cd ../web && npm run dev
```

### 1.2 Running Tests & Quality Gates
```bash
# Backend (apps/api):
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/unit/ -v

# Frontend (apps/web):
npm run lint
npm run format:check
npm run typecheck
npm run build
```

## 2. Token Vault & Key Rotation
When rotating Fernet encryption keys:
1. Generate a new Fernet key.
2. Prepend the new key to `TOKEN_ENCRYPTION_KEYS` (comma-separated):
   `TOKEN_ENCRYPTION_KEYS=new_key,old_key_1,old_key_2`
3. MultiFernet encrypts new tokens using the first key while successfully decrypting older tokens using subsequent keys.
4. Run the re-encryption maintenance script once all records are updated to remove deprecated keys.

## 3. Incident Response

### 3.1 Google OAuth Token Expiry / Invalidation
- **Symptom**: Gmail sync jobs fail with `invalid_grant` error.
- **Remediation**: The system automatically flags mailbox status as `needs_reauth`. The user will see a banner in the Web UI directing them to reconnect their Gmail account.

### 3.2 Pub/Sub Push Webhook Failures
- **Symptom**: Sync delay increases or Pub/Sub drops notifications.
- **Remediation**: The system runs a periodic reconciliation job (every 15 minutes by default) that fetches messages via `history_id` even if push notifications fail.
