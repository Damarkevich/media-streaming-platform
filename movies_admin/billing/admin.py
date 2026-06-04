from django.contrib import admin

from billing.models import BillingProfile, Payment, Refund, WebhookEvent


@admin.register(BillingProfile)
class BillingProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "stripe_customer_id", "created_at", "updated_at")
    search_fields = ("user__email", "stripe_customer_id")
    list_select_related = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "amount",
        "currency",
        "stripe_payment_intent_id",
        "created_at",
    )
    search_fields = ("id", "operation_id", "stripe_payment_intent_id", "user__email")
    list_filter = ("status", "currency", "created_at")
    list_select_related = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "status",
        "amount",
        "currency",
        "stripe_refund_id",
        "created_at",
    )
    search_fields = ("id", "operation_id", "stripe_refund_id", "payment__id")
    list_filter = ("status", "currency", "created_at")
    list_select_related = ("payment",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "stripe_event_id",
        "event_type",
        "status",
        "received_at",
        "processed_at",
    )
    search_fields = ("stripe_event_id", "event_type")
    list_filter = ("status", "event_type", "received_at")
    readonly_fields = ("received_at",)
