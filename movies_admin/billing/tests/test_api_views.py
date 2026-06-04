from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from billing.models import Payment, PaymentStatus, Refund, RefundStatus, WebhookEvent, WebhookEventStatus
from billing.services.errors import BillingValidationError
from billing.services.payments import PaymentCreateResult
from billing.services.refunds import RefundCreateResult


class BillingApiViewsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="api-billing-user@example.com",
            password="secret",
        )
        self.client.force_authenticate(user=self.user)

        self.payment = Payment.objects.create(
            user=self.user,
            operation_id="api-pay-op-1",
            status=PaymentStatus.PENDING,
            amount=49900,
            currency="rub",
            stripe_customer_id="cus_api_1",
            stripe_payment_intent_id="pi_api_1",
            metadata={"client_secret": "cs_api_1"},
        )
        self.other_user = User.objects.create_user(
            email="api-billing-other@example.com",
            password="secret",
        )
        self.other_payment = Payment.objects.create(
            user=self.other_user,
            operation_id="api-pay-op-2",
            status=PaymentStatus.PENDING,
            amount=29900,
            currency="rub",
            stripe_customer_id="cus_api_2",
            stripe_payment_intent_id="pi_api_2",
            metadata={"client_secret": "cs_api_2"},
        )

    @patch("billing.api.v1.views.create_payment_intent_for_user")
    def test_payment_create_endpoint(self, payment_create_mock):
        payment_create_mock.return_value = PaymentCreateResult(
            payment=self.payment,
            created=True,
            client_secret="cs_api_1",
        )

        response = self.client.post(
            reverse("billing-payment-create"),
            {
                "operation_id": "api-op-new",
                "amount": 49900,
                "currency": "rub",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.payment.id))
        self.assertTrue(response.data["created"])
        payment_create_mock.assert_called_once()

    @patch("billing.api.v1.views.create_payment_intent_for_user")
    def test_payment_create_endpoint_returns_400_for_invalid_operation(self, payment_create_mock):
        payment_create_mock.side_effect = BillingValidationError(
            "Operation ID already exists with different amount or currency."
        )

        response = self.client.post(
            reverse("billing-payment-create"),
            {
                "operation_id": "api-op-conflict",
                "amount": 39900,
                "currency": "rub",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Operation ID already exists with different amount or currency.",
        )

    def test_payment_detail_endpoint(self):
        response = self.client.get(
            reverse("billing-payment-detail", kwargs={"payment_id": self.payment.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.payment.id))
        self.assertEqual(response.data["status"], PaymentStatus.PENDING)

    def test_payment_detail_endpoint_returns_404_for_other_user_payment(self):
        response = self.client.get(
            reverse("billing-payment-detail", kwargs={"payment_id": self.other_payment.id})
        )

        self.assertEqual(response.status_code, 404)

    @patch("billing.api.v1.views.create_refund_for_payment")
    def test_refund_create_endpoint(self, refund_create_mock):
        refund = Refund.objects.create(
            payment=self.payment,
            operation_id="api-ref-op-1",
            status=RefundStatus.PENDING,
            amount=49900,
            currency="rub",
            stripe_refund_id="re_api_1",
        )
        refund_create_mock.return_value = RefundCreateResult(refund=refund, created=True)

        response = self.client.post(
            reverse("billing-refund-create"),
            {
                "payment_id": str(self.payment.id),
                "operation_id": "api-refund-op-new",
                "amount": 49900,
                "reason": "user request",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(refund.id))
        self.assertTrue(response.data["created"])
        refund_create_mock.assert_called_once()

    @patch("billing.api.v1.views.create_refund_for_payment")
    def test_refund_create_endpoint_returns_404_for_other_user_payment(self, refund_create_mock):
        response = self.client.post(
            reverse("billing-refund-create"),
            {
                "payment_id": str(self.other_payment.id),
                "operation_id": "api-refund-op-other",
                "amount": 29900,
                "reason": "user request",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 404)
        refund_create_mock.assert_not_called()

    @patch("billing.api.v1.views.create_refund_for_payment")
    def test_refund_create_endpoint_returns_400_for_invalid_amount(self, refund_create_mock):
        refund_create_mock.side_effect = BillingValidationError(
            "Refund amount cannot exceed the original payment amount."
        )

        response = self.client.post(
            reverse("billing-refund-create"),
            {
                "payment_id": str(self.payment.id),
                "operation_id": "api-refund-op-too-large",
                "amount": 99999,
                "reason": "user request",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Refund amount cannot exceed the original payment amount.",
        )

    @patch("billing.api.v1.views.create_refund_for_payment")
    def test_refund_create_endpoint_returns_400_for_cumulative_overflow(self, refund_create_mock):
        refund_create_mock.side_effect = BillingValidationError(
            "Refund amount exceeds available refundable amount."
        )

        response = self.client.post(
            reverse("billing-refund-create"),
            {
                "payment_id": str(self.payment.id),
                "operation_id": "api-refund-op-cumulative-too-large",
                "amount": 25000,
                "reason": "user request",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Refund amount exceeds available refundable amount.",
        )

    @patch("billing.api.v1.views.create_refund_for_payment")
    def test_refund_create_endpoint_returns_400_when_payment_not_succeeded(self, refund_create_mock):
        refund_create_mock.side_effect = BillingValidationError(
            "Refund can be created only for succeeded payments."
        )

        response = self.client.post(
            reverse("billing-refund-create"),
            {
                "payment_id": str(self.payment.id),
                "operation_id": "api-refund-op-not-succeeded",
                "amount": 10000,
                "reason": "user request",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Refund can be created only for succeeded payments.",
        )

    @patch("billing.api.v1.views.create_refund_for_payment")
    def test_refund_create_endpoint_returns_400_when_payment_has_no_intent(self, refund_create_mock):
        refund_create_mock.side_effect = BillingValidationError(
            "Payment has no Stripe PaymentIntent ID for refund creation."
        )

        response = self.client.post(
            reverse("billing-refund-create"),
            {
                "payment_id": str(self.payment.id),
                "operation_id": "api-refund-op-no-intent",
                "amount": 10000,
                "reason": "user request",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["detail"],
            "Payment has no Stripe PaymentIntent ID for refund creation.",
        )


class StripeWebhookApiViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("billing.api.v1.views.process_stripe_event")
    @patch("billing.api.v1.views.stripe.Webhook.construct_event")
    def test_webhook_endpoint(self, construct_event_mock, process_event_mock):
        construct_event_mock.return_value = {
            "id": "evt_api_1",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_api_1"}},
        }

        webhook_event = WebhookEvent.objects.create(
            stripe_event_id="evt_api_1",
            event_type="payment_intent.succeeded",
            status=WebhookEventStatus.PROCESSED,
            payload_hash="a" * 64,
            payload={"id": "evt_api_1"},
        )
        process_event_mock.return_value = (webhook_event, True)

        response = self.client.post(
            reverse("billing-stripe-webhook"),
            data="{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=123,v1=abc",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["webhook_event_id"], str(webhook_event.id))
        self.assertTrue(response.data["created"])
        construct_event_mock.assert_called_once()
        process_event_mock.assert_called_once()


class BillingApiViewsUnauthorizedTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="api-billing-unauth-user@example.com",
            password="secret",
        )
        self.payment = Payment.objects.create(
            user=self.user,
            operation_id="api-pay-op-unauth",
            status=PaymentStatus.PENDING,
            amount=19900,
            currency="rub",
            stripe_customer_id="cus_api_unauth",
            stripe_payment_intent_id="pi_api_unauth",
            metadata={"client_secret": "cs_api_unauth"},
        )

    @patch("billing.api.v1.views.create_payment_intent_for_user")
    def test_payment_create_endpoint_requires_authentication(self, payment_create_mock):
        response = self.client.post(
            reverse("billing-payment-create"),
            {
                "operation_id": "api-op-unauth",
                "amount": 19900,
                "currency": "rub",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        payment_create_mock.assert_not_called()

    def test_payment_detail_endpoint_requires_authentication(self):
        response = self.client.get(
            reverse("billing-payment-detail", kwargs={"payment_id": self.payment.id})
        )

        self.assertEqual(response.status_code, 403)

    @patch("billing.api.v1.views.create_refund_for_payment")
    def test_refund_create_endpoint_requires_authentication(self, refund_create_mock):
        response = self.client.post(
            reverse("billing-refund-create"),
            {
                "payment_id": str(self.payment.id),
                "operation_id": "api-refund-op-unauth",
                "amount": 19900,
                "reason": "user request",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        refund_create_mock.assert_not_called()
