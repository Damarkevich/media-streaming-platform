# Delivery Worker for Movies Platform

Delivery worker service for the media streaming platform.
The worker consumes notification topics from Kafka, resolves recipient data, renders templates, sends emails via Brevo, and writes delivery results.

## 🎯 Overview

This worker is responsible for:

- consuming campaign fanout messages from `notifications.delivery`;
- consuming review-like events from `notifications.events.review_liked`;
- applying per-author throttle for review-like notifications;
- rendering template subject/body using Jinja2;
- sending emails through Brevo transactional API;
- writing delivery audit records to `notif.deliveries`.

### Key Features

- Fully asynchronous Kafka consumers (`aiokafka`)
- Email sending via `brevo-python`
- Redis-based throttle for review-liked notifications
- Idempotency check by `idempotency_key`
- Delivery persistence in PostgreSQL

## 📚 Logic Description

### Runtime Model

The process starts two consumers concurrently:

1. `notifications.delivery` consumer for campaign fanout messages
2. `notifications.events.review_liked` consumer for event-triggered notifications

### Delivery Flow (`notifications.delivery`)

1. Read message from Kafka.
2. Skip if `idempotency_key` already exists in `notif.deliveries`.
3. Load template from `notif.templates`.
4. Fetch recipient profile from auth internal API.
5. Render subject/body with Jinja2 variables.
6. Send email via Brevo.
7. Persist delivery result (`SENT` or `FAILED`).

### Review-liked Flow (`notifications.events.review_liked`)

1. Read event payload (`review_id`, `review_author_id`, `liker_user_id`).
2. Check Redis throttle key `notif:review_liked:{review_author_id}`.
3. If throttled: persist `THROTTLED` and stop.
4. If not throttled: fetch template `review_liked`, fetch author profile, send email.
5. On success: set throttle key with TTL (default 86400 sec).
6. Persist delivery result (`SENT` or `FAILED`).

## 🛠 Tech Stack

Core:

- Python 3.12+
- aiokafka
- orjson

Integrations:

- Brevo (`brevo-python`)
- Redis (`redis[hiredis]`)
- PostgreSQL (`SQLAlchemy asyncio`, `asyncpg`)
- Auth internal API (`httpx`)
- Jinja2 template rendering

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- uv
- Kafka
- PostgreSQL
- Redis
- Auth service
- Notifications DB schema migrated (`notif.*`)

### Installation

```bash
cd delivery-worker
uv sync
```

### Run the worker

```bash
uv run python -m src.main
```

### Docker

```bash
docker build -t movies-delivery-worker ./delivery-worker
```

## 🔧 Configuration

Main settings are loaded from environment variables or `.env`.

Required:

- `POSTGRES_PASSWORD`
- `BREVO_API_KEY`

Important optional settings:

- `KAFKA_BOOTSTRAP_SERVERS` (default `kafka-0:9092,kafka-1:9092,kafka-2:9092`)
- `KAFKA_CONSUMER_GROUP` (default `delivery-worker`)
- `POSTGRES_DB` (default `movies_database`)
- `POSTGRES_USER` (default `app`)
- `SQL_HOST` (default `movies-db`)
- `SQL_PORT` (default `5432`)
- `REDIS_HOST` (default `movies-redis`)
- `REDIS_PORT` (default `6379`)
- `REVIEW_LIKED_THROTTLE_TTL` (default `86400`)
- `AUTH_INTERNAL_URL` (default `http://movies-auth:8000`)
- `INTERNAL_API_KEY`
- `BREVO_SENDER_EMAIL` (default `noreply@movies-platform.com`)
- `BREVO_SENDER_NAME` (default `Movies Platform`)

## ✅ Testing

Automated tests are not added yet for this worker.

Recommended next step:

```bash
cd delivery-worker
uv run pytest -q
```

after adding a `tests/` package.

## 🏗 Project Structure

```
delivery-worker/
├── src/
│   ├── consumers/
│   │   ├── delivery.py
│   │   └── review_liked.py
│   ├── core/
│   │   ├── config.py
│   │   └── db.py
│   ├── services/
│   │   ├── auth_client.py
│   │   ├── delivery_record.py
│   │   ├── email.py
│   │   ├── template_renderer.py
│   │   └── throttle.py
│   └── main.py
├── Dockerfile
└── pyproject.toml
```
