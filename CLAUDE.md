# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastAPI-based billing/subscription microservice. Stripe-integrated, multi-currency (39 supported), PostgreSQL + SQLAlchemy 2.0 + Alembic, deployed to AWS ECS Fargate via GitHub Actions.

## Common commands

The `Makefile` is the canonical entry point. Use `make help` to list targets.

- `make dev` — run dev server with reload (`uvicorn app.main:app --reload --port 8000`)
- `make test` — full pytest run (`pytest -v --tb=short`)
- `make test-cov` — pytest with coverage report
- `pytest tests/test_subscriptions.py::test_name -v` — run a single test
- `make lint` — flake8 (`--max-line-length=120`); CI runs the same command and fails the build on violations
- `make migrate` — `alembic upgrade head`
- `make migrate-create msg="..."` — autogenerate a new Alembic revision
- `make seed` — `python -m app.scripts.seed_data` (loads 6 plans + 5 customers)
- `make docker-up` / `make docker-down` — full stack via `docker-compose.yml` (api + postgres)

Tests use an in-memory SQLite DB (see `tests/conftest.py`) and a fully mocked Stripe client — no external services required to run the suite locally. Stripe is mocked at `app.services.stripe_service.stripe`.

Python 3.11 is required (pinned in `pyproject.toml` and CI).

## Authentication

Every `/api/v1/*` route except `/api/v1/webhooks/stripe` requires an `X-API-Key` header. Keys are stored as SHA-256 hashes in the `api_keys` table; the plaintext is shown once at creation time via `python -m app.scripts.create_api_key <name>` and cannot be recovered. The webhook endpoint is authenticated by Stripe's HMAC signature (`construct_webhook_event` in `StripeService`), not by the API key. `/health` at the root is public.

The dependency is `Depends(require_api_key)` from `app/core/security.py` — attach it at the `APIRouter(...)` level for new routers so it covers every endpoint by default.

## Architecture

Three-layer FastAPI app: **endpoints → services → models/db**. Keep new code on this seam — never call Stripe directly from an endpoint; route through a service.

- `app/main.py` — `create_app()` factory. Registers CORS, request-logging middleware, the `BillingException` handler (translates custom exceptions into structured `{"error": {...}}` JSON responses), and mounts `api_router` under `/api/v1`. `/health` lives at the root.
- `app/api/v1/router.py` — aggregates 8 endpoint modules: `customers`, `plans`, `subscriptions`, `invoices`, `payments`, `checkout`, `webhooks`, `currencies`.
- `app/services/` — business logic. `StripeService` is the Stripe abstraction; `SubscriptionService`, `InvoiceService`, `CurrencyService` orchestrate domain operations. Services take a `Session` in `__init__` and instantiate `StripeService()` internally.
- `app/models/` — SQLAlchemy 2.0 models on the shared `Base` from `app/db/base.py`. Use the `UUIDMixin` + `TimestampMixin` mixins for new tables. Primary keys use a custom `GUID` `TypeDecorator` that stores as `CHAR(36)` and works on both PostgreSQL and SQLite (the test backend) — do not switch to `postgresql.UUID` directly without preserving SQLite compatibility, or the tests will break.
- `app/schemas/` — Pydantic v2 request/response models, one module per domain.
- `app/core/config.py` — `Settings` is a `pydantic_settings.BaseSettings` cached via `lru_cache`. `CORS_ORIGINS` is a JSON string parsed by the `cors_origins_list` property.
- `app/core/exceptions.py` — custom `BillingException` hierarchy. Raise these from services; the global handler in `main.py` formats them. Don't raise raw `HTTPException` from services.
- `alembic/versions/` — schema migrations. Always create a migration when changing models; don't rely on `create_all`.

## Stripe & webhooks

Stripe is the system of record for payment state. Local DB rows mirror Stripe objects (customer/product/price/subscription/invoice IDs are stored on the corresponding models). Webhook events arrive at `POST /api/v1/webhooks/stripe` and are verified with `STRIPE_WEBHOOK_SECRET` before being applied to local state. When adding flows that mutate billing state, ensure both the Stripe call and the local DB write happen in `StripeService` / a domain service — don't split them across layers.

## Multi-currency

`CurrencyService` enforces per-currency minimum charges and zero-decimal currency handling (JPY, KRW, etc.). When dealing with amounts, check what unit the boundary expects: Stripe uses smallest currency unit (cents for USD, whole units for JPY); the API accepts decimal amounts and the service layer converts.

## Configuration

All config flows through env vars → `Settings`. Required for any non-test run: `DATABASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`. See `.env.example` for the full list. `APP_ENV=testing` is what CI sets.

## CI/CD

`.github/workflows/ci-cd.yml` runs lint + pytest (against a real Postgres service container) on every push/PR. On push to `master`/`main`, it builds the Docker image, pushes to ECR, and deploys to ECS Fargate (cluster `billing-cluster`, service `billing-api-service`). The deploy step currently has `wait-for-service-stability: false` — see recent commit `de4b83f` (disabled until DB is provisioned).
