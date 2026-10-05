# Mail Agent Backend API

FastAPI-based backend service for Mail Agent, an AI-powered email management assistant for Gmail.

## Tech Stack
- Python 3.12, managed with `uv`
- FastAPI + Pydantic v2 + `pydantic-settings`
- SQLAlchemy 2.0 (async, `asyncpg`) + Alembic
- PostgreSQL 16, Redis 7
- ARQ for background jobs
- `anthropic` Python SDK for LLM calls
- Google API client for Gmail
- `cryptography` MultiFernet token encryption
