from unittest.mock import patch

from django.test import TestCase, override_settings

from accounts.models import User
from billing.models import BillingProfile, Payment, PaymentStatus
from billing.services.errors import BillingValidationError
from billing.services.payments import create_payment_intent_for_user


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="payer@example.com",
            password="secret",
        )

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.payments.stripe.PaymentIntent.create")
    @patch("billing.services.customers.stripe.Customer.create")
    def test_creates_payment_intent_for_new_operation(
        self,
        customer_create_mock,
        payment_intent_create_mock,
    ):
        customer_create_mock.return_value = {"id": "cus_stage3_1"}
        payment_intent_create_mock.return_value = {
            "id": "pi_stage3_1",
            "client_secret": "cs_stage3_1",
        }

        result = create_payment_intent_for_user(
            self.user,
            operation_id="op-pay-1",
            amount=49900,
        )

        self.assertTrue(result.created)
        self.assertEqual(result.payment.operation_id, "op-pay-1")
        self.assertEqual(result.payment.stripe_payment_intent_id, "pi_stage3_1")
        self.assertEqual(result.client_secret, "cs_stage3_1")
        self.assertNotIn("client_secret", result.payment.metadata)
        customer_create_mock.assert_called_once()
        payment_intent_create_mock.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.payments.stripe.PaymentIntent.create")
    def test_returns_existing_payment_for_duplicate_operation(self, payment_intent_create_mock):
        BillingProfile.objects.create(
            user=self.user,
            stripe_customer_id="cus_existing_2",
        )
        payment_intent_create_mock.return_value = {
            "id": "pi_duplicate_1",
            "client_secret": "cs_duplicate_1",
        }

        first_result = create_payment_intent_for_user(
            self.user,
            operation_id="op-pay-dup",
            amount=49900,
        )
        second_result = create_payment_intent_for_user(
            self.user,
            operation_id="op-pay-dup",
            amount=49900,
        )

        self.assertTrue(first_result.created)
        self.assertFalse(second_result.created)
        self.assertEqual(first_result.payment.id, second_result.payment.id)
        self.assertEqual(first_result.client_secret, "cs_duplicate_1")
        self.assertIsNone(second_result.client_secret)
        self.assertNotIn("client_secret", first_result.payment.metadata)
        payment_intent_create_mock.assert_called_once()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.payments.stripe.PaymentIntent.create")
    def test_raises_validation_error_for_non_positive_amount(self, payment_intent_create_mock):
        with self.assertRaises(BillingValidationError):
            create_payment_intent_for_user(
                self.user,
                operation_id="op-pay-invalid",
                amount=0,
            )

        payment_intent_create_mock.assert_not_called()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.payments.stripe.PaymentIntent.create")
    def test_raises_validation_error_for_duplicate_operation_with_different_amount(
        self, payment_intent_create_mock
    ):
        BillingProfile.objects.create(
            user=self.user,
            stripe_customer_id="cus_existing_diff_amount",
        )
        Payment.objects.create(
            user=self.user,
            operation_id="op-pay-conflict",
            status=PaymentStatus.PENDING,
            amount=49900,
            currency="rub",
            stripe_customer_id="cus_existing_diff_amount",
            stripe_payment_intent_id="pi_existing_conflict",
        )

        with self.assertRaises(BillingValidationError):
            create_payment_intent_for_user(
                self.user,
                operation_id="op-pay-conflict",
                amount=39900,
            )

        payment_intent_create_mock.assert_not_called()

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.payments.stripe.PaymentIntent.create")
    def test_recovers_duplicate_operation_without_stripe_payment_intent(
        self, payment_intent_create_mock
    ):
        BillingProfile.objects.create(
            user=self.user,
            stripe_customer_id="cus_existing_recovery",
        )
        payment = Payment.objects.create(
            user=self.user,
            operation_id="op-pay-recover",
            status=PaymentStatus.PENDING,
            amount=49900,
            currency="rub",
            stripe_customer_id="cus_existing_recovery",
            stripe_payment_intent_id=None,
        )
        payment_intent_create_mock.return_value = {
            "id": "pi_recovered_1",
            "client_secret": "cs_recovered_1",
        }

        result = create_payment_intent_for_user(
            self.user,
            operation_id="op-pay-recover",
            amount=49900,
        )

        self.assertFalse(result.created)
        self.assertEqual(result.client_secret, "cs_recovered_1")
        payment.refresh_from_db()
        self.assertEqual(payment.stripe_payment_intent_id, "pi_recovered_1")
        payment_intent_create_mock.assert_called_once()
