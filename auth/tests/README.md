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

## Coverage

Full coverage report:

```bash
uv run pytest tests --cov=src --cov-report=term-missing --cov-report=html
```

Fail on low coverage (example):

```bash
uv run pytest tests --cov=src --cov-fail-under=80
```

Coverage HTML report path: `auth/htmlcov/index.html`.
