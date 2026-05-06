# Notifications Service for Movies Platform

Notifications API service for the media streaming platform.
The service is built with FastAPI and provides template management, campaign management, and campaign fanout to Kafka.

## 🎯 Overview

This service is responsible for:

- storing notification templates;
- creating and managing campaigns;
- triggering campaign fanout to Kafka;
- exposing internal health status for orchestration.

### Key Features

- Asynchronous API with FastAPI
- PostgreSQL persistence (`notif` schema)
- Alembic migrations with initial seed data
- JWT-based admin protection for management endpoints
- Background fanout task for campaign send
- Kafka publishing to `notifications.delivery`

## 📚 Logic Description

### Architecture

```
┌─────────────────┐
│   API Layer     │  FastAPI routers and schemas
├─────────────────┤
│ Service Layer   │  Templates/campaigns business logic
├─────────────────┤
│   DB Layer      │  PostgreSQL (`notif` schema)
└─────────────────┘
```

### Management Flow

1. Admin creates or updates templates.
2. Admin creates a campaign based on a template.
3. Admin calls `POST /campaigns/{id}/send`.
4. Service marks campaign as `QUEUED`.
5. Background fanout loads all users from auth internal API.
6. Service publishes one Kafka message per user to `notifications.delivery`.

## 📖 API Endpoints

Base path for business endpoints: `/api/v1/notifications`

Health:

- `GET /api/health`

Templates:

- `GET /api/v1/notifications/templates/`
- `POST /api/v1/notifications/templates/`
- `GET /api/v1/notifications/templates/{template_id}`
- `PUT /api/v1/notifications/templates/{template_id}`
- `DELETE /api/v1/notifications/templates/{template_id}`

Campaigns:

- `GET /api/v1/notifications/campaigns/`
- `POST /api/v1/notifications/campaigns/`
- `GET /api/v1/notifications/campaigns/{campaign_id}`
- `POST /api/v1/notifications/campaigns/{campaign_id}/send` (returns `202`)

## 🛠 Tech Stack

Core:

- Python 3.12+
- FastAPI
- Pydantic v2
- Uvicorn

Storage and infra:

- PostgreSQL (`SQLAlchemy asyncio`, `asyncpg`)
- Alembic
- Kafka (`aiokafka` for fanout publish)

Integration:

- Auth internal API (`/api/v1/users/internal`)
- JWT auth via `async-fastapi-jwt-auth`

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- uv
- PostgreSQL
- Kafka
- Auth service

### Installation

```bash
cd notifications
uv sync
```

Install test dependencies:

```bash
uv sync --group test
```

### Run migrations

```bash
uv run alembic upgrade head
```

### Run the service

Development:

```bash
uv run fastapi dev src/main.py
```

Production-like:

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Docs and OpenAPI:

- Docs UI: `http://localhost:8000/api/notifications/docs`
- OpenAPI JSON: `http://localhost:8000/api/notifications/openapi.json`

## 🔧 Configuration

Main settings are loaded from environment variables or `.env`.

Required:

- `AUTHJWT_SECRET_KEY`
- `POSTGRES_PASSWORD`

Important optional settings:

- `DEVELOPMENT_MODE` (default `false`)
- `SQL_HOST` (default `localhost`)
- `SQL_PORT` (default `5432`)
- `POSTGRES_DB` (default `movies_database`)
- `POSTGRES_USER` (default `app`)
- `POSTGRES_DB_SCHEMA` (default `notif`)
- `INTERNAL_API_KEY`
- `AUTH_INTERNAL_URL` (default `http://movies-auth:8000`)
- `KAFKA_BOOTSTRAP_SERVERS` (default `kafka-0:9092,kafka-1:9092,kafka-2:9092`)

## ✅ Testing

```bash
cd notifications
uv run --group test pytest -q
```

## 🏗 Project Structure

```
notifications/
├── alembic/
│   └── versions/
├── src/
│   ├── api/
│   │   ├── health.py
│   │   └── v1/
│   │       ├── templates.py
│   │       └── campaigns.py
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
├── Dockerfile
└── pyproject.toml
```
