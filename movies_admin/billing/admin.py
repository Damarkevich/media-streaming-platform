import logging
from uuid import uuid4

import httpx
from django.conf import settings
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import BillingProfile, Payment, Refund, WebhookEvent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status badge helpers
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "new": "#6c757d",
    "pending": "#fd7e14",
    "succeeded": "#198754",
    "failed": "#dc3545",
    "canceled": "#adb5bd",
    "processed": "#198754",
    "ignored": "#6c757d",
}


def _status_badge(status: str) -> str:
    color = _STATUS_COLORS.get(status, "#6c757d")
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px;'
        'font-size:11px;font-weight:600">{}</span>',
        color,
        status,
    )


# ---------------------------------------------------------------------------
# Billing Profile
# ---------------------------------------------------------------------------


@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ("user_id", "stripe_customer_id", "created_at", "updated_at")
    search_fields = ("user_id__iexact", "stripe_customer_id")
    readonly_fields = (
        "id",
        "user_id",
        "stripe_customer_id",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False


# ---------------------------------------------------------------------------
# Refund (inline + standalone)
# ---------------------------------------------------------------------------


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    can_delete = False
    show_change_link = True
    fields = (
        "id",
        "operation_id",
        "status_badge",
        "amount_display",
        "currency",
        "reason",
        "stripe_refund_id",
        "created_at",
    )
    readonly_fields = (
        "id",
        "operation_id",
        "status_badge",
        "amount_display",
        "currency",
        "reason",
        "stripe_refund_id",
        "created_at",
    )

    @admin.display(description=_("status"))
    def status_badge(self, obj):
        return _status_badge(obj.status)

    @admin.display(description=_("amount"))
    def amount_display(self, obj):
        return obj.amount_display

    def has_add_permission(self, request, obj=None):  # noqa: ARG002
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "operation_id",
        "status_badge",
        "amount_display",
        "currency",
        "reason",
        "stripe_refund_id",
        "created_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = ("operation_id", "stripe_refund_id", "payment__operation_id")
    readonly_fields = (
        "id",
        "payment",
        "operation_id",
        "status",
        "amount",
        "currency",
        "reason",
        "stripe_refund_id",
        "metadata_json",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    @admin.display(description=_("status"))
    def status_badge(self, obj):
        return _status_badge(obj.status)

    @admin.display(description=_("amount"))
    def amount_display(self, obj):
        return obj.amount_display

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


def _initiate_full_refund(modeladmin, request, queryset):
    """Admin action: initiate a full refund for each selected succeeded payment."""
    billing_url = getattr(settings, "BILLING_SERVICE_URL", "http://movies-billing:8010")
    succeeded_count = 0
    for payment in queryset:
        if payment.status != "succeeded":
            modeladmin.message_user(
                request,
                _(
                    "Payment %(id)s skipped — only succeeded payments can be refunded "
                    "(current status: %(status)s)."
                )
                % {"id": payment.id, "status": payment.status},
            )
            continue

        operation_id = f"admin-refund:{payment.id}:{uuid4()}"
        try:
            resp = httpx.post(
                f"{billing_url}/api/v1/billing/refunds/create",
                json={
                    "payment_id": str(payment.id),
                    "operation_id": operation_id,
                    "reason": "admin_initiated",
                },
                headers={"X-User-Id": str(payment.user_id)},
                timeout=10.0,
            )
            resp.raise_for_status()
            succeeded_count += 1
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Billing refund request failed",
                extra={
                    "payment_id": str(payment.id),
                    "status_code": exc.response.status_code,
                    "response_text": exc.response.text,
                },
            )
            modeladmin.message_user(
                request,
                _("Payment %(id)s: refund failed in billing service.")
                % {"id": payment.id},
                level=messages.ERROR,
            )
        except httpx.RequestError:
            logger.warning(
                "Billing service is unavailable for refund request",
                extra={"payment_id": str(payment.id)},
                exc_info=True,
            )
            modeladmin.message_user(
                request,
                _("Payment %(id)s: billing service is temporarily unavailable.")
                % {"id": payment.id},
                level=messages.ERROR,
            )

    if succeeded_count:
        modeladmin.message_user(
            request,
            _("%(count)d refund(s) initiated successfully.")
            % {"count": succeeded_count},
            level=messages.SUCCESS,
        )


_initiate_full_refund.short_description = _("Initiate full refund")  # type: ignore[attr-defined]
_initiate_full_refund.allowed_permissions = ("view",)  # type: ignore[attr-defined]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_id",
        "operation_id",
        "status_badge",
        "amount_display",
        "currency",
        "stripe_payment_intent_id",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "currency", "created_at")
    search_fields = (
        "user_id__iexact",
        "operation_id",
        "stripe_payment_intent_id",
        "stripe_customer_id",
    )
    readonly_fields = (
        "id",
        "user_id",
        "operation_id",
        "status",
        "amount",
        "currency",
        "stripe_customer_id",
        "stripe_payment_intent_id",
        "metadata_json",
        "created_at",
        "updated_at",
    )
    inlines = (RefundInline,)
    actions = (_initiate_full_refund,)
    ordering = ("-created_at",)

    @admin.display(description=_("status"))
    def status_badge(self, obj):
        return _status_badge(obj.status)

    @admin.display(description=_("amount"))
    def amount_display(self, obj):
        return obj.amount_display

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False


# ---------------------------------------------------------------------------
# Webhook Event
# ---------------------------------------------------------------------------


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "stripe_event_id",
        "event_type",
        "status_badge",
        "error_message",
        "received_at",
        "processed_at",
    )
    list_filter = ("status", "event_type", "received_at")
    search_fields = ("stripe_event_id", "event_type")
    readonly_fields = (
        "id",
        "stripe_event_id",
        "event_type",
        "status",
        "payload_hash",
        "payload",
        "error_message",
        "received_at",
        "processed_at",
    )
    ordering = ("-received_at",)

    @admin.display(description=_("status"))
    def status_badge(self, obj):
        return _status_badge(obj.status)

    def has_add_permission(self, request):  # noqa: ARG002
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002
        return False
