from __future__ import annotations

import stripe
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def require_stripe_secret_key() -> str:
    secret_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not secret_key:
        msg = "STRIPE_SECRET_KEY is not set"
        raise ImproperlyConfigured(msg)
    return secret_key


def configure_stripe_client() -> str:
    secret_key = require_stripe_secret_key()
    stripe.api_key = secret_key
    return secret_key
