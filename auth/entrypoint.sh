#!/bin/sh
set -eu

# Apply DB migrations on container start to keep schema in sync.
uv run alembic upgrade head

exec uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
