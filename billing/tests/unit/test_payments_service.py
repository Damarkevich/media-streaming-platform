from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.billing import PaymentStatus
from src.services.errors import BillingValidationError
from src.services.payments import create_payment_intent_for_user


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

    async def scalar(self, _query):
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1


@pytest.mark.asyncio
async def test_create_payment_raises_for_non_positive_amount():
    session = FakeSession([])

    with pytest.raises(BillingValidationError, match="Amount must be greater"):
        await create_payment_intent_for_user(
            session,
            user_id=uuid4(),
            operation_id="op-1",
            amount=0,
        )


@pytest.mark.asyncio
async def test_create_payment_creates_new_payment(monkeypatch):
    user_id = uuid4()
    profile = SimpleNamespace(stripe_customer_id="cus_1")
    session = FakeSession([None])

    async def _fake_customer(*args, **kwargs):
        return profile, True

    monkeypatch.setattr("src.services.payments.create_or_get_customer_for_user", _fake_customer)
    monkeypatch.setattr("src.services.payments.configure_stripe_client", lambda: "sk_test")

    def _fake_payment_intent_create(**kwargs):
        return {"id": "pi_1", "client_secret": "cs_1"}

    monkeypatch.setattr("src.services.payments.stripe.PaymentIntent.create", _fake_payment_intent_create)

    result = await create_payment_intent_for_user(
        session,
        user_id=user_id,
        operation_id="op-2",
        amount=19900,
        currency="rub",
    )

    assert result.created is True
    assert result.client_secret == "cs_1"
    assert result.payment.status == PaymentStatus.PENDING.value
    assert result.payment.stripe_payment_intent_id == "pi_1"
    assert len(session.added) == 1


@pytest.mark.asyncio
async def test_create_payment_returns_existing_intent_without_stripe_call(monkeypatch):
    user_id = uuid4()
    profile = SimpleNamespace(stripe_customer_id="cus_2")
    existing_payment = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        operation_id="op-3",
        amount=29900,
        currency="rub",
        stripe_payment_intent_id="pi_exists",
    )
    session = FakeSession([existing_payment])

    async def _fake_customer(*args, **kwargs):
        return profile, False

    monkeypatch.setattr("src.services.payments.create_or_get_customer_for_user", _fake_customer)
    monkeypatch.setattr("src.services.payments.configure_stripe_client", lambda: "sk_test")

    def _raise_if_called(**kwargs):
        raise AssertionError("Stripe should not be called for existing payment intent")

    monkeypatch.setattr("src.services.payments.stripe.PaymentIntent.create", _raise_if_called)

    result = await create_payment_intent_for_user(
        session,
        user_id=user_id,
        operation_id="op-3",
        amount=29900,
        currency="rub",
    )

    assert result.created is False
    assert result.client_secret is None
    assert result.payment is existing_payment


@pytest.mark.asyncio
async def test_create_payment_rejects_operation_id_reuse_for_other_user(monkeypatch):
    user_id = uuid4()
    profile = SimpleNamespace(stripe_customer_id="cus_3")
    existing_payment = SimpleNamespace(
        user_id=uuid4(),
        operation_id="op-4",
        amount=9900,
        currency="rub",
        stripe_payment_intent_id=None,
    )
    session = FakeSession([existing_payment])

    async def _fake_customer(*args, **kwargs):
        return profile, False

    monkeypatch.setattr("src.services.payments.create_or_get_customer_for_user", _fake_customer)
    monkeypatch.setattr("src.services.payments.configure_stripe_client", lambda: "sk_test")

    with pytest.raises(BillingValidationError, match="another user"):
        await create_payment_intent_for_user(
            session,
            user_id=user_id,
            operation_id="op-4",
            amount=9900,
            currency="rub",
        )
