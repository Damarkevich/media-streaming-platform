# GitHub Actions Workflows

This directory contains configuration files for the project's CI/CD pipeline.

## Workflows

### 1. CI (ci.yml) - Combined Pipeline
**Triggers:** Push to `main`/`develop`, Pull Requests

Combined workflow that executes:
- **Lint job:** Code quality checks with ruff (formatting and linting) for all services
- **Test job:** Run tests for each service on Python 3.13, 3.14

**Features:**
- Tests run only after successful linting
- Uses matrix strategy for parallel testing
- Uses uv for fast dependency installation with `--system` flag
- Built-in uv caching for faster builds
- Coverage reports generated locally
- Test environment variables configured (AUTHJWT_SECRET_KEY, POSTGRES_PASSWORD)

### 2. Lint (lint.yml) - Linting Only
**Triggers:** Push to `main`/`develop`, Pull Requests

Standalone workflow for quick code quality checks:
- Format checking with `ruff format --check`
- Code style checking with `ruff check`

**Services:**
- async_api
- auth
- event_ingest
- etl-kafka-clickhouse
- etl-postgres-elasticsearch
- ugc

### 3. Tests (test.yml) - Testing Only
**Triggers:** Push to `main`/`develop`, Pull Requests

Standalone workflow for running tests:
- Python version matrix: 3.13, 3.14
- Testing with coverage
- Uses uv for fast dependency installation with `--system` flag
- Built-in uv caching

**Tested services:**
- async_api
- auth
- event_ingest
- ugc (uses mongomock-motor, no real MongoDB needed. Note: 2 tests skipped due to mongomock limitations with advanced aggregation pipelines)

## Matrix Strategy

All workflows use matrix strategy for parallel execution:

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ['3.13', '3.14']
    service: [async_api, auth, event_ingest, ugc]
```

This creates 8 parallel test jobs (4 services × 2 Python versions).

## Ruff Configuration

Linter settings are located in the `ruff.toml` file in the repository root.

Key rules:
- Line length: 88 characters (Black-compatible)
- Minimum Python version: 3.12
- Enabled rules: pycodestyle, pyflakes, isort, pep8-naming, pyupgrade, flake8-bugbear, and many others

## Usage

### Local Development

Install uv and ruff:
```bash
# Install uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
# or via pip
pip install uv

# Install ruff
uv tool install ruff
# or
pip install ruff
```

Code checks:
```bash
# Check entire project
ruff check .

# Check specific service
cd async_api
ruff check .

# Auto-fix issues
ruff check --fix .

# Check formatting
ruff format --check .

# Apply formatting
ruff format .
```

### Pre-commit Hooks

Install pre-commit hooks for automatic checks before commits:
```bash
pip install pre-commit
pre-commit install
```

## Caching

Workflows use built-in uv caching to speed up builds:
- Cache is automatically managed via `astral-sh/setup-uv@v5`
- Cache key is based on `cache-dependency-glob` (typically `pyproject.toml`)
- Cache is automatically invalidated when dependencies change
- uv is significantly faster than pip (10-100x)

## Test Environment Variables

Tests require certain environment variables to be set. In GitHub Actions, these are configured in the test workflows:

- **AUTHJWT_SECRET_KEY** - JWT secret key (minimum 32 characters) - required for auth, async_api, event_ingest, ugc services
- **POSTGRES_PASSWORD** - PostgreSQL password - required for auth service
- **SESSION_SECRET_KEY** - Session secret key (minimum 32 characters) - required for auth service (OAuth sessions)
- **GOOGLE_CLIENT_ID** - Google OAuth client ID - required for auth service
- **GOOGLE_CLIENT_SECRET** - Google OAuth client secret - required for auth service

For local testing, copy `.env.example` to `.env` in each service directory and set appropriate values.

## Extending

To add a new service to CI:
1. Add the service name to `matrix.service` in the relevant workflows
2. Ensure the service has a `pyproject.toml` with a `test` dependency group
3. Ensure tests run via pytest

## Links

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Why uv? (Benefits and Migration Guide)](../UV_BENEFITS.md)
- [pytest Documentation](https://docs.pytest.org/)
- [pre-commit Documentation](https://pre-commit.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
