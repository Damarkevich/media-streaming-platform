# Billing Service (FastAPI)

Standalone billing service extracted from the Django admin application.

## What It Provides

- Stripe customer lazy creation per user;
- payment intent creation with idempotency (`operation_id`);
- payment lookup by owner;
- refund creation with cumulative amount protection;
- webhook ingestion with signature validation and event deduplication;
- isolated PostgreSQL schema (`billing`) and Alembic migrations.

## API Base

- Base: `/api/v1/billing`
- Health: `/api/health`

Endpoints:

- `POST /payments/create`
- `GET /payments/{payment_id}`
- `POST /refunds/create`
- `POST /webhooks/stripe`

## Auth Model

For service-to-service usage this version expects user identity via header:

- `X-User-Id: <uuid>`

Webhook endpoint is public and validated with `Stripe-Signature`.

## Environment

Copy `.env.example` to `.env` and fill values.

Required settings:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `SQL_HOST`
- `SQL_PORT`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

Optional:

- `POSTGRES_DB_SCHEMA` (default: `billing`)
- `DEVELOPMENT_MODE`
- `CORS_ORIGINS`
- `SQL_ECHO`

## Run Locally

```bash
cd billing
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --host 0.0.0.0 --port 8010
```

## Migration Notes

- Alembic configuration is local to this service.
- Initial revision creates schema + billing tables:
  - `billing_profiles`
  - `payments`
  - `refunds`
  - `webhook_events`

## Design Guarantees

- operation-level idempotency for payments and refunds;
- race-safe profile/payment/refund creation with DB locks;
- safe retry behavior after transient Stripe refund API failures;
- no downgrade from terminal success in webhook conflict scenarios.
