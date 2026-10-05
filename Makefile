.PHONY: dev dev-api dev-web dev-infra lint lint-api lint-web typecheck typecheck-api typecheck-web \
       test test-unit test-integ test-e2e fmt fmt-api fmt-web build migrate migrate-down \
       migrate-create audit clean

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

dev: dev-infra dev-api dev-web ## Start all services for local development

dev-infra: ## Start PostgreSQL and Redis
	docker compose up -d postgres redis

dev-api: ## Start the FastAPI backend
	cd apps/api && uv run uvicorn mailagent.main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Start the Next.js frontend
	cd apps/web && npm run dev

dev-worker: ## Start the ARQ worker
	cd apps/api && uv run python -m mailagent.workers.run

# ---------------------------------------------------------------------------
# Linting
# ---------------------------------------------------------------------------

lint: lint-api lint-web ## Run all linters

lint-api: ## Lint the backend
	cd apps/api && uv run ruff check src/ tests/
	cd apps/api && uv run ruff format --check src/ tests/

lint-web: ## Lint the frontend
	cd apps/web && npm run lint
	cd apps/web && npx prettier --check "src/**/*.{ts,tsx,css}"

# ---------------------------------------------------------------------------
# Type Checking
# ---------------------------------------------------------------------------

typecheck: typecheck-api typecheck-web ## Run all type checkers

typecheck-api: ## Type-check the backend
	cd apps/api && uv run mypy src/

typecheck-web: ## Type-check the frontend
	cd apps/web && npx tsc --noEmit

# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

test: test-unit test-integ ## Run all backend tests

test-unit: ## Run backend unit tests
	cd apps/api && uv run pytest tests/unit/ -v --tb=short

test-integ: ## Run backend integration tests (requires running Postgres + Redis)
	cd apps/api && uv run pytest tests/integration/ -v --tb=short

test-e2e: ## Run Playwright end-to-end tests
	cd apps/web && npx playwright test

test-cov: ## Run tests with coverage report
	cd apps/api && uv run pytest tests/ -v --cov=mailagent --cov-report=term-missing --cov-report=html

test-web: ## Run frontend unit tests
	cd apps/web && npm test

# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

fmt: fmt-api fmt-web ## Auto-format all code

fmt-api: ## Format the backend
	cd apps/api && uv run ruff format src/ tests/
	cd apps/api && uv run ruff check --fix src/ tests/

fmt-web: ## Format the frontend
	cd apps/web && npx prettier --write "src/**/*.{ts,tsx,css}"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

migrate: ## Apply all database migrations
	cd apps/api && uv run alembic upgrade head

migrate-down: ## Rollback the last migration
	cd apps/api && uv run alembic downgrade -1

migrate-create: ## Create a new migration (usage: make migrate-create MSG="add users table")
	cd apps/api && uv run alembic revision --autogenerate -m "$(MSG)"

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build: ## Build Docker images
	docker compose build

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

audit: ## Audit dependencies for vulnerabilities
	cd apps/api && uv run pip-audit
	cd apps/web && npm audit

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove caches, build artifacts, and containers
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf apps/api/htmlcov apps/web/.next apps/web/node_modules/.cache

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
