# ADR 0002: Async Job Queue with ARQ and Redis

## Status
Accepted

## Context
Mail Agent performs asynchronous, I/O-heavy operations:
- Fetching and parsing Gmail messages via Google API.
- LLM inference calls to Anthropic for email classification and drafting.
- Token refresh and mailbox watch renewals.
- Periodic inbox reconciliation.

We considered Celery vs. ARQ.

## Decision
We chose **ARQ** over Celery:
1. **Native Asyncio**: ARQ runs directly on Python's `asyncio` event loop. All database calls (`asyncpg` + SQLAlchemy 2.0 async) and HTTP requests (`httpx`) execute natively without thread pools or blocking event loops.
2. **Lightweight & High Performance**: Backed by Redis 7, ARQ avoids the heavy complexity, broker configurations, and serialization overhead of Celery.
3. **Structured Context**: ARQ passes shared lifespan objects (e.g. database sessions, Redis clients, HTTP sessions) cleanly via its worker context `ctx`.
4. **Retry & Backoff**: Supports exponential retry with jitter out of the box.

## Consequences
- Single cohesive async ecosystem across FastAPI and background workers.
- Requires all worker tasks to be written with non-blocking async primitives. Blocking calls (e.g., standard Google API clients) must be dispatched to `asyncio.to_thread` or thread pools.
