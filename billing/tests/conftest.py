import os

# Set required settings before importing src modules in tests.
os.environ.setdefault("POSTGRES_PASSWORD", "test-password")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_123")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_123")
