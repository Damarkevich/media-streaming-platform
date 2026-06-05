from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.customers import create_or_get_customer_for_user


class _BeginCtx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeSession:
    def __init__(self, scalar_results):
        self._scalar_results = list(scalar_results)
        self.added = []
        self.flush_calls = 0

    def begin(self):
        return _BeginCtx()

    async def execute(self, _query):
        return None

    async def scalar(self, _query):
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1


# EC-13: First billing action — profile exists without customer → Stripe Customer created
@pytest.mark.asyncio
async def test_create_or_get_customer_creates_stripe_customer_when_missing(monkeypatch):
    user_id = uuid4()
    profile = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        stripe_customer_id=None,
    )
    session = FakeSession([profile])

    monkeypatch.setattr(
        "src.services.customers.configure_stripe_client", lambda: "sk_test"
    )
    monkeypatch.setattr(
        "src.services.customers.stripe.Customer.create",
        lambda **kwargs: {"id": "cus_new"},
    )

    result_profile, created = await create_or_get_customer_for_user(
        session, user_id=user_id, operation_id="op-1"
    )

    assert created is True
    assert result_profile.stripe_customer_id == "cus_new"


@pytest.mark.asyncio
async def test_create_or_get_customer_returns_existing_without_stripe_call(monkeypatch):
    user_id = uuid4()
    profile = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        stripe_customer_id="cus_existing",
    )
    session = FakeSession([profile])

    monkeypatch.setattr(
        "src.services.customers.configure_stripe_client", lambda: "sk_test"
    )

    def _should_not_be_called(**kwargs):
        raise AssertionError("Stripe.Customer.create should not be called")

    monkeypatch.setattr(
        "src.services.customers.stripe.Customer.create", _should_not_be_called
    )

    result_profile, created = await create_or_get_customer_for_user(
        session, user_id=user_id
    )

    assert created is False
    assert result_profile.stripe_customer_id == "cus_existing"
