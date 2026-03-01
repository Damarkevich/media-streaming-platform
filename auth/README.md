# Auth Service for Movies Platform

Authentication and authorization service for the media streaming platform.
The service is built with FastAPI and provides user registration, login,
JWT refresh/revoke flows, and current-user lookup.

## 🎯 Overview

This service is responsible for:

- user account creation;
- issuing access/refresh JWT tokens;
- token refresh;
- access-token revocation via Redis blacklist;
- refresh-token revocation via PostgreSQL blacklist;
- identifying the currently authenticated user (`/users/me`).

### Key Features

- **Asynchronous API** with FastAPI
- **JWT Authentication** (`async-fastapi-jwt-auth`)
- **Access Token Revocation** via Redis blacklist
- **Refresh Token Revocation** via PostgreSQL blacklist table
- **Password Validation** with explicit complexity rules
- **PostgreSQL Persistence** for users and blacklisted tokens
- **Health Check Endpoint** for Redis/PostgreSQL availability

## 📚 Logic Description

### Architecture

The application follows a layered architecture:

```
┌─────────────────┐
│   API Layer     │  FastAPI routes and HTTP mapping
├─────────────────┤
│ Service Layer   │  User/token business logic
├─────────────────┤
│   DB Layer      │  PostgreSQL session and Redis client
└─────────────────┘
```

### Core Endpoints

#### Auth (`/api/v1/auth`)

- `POST /signup` — register a new user
- `POST /login` — obtain `access_token` and `refresh_token`
- `POST /refresh` — issue a new token pair using a valid refresh token
- `DELETE /access-revoke` — revoke current access token
- `DELETE /refresh-revoke` — revoke current refresh token

#### Users (`/api/v1/users`)

- `GET /me` — return current user profile
- `PATCH /me/login` — change current user login
- `PATCH /me/password` — change current user password

#### Health (`/api`)

- `GET /health` — status of Redis/PostgreSQL dependencies

### Authentication Flow

1. User logs in with `login/password`.
2. Service returns access + refresh tokens.
3. Protected endpoints use `Authorization: Bearer <token>`.
4. `DELETE /access-revoke` writes access token `jti` to Redis blacklist.
5. `DELETE /refresh-revoke` writes refresh token `jti` to PostgreSQL blacklist.
6. Blacklisted access tokens are rejected on access-protected endpoints.
7. Blacklisted refresh tokens are rejected on `/refresh`.
8. `PATCH /users/me/login` and `PATCH /users/me/password` require a **fresh** access token.
9. Access token issued by `/refresh` is non-fresh, so these endpoints return `401` until user re-authenticates via `/login`.

### Error Responses by Endpoint

The table below lists application-level and auth-related error codes returned by each endpoint.

| Endpoint | Error codes |
|---|---|
| `POST /api/v1/auth/signup` | `409` (login already exists), `422` (validation error) |
| `POST /api/v1/auth/login` | `401` (invalid credentials), `422` (validation error) |
| `POST /api/v1/auth/refresh` | `401` (authentication required, token invalid, or token revoked), `422` (wrong token type or token validation error) |
| `DELETE /api/v1/auth/access-revoke` | `401` (authentication required, token invalid, or token revoked), `422` (wrong token type or token validation error) |
| `DELETE /api/v1/auth/refresh-revoke` | `401` (authentication required, token invalid, or token revoked), `422` (wrong token type or token validation error) |
| `GET /api/v1/users/me` | `401` (authentication required, token invalid, or token revoked), `404` (user not found), `422` (wrong token type or token validation error) |
| `PATCH /api/v1/users/me/login` | `401` (authentication required, token invalid, token revoked, or fresh token required), `404` (user not found), `409` (login already exists), `422` (request validation error, wrong token type, or token validation error) |
| `PATCH /api/v1/users/me/password` | `401` (authentication required, token invalid, token revoked, or fresh token required), `404` (user not found), `422` (request validation error, wrong token type, or token validation error) |

## 🛠 Tech Stack

### Core

- **Python 3.14+**
- **FastAPI**
- **Pydantic v2**
- **Uvicorn**

### Data & Auth

- **PostgreSQL** (`SQLAlchemy asyncio`, `asyncpg`)
- **Redis**
- **async-fastapi-jwt-auth**
- **Alembic**

## 🚀 Getting Started

### Prerequisites

- Python 3.14+
- uv
- PostgreSQL instance
- Redis instance

### Installation

```bash
cd auth
uv sync --group test
```

### Run Database Migrations

```bash
uv run alembic upgrade head
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

API endpoints:

- API base: `http://localhost:8000/api/v1`
- Health: `http://localhost:8000/api/health`
- OpenAPI UI: `http://localhost:8000/api/openapi`

## ✅ Testing

Test suite includes:

- **Unit tests** for schema validation and service logic
- **Functional tests** for auth endpoints and revoke flow

Run all tests:

```bash
cd auth
uv run pytest tests -q
```

For detailed test notes, see `tests/README.md`.

## 🏗 Project Structure

```
auth/
├── alembic/                 # DB migrations
├── src/
│   ├── api/                 # API routes
│   │   ├── health.py
│   │   └── v1/
│   │       ├── auth.py
│   │       └── users.py
│   ├── core/                # settings, jwt config, lifespan
│   ├── db/                  # postgres and redis access
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── services/            # domain services
├── tests/
│   ├── functional/
│   └── unit/
└── pyproject.toml
```

## 🔧 Configuration

Main settings are loaded from environment variables (or `.env`):

- `APP_ENV` (`dev` | `test` | `prod`, default: `dev`)
- `AUTHJWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRES`
- `REFRESH_TOKEN_EXPIRES`
- `SQL_ECHO` (enabled only when `APP_ENV=dev`)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `SQL_HOST`, `SQL_PORT`
- `REDIS_HOST`, `REDIS_PORT`

> Note: `AUTHJWT_SECRET_KEY` is mandatory and must be non-empty.

## 📄 Notes

This module is part of the Media Streaming Platform monorepo.
