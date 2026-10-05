# Mail Agent: Architecture Documentation

## 1. System Overview

Mail Agent is a single-user-per-account email management assistant built for Gmail accounts. It automatically fetches unread emails, analyzes their importance and category using Claude (Anthropic), generates suggested replies, and sends them **only after explicit human approval**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Next.js Web (Port 3000)                       │
│  - App Router, Tailwind CSS, shadcn/ui, TanStack Query                 │
│  - Same-origin API rewrites to FastAPI backend (/api/* -> backend)     │
│  - HttpOnly SameSite=Lax Session Cookie                                │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP + CSRF
┌──────────────────────────────────▼─────────────────────────────────────┐
│                          FastAPI API (Port 8000)                       │
│  - Routers: Auth, Mailboxes, Emails, Drafts, Templates, Webhooks       │
│  - Services: Business logic, state machines, hash verification         │
│  - Repositories: SQLAlchemy 2.0 async SQL queries                      │
│  - Security: MultiFernet token vault, session signing, rate limiting   │
└──────────────┬───────────────────┬───────────────────┬─────────────────┘
               │                   │                   │
               ▼                   ▼                   ▼
      ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
      │  PostgreSQL 16  │ │     Redis 7     │ │  ARQ Background │
      │  Relational DB  │ │  Cache + Queue  │ │     Workers     │
      └─────────────────┘ └─────────────────┘ └────────┬────────┘
                                                       │
                               ┌───────────────────────┴─────────────────┐
                               ▼                                         ▼
                      ┌─────────────────┐                       ┌─────────────────┐
                      │    Gmail API    │                       │  Anthropic API  │
                      │  Sync & Send    │                       │  Classification │
                      └─────────────────┘                       │  & Drafting     │
                                                                └─────────────────┘
```

## 2. Core Architectural Principles

### 2.1 Backend Layering: Router -> Service -> Repository
- **Routers**: HTTP transport only. Validate request bodies with Pydantic, check sessions, serialize responses. Never run SQL queries or handle business decisions.
- **Services**: Business domain logic, transaction boundaries (`async with session.begin()`), state machines, audit log writes. Never touch HTTP request/response objects or status codes.
- **Repositories**: Encapsulate all database operations with parameterized SQLAlchemy 2.0 async statements.

### 2.2 Security & The Human-in-the-Loop Hard Rule
- **Domain-Enforced Approval**: The email drafting state machine requires `APPROVED` state before a draft can transition to `SENDING`.
- **Content Hash Verification**: When a draft is approved, the SHA-256 hash of `subject + "\n\n" + body` is computed and stored (`approved_content_sha256`). When sending, the hash is recomputed and strictly validated against the approved hash. If any tampering occurred, sending is aborted.
- **Idempotency**: Sends require a unique `send_idempotency_key` and row lock (`SELECT ... FOR UPDATE`), preventing double-sends even under rapid repeated requests or worker retries.
- **Zero Send Permissions for AI**: The AI pipeline has no tools or API hooks to send emails, modify labels, or delete messages.
- **MultiFernet Token Vault**: Google refresh tokens are encrypted at rest using `MultiFernet` with versioned keys, enabling seamless key rotation.

## 3. Data Flow

### 3.1 Email Ingestion & Analysis
1. Google Pub/Sub sends push notification on new email activity.
2. `/api/v1/webhooks/gmail/push` validates JWT token and enqueues sync task in ARQ.
3. Worker retrieves incremental changes via `history.list(startHistoryId)`.
4. New unread messages are stored in the database.
5. Worker triggers Anthropic classification job with sanitized email content.
6. Categorization, importance score (1–5), needs-reply flag, and summary are saved.

### 3.2 Reply Drafting & Approval
1. User requests reply draft (optionally selecting a template).
2. Drafter service compiles prompt with email context and user tone guidelines.
3. Draft is created in `DRAFTED` status.
4. User reviews draft in Web UI, can edit subject/body.
5. User clicks "Approve" -> draft transitions to `APPROVED` and content hash is sealed.
6. If user edits draft after approval, status automatically resets to `DRAFTED`.
7. User clicks "Send" -> Send service validates hash, acquires DB lock, builds RFC 5322 MIME message, sends via Gmail API, and transitions to `SENT`.
