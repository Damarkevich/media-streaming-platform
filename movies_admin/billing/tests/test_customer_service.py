from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings

from accounts.models import User
from billing.models import BillingProfile
from billing.services import create_or_get_customer_for_user


class CreateOrGetCustomerServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="billing-user@example.com",
            password="secret",
        )

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.customers.stripe.Customer.create")
    def test_creates_customer_and_profile_when_missing(self, create_customer_mock):
        create_customer_mock.return_value = {"id": "cus_test_123"}

        profile, created = create_or_get_customer_for_user(
            self.user,
            operation_id="op-test-1",
        )

        self.assertTrue(created)
        self.assertEqual(profile.stripe_customer_id, "cus_test_123")
        create_customer_mock.assert_called_once()

    @patch("billing.services.customers.stripe.Customer.create")
    def test_returns_existing_customer_without_stripe_call(self, create_customer_mock):
        existing_profile = BillingProfile.objects.create(
            user=self.user,
            stripe_customer_id="cus_existing_1",
        )

        profile, created = create_or_get_customer_for_user(self.user)

        self.assertFalse(created)
        self.assertEqual(profile.id, existing_profile.id)
        self.assertEqual(profile.stripe_customer_id, "cus_existing_1")
        create_customer_mock.assert_not_called()

    @patch("billing.services.customers.stripe.Customer.create")
    def test_raises_when_secret_key_missing(self, create_customer_mock):
        with self.assertRaises(ImproperlyConfigured):
            create_or_get_customer_for_user(self.user)

        create_customer_mock.assert_not_called()


class CreateOrGetCustomerConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="billing-concurrency@example.com",
            password="secret",
        )

    @override_settings(STRIPE_SECRET_KEY="sk_test_123")
    @patch("billing.services.customers.stripe.Customer.create")
    def test_concurrent_first_requests_create_single_stripe_customer(
        self,
        create_customer_mock,
    ):
        create_customer_mock.return_value = {"id": "cus_concurrent_1"}

        def call_service(operation_id: str):
            close_old_connections()
            try:
                user = User.objects.get(pk=self.user.pk)
                return create_or_get_customer_for_user(user, operation_id=operation_id)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(call_service, "op-concurrent-1"),
                executor.submit(call_service, "op-concurrent-2"),
            ]
            results = [future.result() for future in futures]

        profiles = [profile for profile, _ in results]
        created_flags = [created for _, created in results]

        self.assertEqual(profiles[0].stripe_customer_id, "cus_concurrent_1")
        self.assertEqual(profiles[1].stripe_customer_id, "cus_concurrent_1")
        self.assertEqual(sum(created_flags), 1)
        create_customer_mock.assert_called_once()
