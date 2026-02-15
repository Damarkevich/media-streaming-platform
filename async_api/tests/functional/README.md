# Functional Tests

This directory contains functional API tests.

## What Is Covered

- main public service endpoints (`films`, `genres`, `persons`, `health`)
- correct response status codes and payload formats
- basic caching scenarios
- behavior for invalid parameters and `not found` cases

## How It Runs

`docker-compose.yml` starts a test stack with the following containers:

- `test-elasticsearch` — search data store
- `test-redis` — cache
- `test-fastapi` — FastAPI application
- `tests` — container that runs `pytest`

Tests are executed in the `tests` container. It waits until dependencies (`elasticsearch`, `redis`, `fastapi`) are healthy, then runs the test suite.

## Quick Start

From the `tests/functional` directory:

```bash
docker compose up
```

If you want to explicitly run only the test service:

```bash
docker compose up --build tests
```

## After the Run

Stop and remove containers:

```bash
docker compose down
```

For the coverage workflow, see `README_COVERAGE.md`.
