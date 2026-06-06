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
        self.fail_flush_once = False

    def begin(self):
        return _BeginCtx()

    async def scalar(self, _query):
        if not self._scalar_results:
            return None
        return self._scalar_results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        if self.fail_flush_once:
            self.fail_flush_once = False
            raise RuntimeError("db finalize failed")
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


# EC-7: Partial refund (amount < payment.amount) succeeds
@pytest.mark.asyncio
async def test_create_partial_refund_uses_specified_amount(monkeypatch):
    payment_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_id=uuid4(),
        status=PaymentStatus.SUCCEEDED.value,
        amount=500,
        currency="rub",
        stripe_payment_intent_id="pi_partial",
    )
    locked_refund = SimpleNamespace(
        id=uuid4(),
        payment_id=payment_id,
        operation_id="r-partial",
        status=None,
        amount=200,
        currency="rub",
        reason="",
        stripe_refund_id=None,
    )
    session = FakeSession([payment, None, 0, locked_refund])

    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")
    monkeypatch.setattr(
        "src.services.refunds.stripe.Refund.create",
        lambda **kwargs: {"id": "re_partial"},
    )

    result = await create_refund_for_payment(
        session,
        user_id=payment.user_id,
        payment_id=payment.id,
        operation_id="r-partial",
        amount=200,
    )

    assert result.created is True
    assert locked_refund.stripe_refund_id == "re_partial"
    assert locked_refund.status == RefundStatus.PENDING.value


# EC-11: Refund exceeds available refundable amount
@pytest.mark.asyncio
async def test_create_refund_raises_when_amount_exceeds_available(monkeypatch):
    payment_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_id=uuid4(),
        status=PaymentStatus.SUCCEEDED.value,
        amount=500,
        currency="rub",
        stripe_payment_intent_id="pi_over",
    )
    # All 500 already reserved by prior refunds
    session = FakeSession([payment, None, 500])

    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")

    with pytest.raises(BillingValidationError, match="exceeds available refundable amount"):
        await create_refund_for_payment(
            session,
            user_id=payment.user_id,
            payment_id=payment.id,
            operation_id="r-over",
            amount=100,
        )


@pytest.mark.asyncio
async def test_create_refund_recovers_after_finalize_failure(monkeypatch):
    payment_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_id=uuid4(),
        status=PaymentStatus.SUCCEEDED.value,
        amount=700,
        currency="rub",
        stripe_payment_intent_id="pi_recover_refund",
    )
    existing_refund = SimpleNamespace(
        id=uuid4(),
        payment_id=payment_id,
        operation_id="r-recover",
        status=RefundStatus.NEW.value,
        amount=200,
        currency="rub",
        reason="",
        stripe_refund_id=None,
    )
    session = FakeSession([payment, existing_refund, existing_refund])

    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")

    stripe_call_count = 0

    def _fake_refund_create(**kwargs):
        nonlocal stripe_call_count
        stripe_call_count += 1
        return {"id": "re_recover"}

    monkeypatch.setattr("src.services.refunds.stripe.Refund.create", _fake_refund_create)

    session.fail_flush_once = True
    with pytest.raises(RuntimeError, match="db finalize failed"):
        await create_refund_for_payment(
            session,
            user_id=payment.user_id,
            payment_id=payment.id,
            operation_id="r-recover",
            amount=200,
        )

    # Emulate DB rollback: previous flush failed, so Stripe refund ID was not persisted.
    existing_refund.stripe_refund_id = None

    # Retry with the same operation_id should reconcile persisted Stripe ID.
    session._scalar_results.extend([payment, existing_refund, existing_refund])
    result = await create_refund_for_payment(
        session,
        user_id=payment.user_id,
        payment_id=payment.id,
        operation_id="r-recover",
        amount=200,
    )

    assert stripe_call_count == 2
    assert result.refund.stripe_refund_id == "re_recover"
    assert result.refund.status == RefundStatus.PENDING.value


@pytest.mark.asyncio
async def test_create_refund_raises_when_finalize_row_missing(monkeypatch):
    payment_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_id=uuid4(),
        status=PaymentStatus.SUCCEEDED.value,
        amount=500,
        currency="rub",
        stripe_payment_intent_id="pi_finalize_missing",
    )
    session = FakeSession([payment, None, 0, None])

    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")
    monkeypatch.setattr(
        "src.services.refunds.stripe.Refund.create",
        lambda **kwargs: {"id": "re_finalize_missing"},
    )

    with pytest.raises(BillingValidationError, match="Refund record is unavailable"):
        await create_refund_for_payment(
            session,
            user_id=payment.user_id,
            payment_id=payment.id,
            operation_id="r-finalize-missing",
            amount=100,
        )


@pytest.mark.asyncio
async def test_create_refund_keeps_original_error_when_mark_failed_row_missing(monkeypatch):
    payment_id = uuid4()
    payment = SimpleNamespace(
        id=payment_id,
        user_id=uuid4(),
        status=PaymentStatus.SUCCEEDED.value,
        amount=500,
        currency="rub",
        stripe_payment_intent_id="pi_mark_failed_missing",
    )
    session = FakeSession([payment, None, 0])

    monkeypatch.setattr("src.services.refunds.configure_stripe_client", lambda: "sk_test")

    def _refund_create_error(**kwargs):
        raise stripe.error.APIConnectionError("network")

    monkeypatch.setattr("src.services.refunds.stripe.Refund.create", _refund_create_error)

    with pytest.raises(BillingValidationError, match="temporarily unavailable"):
        await create_refund_for_payment(
            session,
            user_id=payment.user_id,
            payment_id=payment.id,
            operation_id="r-mark-failed-missing",
            amount=200,
        )
