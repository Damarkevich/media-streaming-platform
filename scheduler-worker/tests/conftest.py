"""Shared fixtures for scheduler-worker tests.

Settings are overridden via environment variables before the module is imported
so that pydantic-settings never attempts to read a real .env file or connect
to external services.
"""

import os

import pytest

# ---------------------------------------------------------------------------
# Provide required env vars before any src.* module is imported.
# ---------------------------------------------------------------------------
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("AUTH_INTERNAL_URL", "http://test-auth:8000")
os.environ.setdefault("ASYNC_API_URL", "http://test-async-api:8000")
