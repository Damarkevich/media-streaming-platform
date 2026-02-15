#!/bin/sh
set -eu

# Run from project root inside container.
cd /app

# Install test dependencies in container environment.
uv sync --group test

# Switch to functional tests directory.
cd /tests/functional

# Wait until dependent services are reachable.
uv run --project /app python utils/wait_for_es.py
uv run --project /app python utils/wait_for_redis.py

# Run functional test suite.
uv run --project /app pytest src -v
