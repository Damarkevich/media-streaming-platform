from types import SimpleNamespace
from uuid import uuid4

import pytest
import stripe

from src.models.billing import PaymentStatus, RefundStatus
from src.services.errors import BillingValidationError
from src.services.refunds import create_refund_for_payment


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
async def test_create_refund_raises_when_payment_not_found(monkeypatch):
    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")
    session = FakeSession([None])

    with pytest.raises(BillingValidationError, match="Payment not found"):
        await create_refund_for_payment(
            session,
            user_id=uuid4(),
            payment_id=uuid4(),
            operation_id="r-op-1",
            amount=100,
        )


@pytest.mark.asyncio
async def test_create_refund_returns_existing_by_operation_id(monkeypatch):
    payment_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_id=uuid4(),
        status=PaymentStatus.SUCCEEDED.value,
        amount=500,
        currency="rub",
        stripe_payment_intent_id="pi_1",
    )
    existing_refund = SimpleNamespace(
        id=uuid4(),
        payment_id=payment_id,
        operation_id="r-op-2",
        stripe_refund_id="re_exists",
    )
    session = FakeSession([payment, existing_refund])

    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")

    def _raise_if_called(**kwargs):
        raise AssertionError("Stripe should not be called when refund already exists")

    monkeypatch.setattr("src.services.refunds.stripe.Refund.create", _raise_if_called)

    result = await create_refund_for_payment(
        session,
        user_id=payment.user_id,
        payment_id=payment.id,
        operation_id="r-op-2",
        amount=100,
    )

    assert result.created is False
    assert result.refund is existing_refund


@pytest.mark.asyncio
async def test_create_refund_handles_stripe_error_and_marks_failed(monkeypatch):
    payment_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_id=uuid4(),
        status=PaymentStatus.SUCCEEDED.value,
        amount=500,
        currency="rub",
        stripe_payment_intent_id="pi_2",
    )
    new_refund = SimpleNamespace(
        id=uuid4(),
        payment_id=payment_id,
        operation_id="r-op-3",
        status=RefundStatus.NEW.value,
        amount=200,
        currency="rub",
        reason="",
        metadata_json={},
    )
    session = FakeSession([payment, None, 0, new_refund])

    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")

    def _refund_create_error(**kwargs):
        raise stripe.error.APIConnectionError("network")

    monkeypatch.setattr("src.services.refunds.stripe.Refund.create", _refund_create_error)

    with pytest.raises(BillingValidationError, match="temporarily unavailable"):
        await create_refund_for_payment(
            session,
            user_id=payment.user_id,
            payment_id=payment.id,
            operation_id="r-op-3",
            amount=200,
        )

    assert new_refund.status == RefundStatus.FAILED.value
    assert "stripe_error" in new_refund.metadata_json
