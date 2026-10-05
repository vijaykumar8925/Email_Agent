# Mail Agent

An AI-powered email management assistant for Gmail. Categorizes, ranks, and drafts replies—with mandatory human approval before any email is sent.

## Features

- **Smart Inbox**: Automatically categorizes emails (Work, Finance, Personal, etc.) and ranks by importance (1–5)
- **AI Drafts**: Generates context-aware reply drafts using Claude, with optional templates
- **Human-in-the-Loop**: Every draft requires explicit approval before sending—enforced at the domain layer
- **Gmail Integration**: OAuth 2.0, real-time push notifications, history-based sync
- **Audit Trail**: Append-only log of all actions for accountability

## Architecture

```
┌─────────┐     ┌──────────┐     ┌──────────┐
│ Next.js  │────▶│ FastAPI  │────▶│PostgreSQL│
│ Frontend │     │ Backend  │     │  + Redis │
└─────────┘     └──────────┘     └──────────┘
                     │
              ┌──────┴──────┐
              │             │
         ┌────▼───┐  ┌─────▼────┐
         │ Gmail  │  │ Anthropic│
         │  API   │  │   API    │
         └────────┘  └──────────┘
```

See [docs/architecture.md](docs/architecture.md) for the full design.

## Tech Stack

| Layer    | Technology                                                            |
|----------|-----------------------------------------------------------------------|
| Backend  | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Redis, ARQ |
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui            |
| AI       | Anthropic Claude (classification + drafting)                          |
| Email    | Gmail API (OAuth 2.0, push via Pub/Sub)                               |
| Infra    | Docker, docker-compose, GitHub Actions                                |

## Prerequisites

- Python 3.12+ with [uv](https://docs.astral.sh/uv/)
- Node.js 20+ with npm
- Docker and Docker Compose
- A Google Cloud project with Gmail API enabled and OAuth credentials
- An Anthropic API key

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url>
cd mail-agent
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start all services

```bash
make dev
```

This starts PostgreSQL, Redis, the FastAPI backend, the ARQ worker, and the Next.js frontend.

### 3. Run database migrations

```bash
make migrate
```

### 4. Open the app

Visit [http://localhost:3000](http://localhost:3000) and sign in with Google.

## Development

### Available Make targets

| Command             | Description                               |
|---------------------|-------------------------------------------|
| `make dev`          | Start all services for local development  |
| `make lint`         | Run all linters (ruff, eslint, prettier)  |
| `make typecheck`    | Run mypy and tsc                          |
| `make test`         | Run all tests                             |
| `make test-unit`    | Run backend unit tests only               |
| `make test-integ`   | Run backend integration tests             |
| `make test-e2e`     | Run Playwright end-to-end tests           |
| `make migrate`      | Apply database migrations                 |
| `make migrate-down` | Rollback the last migration               |
| `make fmt`          | Auto-format all code                      |
| `make build`        | Build Docker images                       |

### Environment Variables

All environment variables are documented in [`.env.example`](.env.example). The application validates all required variables at startup and fails fast with clear error messages if any are missing or invalid.

### Testing

```bash
# Backend tests (requires running PostgreSQL and Redis via docker-compose)
make test-unit
make test-integ

# Frontend tests
cd apps/web && npm test

# E2E tests
make test-e2e
```

### Code Quality

```bash
# Check everything
make lint && make typecheck && make test

# Auto-fix
make fmt
```

## Project Structure

```
├── apps/
│   ├── api/             # FastAPI backend
│   │   ├── src/mailagent/
│   │   │   ├── core/    # Config, logging, security, errors, middleware
│   │   │   ├── db/      # SQLAlchemy models, migrations
│   │   │   ├── auth/    # Google OAuth, sessions
│   │   │   ├── emails/  # Email models, sync, analysis
│   │   │   ├── ai/      # Anthropic integration, prompts
│   │   │   ├── drafts/  # Draft lifecycle, approval, sending
│   │   │   └── ...
│   │   └── tests/
│   └── web/             # Next.js frontend
│       ├── src/app/     # App Router pages
│       ├── src/features/
│       └── src/components/
├── packages/api-types/  # Generated TypeScript types from OpenAPI
├── docs/                # Architecture docs, ADRs, runbook
└── docker-compose.yml
```

## Security

See [SECURITY.md](SECURITY.md) for the threat model and security architecture.

## License

Proprietary. All rights reserved.
