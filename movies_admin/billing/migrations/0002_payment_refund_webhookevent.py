# Generated manually for billing payment, refund, and webhook models.

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("operation_id", models.CharField(max_length=128, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "NEW"),
                            ("pending", "PENDING"),
                            ("succeeded", "SUCCEEDED"),
                            ("failed", "FAILED"),
                            ("canceled", "CANCELED"),
                        ],
                        default="new",
                        max_length=16,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="rub", max_length=8)),
                ("stripe_customer_id", models.CharField(blank=True, max_length=255, null=True)),
                (
                    "stripe_payment_intent_id",
                    models.CharField(blank=True, max_length=255, null=True, unique=True),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="WebhookEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("stripe_event_id", models.CharField(max_length=255, unique=True)),
                ("event_type", models.CharField(max_length=128)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "PENDING"),
                            ("processed", "PROCESSED"),
                            ("ignored", "IGNORED"),
                            ("failed", "FAILED"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("payload_hash", models.CharField(max_length=64)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ("-received_at",)},
        ),
        migrations.CreateModel(
            name="Refund",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("operation_id", models.CharField(max_length=128, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "NEW"),
                            ("pending", "PENDING"),
                            ("succeeded", "SUCCEEDED"),
                            ("failed", "FAILED"),
                        ],
                        default="new",
                        max_length=16,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="rub", max_length=8)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("stripe_refund_id", models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refunds",
                        to="billing.payment",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
