from billing.api.v1.views import (
    BillingPaymentCreateAPIView,
    BillingPaymentDetailAPIView,
    BillingRefundCreateAPIView,
    StripeWebhookAPIView,
)
from django.urls import path

urlpatterns = [
    path(
        "payments/create",
        BillingPaymentCreateAPIView.as_view(),
        name="billing-payment-create",
    ),
    path(
        "payments/<uuid:payment_id>",
        BillingPaymentDetailAPIView.as_view(),
        name="billing-payment-detail",
    ),
    path(
        "refunds/create",
        BillingRefundCreateAPIView.as_view(),
        name="billing-refund-create",
    ),
    path(
        "webhooks/stripe", StripeWebhookAPIView.as_view(), name="billing-stripe-webhook"
    ),
]
