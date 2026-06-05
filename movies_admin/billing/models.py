import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentStatus(models.TextChoices):
    NEW = "new", _("New")
    PENDING = "pending", _("Pending")
    SUCCEEDED = "succeeded", _("Succeeded")
    FAILED = "failed", _("Failed")
    CANCELED = "canceled", _("Canceled")


class RefundStatus(models.TextChoices):
    NEW = "new", _("New")
    PENDING = "pending", _("Pending")
    SUCCEEDED = "succeeded", _("Succeeded")
    FAILED = "failed", _("Failed")


class WebhookEventStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSED = "processed", _("Processed")
    IGNORED = "ignored", _("Ignored")
    FAILED = "failed", _("Failed")


class ReadOnlyBillingModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *_args, **_kwargs):
        msg = (
            "Billing models are read-only in movies_admin. "
            "Use Billing API for write operations."
        )
        raise RuntimeError(msg)

    def delete(self, *_args, **_kwargs):
        msg = (
            "Billing models are read-only in movies_admin. "
            "Use Billing API for write operations."
        )
        raise RuntimeError(msg)


class BillingProfile(ReadOnlyBillingModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(verbose_name=_("user ID"), null=False)
    stripe_customer_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("Stripe customer ID")
    )
    created_at = models.DateTimeField(verbose_name=_("created at"))
    updated_at = models.DateTimeField(verbose_name=_("updated at"))

    class Meta:
        managed = False
        db_table = '"billing"."billing_profiles"'
        verbose_name = _("billing profile")
        verbose_name_plural = _("billing profiles")
        ordering: list[str] = ["-created_at"]  # noqa: RUF012

    def __str__(self) -> str:
        return f"BillingProfile({self.user_id})"


class Payment(ReadOnlyBillingModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(verbose_name=_("user ID"), null=False, db_index=True)
    operation_id = models.CharField(
        max_length=128, unique=True, verbose_name=_("operation ID")
    )
    status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        verbose_name=_("status"),
    )
    amount = models.IntegerField(verbose_name=_("amount (minor units)"))
    currency = models.CharField(max_length=8, verbose_name=_("currency"))
    stripe_customer_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("Stripe customer ID")
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("Stripe PaymentIntent ID"),
    )
    metadata_json = models.JSONField(
        db_column="metadata", default=dict, verbose_name=_("metadata")
    )
    created_at = models.DateTimeField(verbose_name=_("created at"))
    updated_at = models.DateTimeField(verbose_name=_("updated at"))

    class Meta:
        managed = False
        db_table = '"billing"."payments"'
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering: list[str] = ["-created_at"]  # noqa: RUF012

    def __str__(self) -> str:
        return f"Payment({self.operation_id}, {self.status})"

    @property
    def amount_display(self) -> str:
        """Human-readable amount: minor units → major units."""
        return f"{self.amount / 100:.2f} {self.currency.upper()}"


class Refund(ReadOnlyBillingModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.DO_NOTHING,
        db_column="payment_id",
        related_name="refunds",
        verbose_name=_("payment"),
    )
    operation_id = models.CharField(
        max_length=128, unique=True, verbose_name=_("operation ID")
    )
    status = models.CharField(
        max_length=16,
        choices=RefundStatus.choices,
        verbose_name=_("status"),
    )
    amount = models.IntegerField(verbose_name=_("amount (minor units)"))
    currency = models.CharField(max_length=8, verbose_name=_("currency"))
    reason = models.CharField(max_length=255, blank=True, verbose_name=_("reason"))
    stripe_refund_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("Stripe refund ID"),
    )
    metadata_json = models.JSONField(
        db_column="metadata", default=dict, verbose_name=_("metadata")
    )
    created_at = models.DateTimeField(verbose_name=_("created at"))
    updated_at = models.DateTimeField(verbose_name=_("updated at"))

    class Meta:
        managed = False
        db_table = '"billing"."refunds"'
        verbose_name = _("refund")
        verbose_name_plural = _("refunds")
        ordering: list[str] = ["-created_at"]  # noqa: RUF012

    def __str__(self) -> str:
        return f"Refund({self.operation_id}, {self.status})"

    @property
    def amount_display(self) -> str:
        return f"{self.amount / 100:.2f} {self.currency.upper()}"


class WebhookEvent(ReadOnlyBillingModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stripe_event_id = models.CharField(
        max_length=255, unique=True, verbose_name=_("Stripe event ID")
    )
    event_type = models.CharField(max_length=128, verbose_name=_("event type"))
    status = models.CharField(
        max_length=16,
        choices=WebhookEventStatus.choices,
        verbose_name=_("status"),
    )
    payload_hash = models.CharField(max_length=64, verbose_name=_("payload hash"))
    payload = models.JSONField(verbose_name=_("payload"))
    error_message = models.TextField(blank=True, verbose_name=_("error message"))
    received_at = models.DateTimeField(verbose_name=_("received at"))
    processed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("processed at")
    )

    class Meta:
        managed = False
        db_table = '"billing"."webhook_events"'
        verbose_name = _("webhook event")
        verbose_name_plural = _("webhook events")
        ordering: list[str] = ["-received_at"]  # noqa: RUF012

    def __str__(self) -> str:
        return f"WebhookEvent({self.stripe_event_id}, {self.event_type})"
