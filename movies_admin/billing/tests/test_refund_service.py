from unittest.mock import patch

from django.test import TestCase, override_settings

from accounts.models import User
from billing.models import Payment, PaymentStatus
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
