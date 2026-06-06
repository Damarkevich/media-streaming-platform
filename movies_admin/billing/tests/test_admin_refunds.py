from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import httpx
from django.contrib import admin
from django.contrib.messages import constants as msg
from django.test import RequestFactory, SimpleTestCase

from billing.admin import PaymentAdmin, _initiate_full_refund
from billing.models import Payment


class BillingAdminActionTests(SimpleTestCase):
    def setUp(self):
        self.site = admin.sites.AdminSite()
        self.payment_admin = PaymentAdmin(Payment, self.site)
        self.request = RequestFactory().get("/admin/billing/payment/")

    def test_refund_action_available_with_view_permission(self):
        with (
            patch.object(
                self.payment_admin,
                "has_view_permission",
                return_value=True,
            ),
            patch.object(
                self.payment_admin,
                "has_change_permission",
                return_value=False,
            ),
        ):
            actions = self.payment_admin.get_actions(self.request)

        assert "_initiate_full_refund" in actions

    def test_refund_action_hidden_without_view_permission(self):
        with patch.object(
            self.payment_admin,
            "has_view_permission",
            return_value=False,
        ):
            actions = self.payment_admin.get_actions(self.request)

        assert "_initiate_full_refund" not in actions


class BillingAdminRefundMessageSafetyTests(SimpleTestCase):
    def setUp(self):
        self.model_admin = MagicMock()
        self.request = RequestFactory().post("/admin/billing/payment/")
        self.payment = SimpleNamespace(
            id=uuid4(),
            status="succeeded",
            user_id=uuid4(),
        )

    def test_http_status_error_shows_safe_message_only(self):
        response = httpx.Response(
            status_code=500,
            text='{"detail":"secret-token"}',
            request=httpx.Request("POST", "http://billing/api/v1/billing/refunds/create"),
        )
        error = httpx.HTTPStatusError(
            "Internal Server Error",
            request=response.request,
            response=response,
        )

        with patch("billing.admin.httpx.post", side_effect=error):
            _initiate_full_refund(self.model_admin, self.request, [self.payment])

        self.model_admin.message_user.assert_called_once()
        call = self.model_admin.message_user.call_args
        message_text = call.args[1]
        level = call.kwargs["level"]

        assert level == msg.ERROR
        assert "refund failed in billing service" in str(message_text).lower()
        assert "secret-token" not in str(message_text)

    def test_request_error_shows_safe_message_only(self):
        request = httpx.Request("POST", "http://billing/api/v1/billing/refunds/create")
        error = httpx.RequestError("Connection reset by peer", request=request)

        with patch("billing.admin.httpx.post", side_effect=error):
            _initiate_full_refund(self.model_admin, self.request, [self.payment])

        self.model_admin.message_user.assert_called_once()
        call = self.model_admin.message_user.call_args
        message_text = call.args[1]
        level = call.kwargs["level"]

        assert level == msg.ERROR
        assert "temporarily unavailable" in str(message_text).lower()
        assert "Connection reset by peer" not in str(message_text)


class BillingAdminRefundOperationIdTests(SimpleTestCase):
    def setUp(self):
        self.model_admin = MagicMock()
        self.request = RequestFactory().post("/admin/billing/payment/")
        self.payment = SimpleNamespace(
            id=uuid4(),
            status="succeeded",
            user_id=uuid4(),
        )

    def test_operation_id_is_unique_per_attempt(self):
        response = MagicMock()
        response.raise_for_status.return_value = None

        with patch("billing.admin.httpx.post", return_value=response) as post_mock:
            _initiate_full_refund(
                self.model_admin,
                self.request,
                [self.payment, self.payment],
            )

        operation_ids = [call.kwargs["json"]["operation_id"] for call in post_mock.call_args_list]
        expected_prefix = f"admin-refund:{self.payment.id}:"

        assert len(operation_ids) == 2
        assert operation_ids[0].startswith(expected_prefix)
        assert operation_ids[1].startswith(expected_prefix)
        assert operation_ids[0] != operation_ids[1]


class BillingModelsReadOnlyTests(SimpleTestCase):
    def test_payment_save_raises_runtime_error(self):
        payment = Payment()

        with self.assertRaises(RuntimeError) as exc:  # noqa: PT027
            payment.save()

        assert "read-only" in str(exc.exception).lower()

    def test_payment_delete_raises_runtime_error(self):
        payment = Payment()

        with self.assertRaises(RuntimeError) as exc:  # noqa: PT027
            payment.delete()

        assert "read-only" in str(exc.exception).lower()
