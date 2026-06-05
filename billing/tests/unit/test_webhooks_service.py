from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.models.billing import PaymentStatus, RefundStatus, WebhookEventStatus
from src.services.webhooks import process_stripe_event


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
async def test_process_stripe_event_returns_existing_webhook_event():
    existing_event = SimpleNamespace(status=WebhookEventStatus.PROCESSED.value)
    session = FakeSession([existing_event])

    result = await process_stripe_event(
        session,
        event={"id": "evt_1", "type": "payment_intent.succeeded"},
        raw_payload=b"{}",
    )

    assert result.created is False
    assert result.webhook_event is existing_event


@pytest.mark.asyncio
async def test_process_payment_succeeded_updates_payment_status():
    payment = SimpleNamespace(status=PaymentStatus.PENDING.value)
    session = FakeSession([None, payment])

    result = await process_stripe_event(
        session,
        event={
            "id": "evt_2",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_2"}},
        },
        raw_payload=b'{"ok":1}',
    )

    assert result.created is True
    assert payment.status == PaymentStatus.SUCCEEDED.value
    assert result.webhook_event.status == WebhookEventStatus.PROCESSED.value


@pytest.mark.asyncio
async def test_process_payment_failed_does_not_downgrade_succeeded_payment():
    payment = SimpleNamespace(status=PaymentStatus.SUCCEEDED.value)
    session = FakeSession([None, payment])

    result = await process_stripe_event(
        session,
        event={
            "id": "evt_3",
            "type": "payment_intent.payment_failed",
            "data": {"object": {"id": "pi_3"}},
        },
        raw_payload=b'{"ok":1}',
    )

    assert result.created is True
    assert payment.status == PaymentStatus.SUCCEEDED.value
    assert result.webhook_event.status == WebhookEventStatus.PROCESSED.value


@pytest.mark.asyncio
async def test_process_refund_failed_does_not_downgrade_succeeded_refund():
    refund = SimpleNamespace(status=RefundStatus.SUCCEEDED.value)
    session = FakeSession([None, refund])

    result = await process_stripe_event(
        session,
        event={
            "id": "evt_4",
            "type": "refund.updated",
            "data": {"object": {"id": "re_4", "status": "failed"}},
        },
        raw_payload=b'{"ok":1}',
    )

    assert result.created is True
    assert refund.status == RefundStatus.SUCCEEDED.value
    assert result.webhook_event.status == WebhookEventStatus.PROCESSED.value


@pytest.mark.asyncio
async def test_process_unknown_event_is_ignored():
    session = FakeSession([None])

    result = await process_stripe_event(
        session,
        event={"id": "evt_5", "type": "unknown.event", "data": {"object": {}}},
        raw_payload=b'{"ok":1}',
    )

    assert result.created is True
    assert result.webhook_event.status == WebhookEventStatus.IGNORED.value
    assert result.webhook_event.error_message == "Unsupported Stripe event type."


# EC-6: payment_intent.payment_failed on PENDING payment → FAILED
@pytest.mark.asyncio
async def test_process_payment_failed_updates_pending_payment_to_failed():
    payment = SimpleNamespace(status=PaymentStatus.PENDING.value)
    session = FakeSession([None, payment])

    result = await process_stripe_event(
        session,
        event={
            "id": "evt_6",
            "type": "payment_intent.payment_failed",
            "data": {"object": {"id": "pi_6"}},
        },
        raw_payload=b'{"ok":1}',
    )

    assert result.created is True
    assert payment.status == PaymentStatus.FAILED.value
    assert result.webhook_event.status == WebhookEventStatus.PROCESSED.value
