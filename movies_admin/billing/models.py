import uuid

from django.conf import settings
from django.db import models


class PaymentStatus(models.TextChoices):
    NEW = "new", "NEW"
    PENDING = "pending", "PENDING"
    SUCCEEDED = "succeeded", "SUCCEEDED"
    FAILED = "failed", "FAILED"
    CANCELED = "canceled", "CANCELED"


class RefundStatus(models.TextChoices):
    NEW = "new", "NEW"
    PENDING = "pending", "PENDING"
    SUCCEEDED = "succeeded", "SUCCEEDED"
    FAILED = "failed", "FAILED"


class WebhookEventStatus(models.TextChoices):
    PENDING = "pending", "PENDING"
    PROCESSED = "processed", "PROCESSED"
    IGNORED = "ignored", "IGNORED"
    FAILED = "failed", "FAILED"


class BillingProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_profile",
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Stripe customer identifier for the user.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.email} billing profile"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    operation_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.NEW,
    )
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=8, default="rub")
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"payment {self.id} ({self.status})"


class Refund(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="refunds",
    )
    operation_id = models.CharField(max_length=128, unique=True)
    status = models.CharField(
        max_length=16,
        choices=RefundStatus.choices,
        default=RefundStatus.NEW,
    )
    amount = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=8, default="rub")
    reason = models.CharField(max_length=255, blank=True)
    stripe_refund_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"refund {self.id} ({self.status})"


class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16,
        choices=WebhookEventStatus.choices,
        default=WebhookEventStatus.PENDING,
    )
    payload_hash = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at",)

    def __str__(self):
        return f"{self.event_type} ({self.status})"
