# Tests

Minimal commands to run test suites for the `auth` service.

## Quick Start

From the `auth` directory:

```bash
uv sync --group test
```

Run all tests:

```bash
uv run pytest tests -q
```

Run functional tests:

```bash
uv run pytest tests/functional -q
```

Run unit tests:

```bash
uv run pytest tests/unit -q
```

Run focused suites:

```bash
uv run pytest tests/unit/test_blacklist_checker.py -q
uv run pytest tests/unit/test_jwt_blacklist_loader.py -q
uv run pytest tests/unit/test_permission_check_service_cache.py -q
uv run pytest tests/functional/test_roles_access_permissions.py -q
uv run pytest tests/functional/test_users_me_endpoints.py -q
```

## Coverage

Full coverage report:

```bash
uv run pytest tests --cov=src --cov-report=term-missing --cov-report=html
```

Fail on low coverage (example):

```bash
uv run pytest tests --cov=src --cov-fail-under=80
```

Coverage HTML report path: `htmlcov/index.html`.

## What is covered

- JWT issue/refresh/revoke flows
- Access-token denylist checks (Redis)
- Refresh-token denylist checks (PostgreSQL)
- RBAC access checks (`403` on missing permission)
- Permission cache behavior and invalidation paths
- User profile endpoints (`/users/me`, login/password change, roles, logs)
