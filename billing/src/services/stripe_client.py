from __future__ import annotations

import stripe

from src.core.config import settings


def configure_stripe_client() -> str:
    stripe.api_key = settings.stripe_secret_key
    return settings.stripe_secret_key
