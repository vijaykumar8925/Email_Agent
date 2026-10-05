# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# Mail Agent API — multi-stage production build
# ---------------------------------------------------------------------------

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

COPY README.md ./
COPY src/ src/
RUN uv sync --frozen --no-dev

# Stage 2: Production image
FROM python:3.12-slim AS runtime

# Security: create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/src /app/src
COPY alembic.ini ./

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/healthz')"

CMD ["uvicorn", "mailagent.main:app", "--host", "0.0.0.0", "--port", "8000"]
