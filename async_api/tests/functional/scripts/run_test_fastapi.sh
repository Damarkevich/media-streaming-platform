#!/bin/sh
set -eu

# Run from project root inside container.
cd /app

# Ensure test dependencies (including coverage) are available.
uv sync --frozen --group test

# Start FastAPI under coverage.
# - exec makes this process PID 1, so signals are delivered directly.
# - USR1 is used later to flush coverage data from a long-running server.
exec uv run --project /app coverage run \
  --rcfile=/app/.coveragerc \
  --save-signal=USR1 \
  --data-file=/coverage/.coverage.fastapi \
  -m uvicorn src.main:app --host 0.0.0.0 --port 8000
