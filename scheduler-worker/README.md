# Scheduler Worker for Movies Platform

Scheduler worker service for the media streaming platform.
The worker runs cron-based notification jobs (currently weekly digest) and publishes delivery tasks to Kafka.

## 🎯 Overview

This worker is responsible for:

- loading weekly digest cron from PostgreSQL (`notif.jobs`);
- scheduling job execution via APScheduler;
- fetching top films from async API;
- fetching all users from auth internal API;
- publishing delivery tasks to `notifications.delivery`.

### Key Features

- Async scheduler runtime with `AsyncIOScheduler`
- Dynamic cron loading from DB with fallback value
- Async integrations (`httpx`, `aiokafka`, async SQLAlchemy)
- Per-user idempotency keys for weekly digest messages

## 📚 Logic Description

### Runtime Flow

1. Worker starts and loads cron expression for job `weekly_digest` from `notif.jobs`.
2. If DB lookup fails, fallback to `WEEKLY_DIGEST_CRON` (`0 9 * * 5`).
3. APScheduler registers `run_weekly_digest` job with the loaded trigger.
4. On trigger:
   - load `template_id` from `notif.jobs`;
   - fetch top N films from async API (`/api/v1/films`);
   - fetch all user IDs from auth internal API;
   - publish one Kafka message per user to `notifications.delivery`;
   - update `last_run_at` in `notif.jobs`.

## 🛠 Tech Stack

Core:

- Python 3.12+
- APScheduler
- aiokafka
- orjson

Integrations:

- PostgreSQL (`SQLAlchemy asyncio`, `asyncpg`)
- Async API (`httpx`)
- Auth internal API (`httpx`)

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- uv
- Kafka
- PostgreSQL
- Async API service
- Auth service

### Installation

```bash
cd scheduler-worker
uv sync
```

Install test dependencies:

```bash
uv sync --group dev
```

### Run the worker

```bash
uv run python -m src.main
```

### Docker

```bash
docker build -t movies-scheduler-worker ./scheduler-worker
```

## 🔧 Configuration

Main settings are loaded from environment variables or `.env`.

Required:

- `POSTGRES_PASSWORD`

Important optional settings:

- `KAFKA_BOOTSTRAP_SERVERS` (default `kafka-0:9092,kafka-1:9092,kafka-2:9092`)
- `POSTGRES_DB` (default `movies_database`)
- `POSTGRES_USER` (default `app`)
- `SQL_HOST` (default `movies-db`)
- `SQL_PORT` (default `5432`)
- `AUTH_INTERNAL_URL` (default `http://movies-auth:8000`)
- `INTERNAL_API_KEY`
- `ASYNC_API_URL` (default `http://movies-async-api:8000`)
- `WEEKLY_DIGEST_TOP_N` (default `10`)
- `WEEKLY_DIGEST_CRON` (default `0 9 * * 5`)

## ✅ Testing

```bash
cd scheduler-worker
uv run pytest tests -v
```

Current coverage includes:

- API client behavior (`get_top_films`, `get_all_user_ids`)
- weekly digest job execution flow
- cron loading fallback behavior

## 🏗 Project Structure

```
scheduler-worker/
├── src/
│   ├── core/
│   │   ├── config.py
│   │   └── db.py
│   ├── jobs/
│   │   └── weekly_digest.py
│   ├── services/
│   │   └── api_clients.py
│   └── main.py
├── tests/
├── Dockerfile
└── pyproject.toml
```
