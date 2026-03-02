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
- role and permission management (RBAC);
- permission-based access control for administrative endpoints.

### Key Features

- **Asynchronous API** with FastAPI
- **JWT Authentication** (`async-fastapi-jwt-auth`)
- **Access Token Revocation** via Redis blacklist
- **Refresh Token Revocation** via PostgreSQL blacklist table
- **RBAC Authorization** with role/permission assignments
- **Permission Guard Dependencies** returning `403` when permission is missing
- **Permission Cache** in Redis with TTL + invalidation on RBAC changes
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
│ Service Layer   │  User/token/RBAC business logic
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
- `GET /me/logs` — return logs of current user
- `GET /me/roles` — return roles of current user
- `GET /me/has_permission/{permission_name}` — check if current user has a permission

#### Roles (`/api/v1/roles`)

- `GET /` — list roles
- `GET /{role_id}` — get role by ID
- `POST /` — create role
- `PATCH /{role_id}` — update role name
- `DELETE /{role_id}` — delete role
- `GET /{role_id}/permissions` — list role permissions
- `PUT /{role_id}/users/{user_id}` — assign role to user
- `DELETE /{role_id}/users/{user_id}` — remove role from user

#### Permissions (`/api/v1/permissions`)

- `GET /` — list permissions
- `PUT /{permission_id}/roles/{role_id}` — assign permission to role
- `DELETE /{permission_id}/roles/{role_id}` — remove permission from role

### RBAC and Access Control

- Roles/permissions endpoints are protected by `require_permission(...)` dependencies.
- Missing permission returns `403 Forbidden`.
- Effective user permissions are calculated from `user_roles` and `role_permissions`.
- Effective permissions are cached in Redis (`auth:user_permissions:<user_id>`) for `PERMISSIONS_CACHE_TTL` seconds.
- Cache invalidates on role-user and role-permission assignment changes.

#### Permission → Endpoint Matrix

| Permission | Protected endpoints |
|---|---|
| `roles:read` | `GET /api/v1/roles`, `GET /api/v1/roles/{role_id}` |
| `roles:create` | `POST /api/v1/roles` |
| `roles:update` | `PATCH /api/v1/roles/{role_id}` |
| `roles:delete` | `DELETE /api/v1/roles/{role_id}` |
| `roles:assign` | `PUT /api/v1/roles/{role_id}/users/{user_id}`, `DELETE /api/v1/roles/{role_id}/users/{user_id}` |
| `permissions:read` | `GET /api/v1/permissions`, `GET /api/v1/roles/{role_id}/permissions` |
| `permissions:assign` | `PUT /api/v1/permissions/{permission_id}/roles/{role_id}`, `DELETE /api/v1/permissions/{permission_id}/roles/{role_id}` |

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

Choose dependency groups depending on your task:

- Runtime only (default dependencies):

```bash
cd auth
uv sync
```

- Development tools (`dev` group):

```bash
uv sync --group dev
```

- Test tools (`test` group):

```bash
uv sync --group test
```

- Full local setup (`dev` + `test`):

```bash
uv sync --group dev --group test
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

> Requires `dev` dependency group.

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

> Requires `test` dependency group.

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
│   │       ├── permissions.py
│   │       ├── roles.py
│   │       └── users.py
│   ├── core/                # settings, jwt config, lifespan
│   ├── db/                  # postgres and redis access
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── services/            # domain services (users, tokens, RBAC, authorization)
├── tests/
│   ├── functional/
│   └── unit/
└── pyproject.toml
```

## 🔧 Configuration

Main settings are loaded from environment variables (or `.env`):

- `AUTHJWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRES`
- `REFRESH_TOKEN_EXPIRES`
- `SQL_ECHO`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `POSTGRES_DB_SCHEMA`
- `SQL_HOST`, `SQL_PORT`
- `SQL_OPTIONS`
- `REDIS_HOST`, `REDIS_PORT`
- `PERMISSIONS_CACHE_TTL`

> Note: `AUTHJWT_SECRET_KEY` is mandatory and must be non-empty.

## 📄 Notes

This module is part of the Media Streaming Platform monorepo.
