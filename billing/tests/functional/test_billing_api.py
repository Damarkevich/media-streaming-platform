from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
import stripe
from httpx import ASGITransport, AsyncClient

from src.db.postgres import get_session
from src.main import app


class FakeSession:
    def __init__(self, payment=None):
        self.payment = payment

    async def scalar(self, _query):
        return self.payment


@pytest_asyncio.fixture(autouse=True)
async def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@dataclass
class FakePaymentResult:
    payment: object
    created: bool
    client_secret: str | None


@dataclass
class FakeRefundResult:
    refund: object
    created: bool


@pytest.mark.asyncio
async def test_create_payment_endpoint_returns_payload(test_client, monkeypatch):
    payment_id = uuid4()
    now = datetime.now(tz=UTC)
    payment = SimpleNamespace(
        id=payment_id,
        operation_id="op-1",
        status="pending",
        amount=49900,
        currency="rub",
        stripe_payment_intent_id="pi_1",
        created_at=now,
        updated_at=now,
    )

    async def _create_payment(*args, **kwargs):
        return FakePaymentResult(payment=payment, created=True, client_secret="cs_1")

    monkeypatch.setattr("src.api.v1.billing.create_payment_intent_for_user", _create_payment)

    response = await test_client.post(
        "/api/v1/billing/payments/create",
        headers={"X-User-Id": str(uuid4())},
        json={"operation_id": "op-1", "amount": 49900, "currency": "rub"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(payment_id)
    assert body["created"] is True
    assert body["client_secret"] == "cs_1"


@pytest.mark.asyncio
async def test_create_payment_endpoint_returns_400_for_validation_error(
    test_client,
    monkeypatch,
):
    from src.services.errors import BillingValidationError

    async def _create_payment(*args, **kwargs):
        raise BillingValidationError("bad payment")

    monkeypatch.setattr("src.api.v1.billing.create_payment_intent_for_user", _create_payment)

    response = await test_client.post(
        "/api/v1/billing/payments/create",
        headers={"X-User-Id": str(uuid4())},
        json={"operation_id": "op-1", "amount": 49900, "currency": "rub"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "bad payment"


@pytest.mark.asyncio
async def test_get_payment_returns_404_for_unknown_payment(test_client):
    async def _override_session():
        yield FakeSession(payment=None)

    app.dependency_overrides[get_session] = _override_session

    response = await test_client.get(
        f"/api/v1/billing/payments/{uuid4()}",
        headers={"X-User-Id": str(uuid4())},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_payment_returns_owned_payment(test_client):
    payment_id = uuid4()
    now = datetime.now(tz=UTC)
    payment = SimpleNamespace(
        id=payment_id,
        operation_id="op-2",
        status="succeeded",
        amount=49900,
        currency="rub",
        stripe_payment_intent_id="pi_2",
        created_at=now,
        updated_at=now,
    )

    async def _override_session():
        yield FakeSession(payment=payment)

    app.dependency_overrides[get_session] = _override_session

    response = await test_client.get(
        f"/api/v1/billing/payments/{payment_id}",
        headers={"X-User-Id": str(uuid4())},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(payment_id)


@pytest.mark.asyncio
async def test_create_refund_endpoint_returns_payload(test_client, monkeypatch):
    refund_id = uuid4()
    payment_id = uuid4()
    now = datetime.now(tz=UTC)
    refund = SimpleNamespace(
        id=refund_id,
        payment_id=payment_id,
        operation_id="op-ref-1",
        status="pending",
        amount=10000,
        currency="rub",
        reason="user request",
        stripe_refund_id="re_1",
        created_at=now,
        updated_at=now,
    )

    async def _create_refund(*args, **kwargs):
        return FakeRefundResult(refund=refund, created=True)

    monkeypatch.setattr("src.api.v1.billing.create_refund_for_payment", _create_refund)

    response = await test_client.post(
        "/api/v1/billing/refunds/create",
        headers={"X-User-Id": str(uuid4())},
        json={
            "payment_id": str(payment_id),
            "operation_id": "op-ref-1",
            "amount": 10000,
            "reason": "user request",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(refund_id)
    assert body["created"] is True


@pytest.mark.asyncio
async def test_create_refund_endpoint_returns_400_for_validation_error(
    test_client,
    monkeypatch,
):
    from src.services.errors import BillingValidationError

    async def _create_refund(*args, **kwargs):
        raise BillingValidationError("bad refund")

    monkeypatch.setattr("src.api.v1.billing.create_refund_for_payment", _create_refund)

    response = await test_client.post(
        "/api/v1/billing/refunds/create",
        headers={"X-User-Id": str(uuid4())},
        json={
            "payment_id": str(uuid4()),
            "operation_id": "op-ref-2",
            "amount": 10000,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "bad refund"


@pytest.mark.asyncio
async def test_webhook_endpoint_returns_400_for_missing_signature(test_client):
    response = await test_client.post("/api/v1/billing/webhooks/stripe", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Stripe-Signature header is required."


@pytest.mark.asyncio
async def test_webhook_endpoint_returns_400_for_invalid_payload(test_client, monkeypatch):
    def _construct_event(*args, **kwargs):
        raise ValueError("bad payload")

    monkeypatch.setattr("src.api.v1.billing.stripe.Webhook.construct_event", _construct_event)

    response = await test_client.post(
        "/api/v1/billing/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=abc"},
        content=b"not-json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Stripe webhook payload."


@pytest.mark.asyncio
async def test_webhook_endpoint_returns_400_for_invalid_signature(
    test_client,
    monkeypatch,
):
    def _construct_event(*args, **kwargs):
        raise stripe.error.SignatureVerificationError("bad", "sig")

    monkeypatch.setattr("src.api.v1.billing.stripe.Webhook.construct_event", _construct_event)

    response = await test_client.post(
        "/api/v1/billing/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=bad"},
        content=b"{}",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Stripe signature."


@pytest.mark.asyncio
async def test_webhook_endpoint_returns_processed_payload(test_client, monkeypatch):
    webhook_id = uuid4()

    def _construct_event(*args, **kwargs):
        return {"id": "evt_1", "type": "payment_intent.succeeded", "data": {"object": {}}}

    async def _process_event(*args, **kwargs):
        return SimpleNamespace(
            webhook_event=SimpleNamespace(id=webhook_id, status="processed"),
            created=True,
        )

    monkeypatch.setattr("src.api.v1.billing.stripe.Webhook.construct_event", _construct_event)
    monkeypatch.setattr("src.api.v1.billing.process_stripe_event", _process_event)

    response = await test_client.post(
        "/api/v1/billing/webhooks/stripe",
        headers={"Stripe-Signature": "t=1,v1=ok"},
        content=b"{}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["webhook_event_id"] == str(webhook_id)
    assert body["created"] is True
    assert body["status"] == "processed"
