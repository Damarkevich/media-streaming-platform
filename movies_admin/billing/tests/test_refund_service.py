from unittest.mock import patch

from django.test import TestCase, override_settings
import stripe

from accounts.models import User
from billing.models import Payment, PaymentStatus, Refund, RefundStatus
from billing.services.errors import BillingValidationError
from billing.services.refunds import create_refund_for_payment


class RefundServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="refund-user@example.com",
            password="secret",
        )
        self.payment = Payment.objects.create(
            user=self.user,
            operation_id="payment-op-1",
            status=PaymentStatus.SUCCEEDED,
            amount=49900,
            currency="rub",
            stripe_customer_id="cus_ref_1",
            stripe_payment_intent_id="pi_ref_1",
        )

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_creates_refund_in_stripe_and_db(self, refund_create_mock):
        refund_create_mock.return_value = {"id": "re_test_1"}

        result = create_refund_for_payment(
            payment=self.payment,
            operation_id="refund-op-1",
            amount=49900,
            reason="user request",
        )

        self.assertTrue(result.created)
        self.assertEqual(result.refund.stripe_refund_id, "re_test_1")
        refund_create_mock.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_returns_existing_refund_for_duplicate_operation(self, refund_create_mock):
        refund_create_mock.return_value = {"id": "re_dup_1"}

        first = create_refund_for_payment(
            payment=self.payment,
            operation_id="refund-op-dup",
            amount=49900,
        )
        second = create_refund_for_payment(
            payment=self.payment,
            operation_id="refund-op-dup",
            amount=49900,
        )

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.refund.id, second.refund.id)
        refund_create_mock.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_raises_validation_error_when_refund_exceeds_payment(self, refund_create_mock):
        with self.assertRaises(BillingValidationError):
            create_refund_for_payment(
                payment=self.payment,
                operation_id="refund-op-too-large",
                amount=60000,
            )

        refund_create_mock.assert_not_called()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_raises_validation_error_when_cumulative_refunds_exceed_payment(self, refund_create_mock):
        refund_create_mock.return_value = {"id": "re_first_ok_1"}

        create_refund_for_payment(
            payment=self.payment,
            operation_id="refund-op-first",
            amount=30000,
        )

        with self.assertRaises(BillingValidationError):
            create_refund_for_payment(
                payment=self.payment,
                operation_id="refund-op-second-too-large",
                amount=25000,
            )

        self.assertEqual(refund_create_mock.call_count, 1)

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_raises_validation_error_when_payment_not_succeeded(self, refund_create_mock):
        self.payment.status = PaymentStatus.PENDING
        self.payment.save(update_fields=["status"])

        with self.assertRaises(BillingValidationError):
            create_refund_for_payment(
                payment=self.payment,
                operation_id="refund-op-not-succeeded",
                amount=10000,
            )

        refund_create_mock.assert_not_called()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_raises_validation_error_when_payment_has_no_intent_id(self, refund_create_mock):
        self.payment.stripe_payment_intent_id = None
        self.payment.save(update_fields=["stripe_payment_intent_id"])

        with self.assertRaises(BillingValidationError):
            create_refund_for_payment(
                payment=self.payment,
                operation_id="refund-op-no-intent",
                amount=10000,
            )

        refund_create_mock.assert_not_called()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_marks_refund_failed_when_stripe_temporarily_unavailable(self, refund_create_mock):
        refund_create_mock.side_effect = stripe.error.APIConnectionError("connection lost")

        with self.assertRaises(BillingValidationError):
            create_refund_for_payment(
                payment=self.payment,
                operation_id="refund-op-stripe-down",
                amount=49900,
            )

        refund = Refund.objects.get(operation_id="refund-op-stripe-down")
        self.assertEqual(refund.status, RefundStatus.FAILED)
        self.assertIsNone(refund.stripe_refund_id)
        self.assertIn("stripe_error", refund.metadata)
        refund_create_mock.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.refunds.stripe.Refund.create")
    def test_retries_failed_refund_with_same_operation_id(self, refund_create_mock):
        refund_create_mock.side_effect = [
            stripe.error.APIConnectionError("connection lost"),
            {"id": "re_retry_ok_1"},
        ]

        with self.assertRaises(BillingValidationError):
            create_refund_for_payment(
                payment=self.payment,
                operation_id="refund-op-retry-after-stripe-down",
                amount=49900,
            )

        second_result = create_refund_for_payment(
            payment=self.payment,
            operation_id="refund-op-retry-after-stripe-down",
            amount=49900,
        )

        self.assertFalse(second_result.created)
        self.assertEqual(second_result.refund.stripe_refund_id, "re_retry_ok_1")
        self.assertEqual(second_result.refund.status, RefundStatus.PENDING)
        self.assertEqual(refund_create_mock.call_count, 2)
