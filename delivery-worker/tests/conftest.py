"""Shared fixtures for delivery-worker tests.

Settings are overridden via environment variables before any src.* module
is imported so pydantic-settings never reads a real .env or contacts
external services.
"""

import os

os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("BREVO_API_KEY", "test-brevo-key")
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key")
os.environ.setdefault("AUTH_INTERNAL_URL", "http://test-auth:8000")
os.environ.setdefault("REDIS_HOST", "localhost")
