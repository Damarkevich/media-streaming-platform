from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections
from django.test import TestCase
from django.test import TransactionTestCase

from accounts.models import User
from billing.models import Payment, PaymentStatus, Refund, RefundStatus, WebhookEventStatus
from billing.services.webhooks import process_stripe_event


class WebhookServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="webhook-user@example.com",
            password="secret",
        )
        self.payment = Payment.objects.create(
            user=self.user,
            operation_id="payment-webhook-op",
            status=PaymentStatus.PENDING,
            amount=49900,
            currency="rub",
            stripe_customer_id="cus_wh_1",
            stripe_payment_intent_id="pi_wh_1",
        )
        self.refund = Refund.objects.create(
            payment=self.payment,
            operation_id="refund-webhook-op",
            status=RefundStatus.PENDING,
            amount=49900,
            currency="rub",
            stripe_refund_id="re_wh_1",
        )

    def test_marks_payment_succeeded_for_payment_intent_succeeded(self):
        event = {
            "id": "evt_pay_succeeded_1",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_wh_1"}},
        }

        webhook_event, created = process_stripe_event(event=event, raw_payload=b"p1")

        self.assertTrue(created)
        self.assertEqual(webhook_event.status, WebhookEventStatus.PROCESSED)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCEEDED)

    def test_marks_refund_succeeded_for_refund_updated(self):
        event = {
            "id": "evt_ref_updated_1",
            "type": "refund.updated",
            "data": {"object": {"id": "re_wh_1", "status": "succeeded"}},
        }

        webhook_event, created = process_stripe_event(event=event, raw_payload=b"p2")

        self.assertTrue(created)
        self.assertEqual(webhook_event.status, WebhookEventStatus.PROCESSED)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.SUCCEEDED)

    def test_deduplicates_event_by_stripe_event_id(self):
        event = {
            "id": "evt_duplicate_1",
            "type": "payment_intent.payment_failed",
            "data": {"object": {"id": "pi_wh_1"}},
        }

        first_event, first_created = process_stripe_event(event=event, raw_payload=b"p3")
        second_event, second_created = process_stripe_event(event=event, raw_payload=b"p3")

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first_event.id, second_event.id)

    def test_marks_unknown_event_type_as_ignored(self):
        event = {
            "id": "evt_unknown_1",
            "type": "customer.created",
            "data": {"object": {"id": "cus_1"}},
        }

        webhook_event, created = process_stripe_event(event=event, raw_payload=b"p4")

        self.assertTrue(created)
        self.assertEqual(webhook_event.status, WebhookEventStatus.IGNORED)
        self.assertEqual(webhook_event.error_message, "Unsupported Stripe event type.")

    def test_does_not_downgrade_payment_from_succeeded_to_failed(self):
        self.payment.status = PaymentStatus.SUCCEEDED
        self.payment.save(update_fields=["status"])

        event = {
            "id": "evt_pay_failed_after_success_1",
            "type": "payment_intent.payment_failed",
            "data": {"object": {"id": "pi_wh_1"}},
        }

        webhook_event, created = process_stripe_event(event=event, raw_payload=b"p5")

        self.assertTrue(created)
        self.assertEqual(webhook_event.status, WebhookEventStatus.PROCESSED)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.SUCCEEDED)

    def test_does_not_downgrade_refund_from_succeeded_to_failed(self):
        self.refund.status = RefundStatus.SUCCEEDED
        self.refund.save(update_fields=["status"])

        event = {
            "id": "evt_ref_failed_after_success_1",
            "type": "refund.updated",
            "data": {"object": {"id": "re_wh_1", "status": "failed"}},
        }

        webhook_event, created = process_stripe_event(event=event, raw_payload=b"p6")

        self.assertTrue(created)
        self.assertEqual(webhook_event.status, WebhookEventStatus.PROCESSED)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, RefundStatus.SUCCEEDED)


class WebhookServiceConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="webhook-concurrency-user@example.com",
            password="secret",
        )
        self.payment = Payment.objects.create(
            user=self.user,
            operation_id="payment-webhook-concurrency-op",
            status=PaymentStatus.PENDING,
            amount=49900,
            currency="rub",
            stripe_customer_id="cus_wh_concurrency_1",
            stripe_payment_intent_id="pi_wh_concurrency_1",
        )

    def test_concurrent_conflicting_payment_events_keep_terminal_consistency(self):
        succeeded_event = {
            "id": "evt_pay_concurrency_succeeded_1",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_wh_concurrency_1"}},
        }
        failed_event = {
            "id": "evt_pay_concurrency_failed_1",
            "type": "payment_intent.payment_failed",
            "data": {"object": {"id": "pi_wh_concurrency_1"}},
        }

        def process(event: dict, payload: bytes):
            close_old_connections()
            try:
                return process_stripe_event(event=event, raw_payload=payload)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_succeeded = executor.submit(process, succeeded_event, b"p-concurrency-1")
            future_failed = executor.submit(process, failed_event, b"p-concurrency-2")
            succeeded_result = future_succeeded.result()
            failed_result = future_failed.result()

        self.payment.refresh_from_db()

        self.assertEqual(self.payment.status, PaymentStatus.SUCCEEDED)
        self.assertTrue(succeeded_result[1])
        self.assertTrue(failed_result[1])
