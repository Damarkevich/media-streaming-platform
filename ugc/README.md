# UGC Service for Movies Platform

User-Generated Content service for the media streaming platform.
The service is built with FastAPI and provides bookmarks, movie/review ratings, and text reviews.

## 🎯 Overview

This service is responsible for:

- bookmarks for movies;
- one review per user per movie;
- movie ratings and review ratings;
- retrieving per-user ratings;
- listing reviews with pagination and sorting.

### Key Features

- Asynchronous API with FastAPI
- MongoDB as the primary storage
- Redis usage for JWT access-token denylist checks
- Role-based access guard for UGC endpoints
- Request-ID middleware for traceability in non-development mode
- OpenAPI docs for UGC routes

## 📚 Logic Description

### Architecture

```
┌─────────────────┐
│   API Layer     │  FastAPI routers and schemas
├─────────────────┤
│ Service Layer   │  Business logic for bookmarks/reviews/ratings
├─────────────────┤
│   DB Layer      │  MongoDB collections + Redis denylist checks
└─────────────────┘
```

### Authentication and Access

All `/api/v1/*` UGC endpoints require a Bearer access token.

Validation flow:

1. Decode JWT with shared `AUTHJWT_SECRET_KEY`
2. Ensure token type is `access`
3. Ensure access token `jti` is not in Redis denylist
4. Ensure user has at least one allowed role (`subscriber` or `admin`)

### Request-ID Middleware

In non-development mode, every request must include `X-Request-Id` header.
If missing, the service returns `400`.

When `DEVELOPMENT_MODE=true`, this requirement is bypassed.

### Data Model Notes

Collections:

- `bookmarks`
- `reviews`
- `ratings`

Rules:

- One bookmark per `(user_id, movie_id)`
- One review per `(user_id, movie_id)`
- One rating per `(user_id, target_type, target_id)`
- Rating values are fixed: `10` (like) or `0` (dislike)

Aggregates are calculated on read (MVP):

- movie rating stats (`rating_avg`, `rating_count`) are computed from `ratings`
- review rating stats are computed from `ratings` and attached in review responses

## 📖 API Endpoints

Base path for business endpoints: `/api/v1`

Health:

- `GET /api/health`

Bookmarks:

- `PUT /api/v1/movies/{movie_id}/bookmark`
- `DELETE /api/v1/movies/{movie_id}/bookmark`
- `GET /api/v1/bookmarks?page_size=&page_number=`

Reviews:

- `PUT /api/v1/movies/{movie_id}/review`
- `DELETE /api/v1/movies/{movie_id}/review`
- `GET /api/v1/movies/{movie_id}/review/my`
- `GET /api/v1/movies/{movie_id}/reviews?sort=&page_size=&page_number=`
- `GET /api/v1/reviews/{review_id}`

Allowed `sort` values for reviews list:

- `-created_at`
- `created_at`
- `-rating_avg`
- `rating_avg`

Ratings:

- `PUT /api/v1/movies/{movie_id}/rating`
- `DELETE /api/v1/movies/{movie_id}/rating`
- `GET /api/v1/movies/{movie_id}/rating` (aggregated stats)
- `GET /api/v1/movies/{movie_id}/rating/my`
- `PUT /api/v1/reviews/{review_id}/rating`
- `DELETE /api/v1/reviews/{review_id}/rating`
- `GET /api/v1/reviews/{review_id}/rating/my`

## 🛠 Tech Stack

Core:

- Python 3.14+
- FastAPI
- Pydantic v2
- Uvicorn

Storage and infra:

- MongoDB (PyMongo Async driver)
- Redis (JWT denylist checks)

Observability:

- OpenTelemetry FastAPI instrumentation

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- uv
- MongoDB
- Redis

### Installation

```bash
cd ugc
uv sync
```

Install test dependencies as well:

```bash
uv sync --group test
```

### Run the Application

Development:

```bash
uv run fastapi dev src/main.py
```

Production-like:

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Docs and OpenAPI:

- Docs UI: `http://localhost:8000/api/ugc/docs`
- OpenAPI JSON: `http://localhost:8000/api/ugc/openapi.json`

Health endpoint:

- `http://localhost:8000/api/health`

## 🔧 Configuration

Main settings are loaded from environment variables or `.env`.

Required:

- `AUTHJWT_SECRET_KEY` (at least 32 characters)

Common settings:

- `DEVELOPMENT_MODE` (default `false`)
- `MONGODB_HOST` (default `127.0.0.1`)
- `MONGODB_PORT` (default `27017`)
- `MONGODB_DATABASE` (default `ugc_database`)
- `MONGODB_ROOT_USERNAME` (default `mongo`)
- `MONGODB_ROOT_PASSWORD` (default `mongo_password`)
- `REDIS_HOST` (default `127.0.0.1`)
- `REDIS_PORT` (default `6379`)
- `AUTHJWT_ALGORITHM` (default `HS256`)
- `SUBSCRIBER_ROLE_NAME` (default `subscriber`)
- `ADMIN_ROLE_NAME` (default `admin`)
- `OTEL_TRACES_ENDPOINT` (default `http://localhost:4318/v1/traces`)
- `OTEL_CONSOLE_EXPORT_ENABLED` (default `false`)

## ✅ Testing

Run tests:

```bash
cd ugc
uv run --group test pytest tests -q
```

Current functional coverage includes:

- bookmarks lifecycle and pagination
- reviews lifecycle, retrieval, sorting, pagination
- ratings lifecycle for movies and reviews
- not-found behavior for missing reviews in review-rating endpoints
- cascade cleanup of review ratings on review deletion

## 🏗 Project Structure

```
ugc/
├── src/
│   ├── api/
│   │   ├── health.py
│   │   └── v1/
│   │       ├── bookmarks.py
│   │       ├── paginators.py
│   │       ├── ratings.py
│   │       ├── reviews.py
│   │       └── schemas.py
│   ├── core/
│   │   ├── authentication.py
│   │   ├── authorization.py
│   │   ├── config.py
│   │   ├── lifespan.py
│   │   ├── middleware.py
│   │   └── token_validation.py
│   ├── db/
│   │   ├── mongo.py
│   │   └── redis.py
│   ├── services/
│   │   ├── bookmarks.py
│   │   ├── ratings.py
│   │   └── reviews.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_bookmarks_api.py
│   ├── test_ratings_api.py
│   └── test_reviews_api.py
└── pyproject.toml
```
