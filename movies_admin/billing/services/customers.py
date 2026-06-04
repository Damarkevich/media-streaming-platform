from uuid import uuid4

import stripe
from django.contrib.auth import get_user_model
from django.db import transaction

from billing.models import BillingProfile
from billing.services.stripe_client import configure_stripe_client


def _build_customer_name(user) -> str:
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


def create_or_get_customer_for_user(
    user, *, operation_id: str | None = None
) -> tuple[BillingProfile, bool]:
    """Get an existing Stripe customer id for a user or create a new one safely."""
    user_model = get_user_model()

    with transaction.atomic():
        # Lock the user row to serialize first-time billing requests.
        locked_user = user_model.objects.select_for_update().get(pk=user.pk)
        profile, _ = BillingProfile.objects.get_or_create(user=locked_user)
        if profile.stripe_customer_id:
            return profile, False

        configure_stripe_client()
        idempotency_key = f"customer-create:{locked_user.pk}:{operation_id or uuid4()}"
        customer = stripe.Customer.create(
            email=locked_user.email,
            name=_build_customer_name(locked_user),
            metadata={"user_id": str(locked_user.pk)},
            idempotency_key=idempotency_key,
        )

        customer_id = (
            customer.get("id")
            if isinstance(customer, dict)
            else getattr(customer, "id", None)
        )
        if not customer_id:
            msg = "Stripe did not return customer id"
            raise RuntimeError(msg)

        profile.stripe_customer_id = customer_id
        profile.save(update_fields=["stripe_customer_id", "updated_at"])
        return profile, True
