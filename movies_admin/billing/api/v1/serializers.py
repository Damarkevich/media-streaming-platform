from billing.models import Payment, Refund
from rest_framework import serializers


class PaymentCreateSerializer(serializers.Serializer):
    operation_id = serializers.CharField(max_length=128)
    amount = serializers.IntegerField(
        min_value=1,
        help_text="Amount in minor units (kopecks/cents). Example: 49900 means 499.00.",
    )
    currency = serializers.CharField(max_length=8, default="rub")


class PaymentSerializer(serializers.ModelSerializer):
    client_secret = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "operation_id",
            "status",
            "amount",
            "currency",
            "stripe_payment_intent_id",
            "client_secret",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_client_secret(self, obj: Payment) -> str | None:
        return getattr(obj, "client_secret", None)


class PaymentCreateResponseSerializer(serializers.ModelSerializer):
    created = serializers.BooleanField(read_only=True)
    client_secret = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = (
            "id",
            "operation_id",
            "status",
            "amount",
            "currency",
            "stripe_payment_intent_id",
            "client_secret",
            "created_at",
            "updated_at",
            "created",
        )
        read_only_fields = fields

    def get_client_secret(self, obj: Payment) -> str | None:
        return getattr(obj, "client_secret", None)


class RefundCreateSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField()
    operation_id = serializers.CharField(max_length=128)
    amount = serializers.IntegerField(
        min_value=1,
        required=False,
        help_text="Refund amount in minor units (kopecks/cents). If omitted, full payment amount is used.",
    )
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = (
            "id",
            "payment",
            "operation_id",
            "status",
            "amount",
            "currency",
            "reason",
            "stripe_refund_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class RefundCreateResponseSerializer(serializers.ModelSerializer):
    created = serializers.BooleanField(read_only=True)

    class Meta:
        model = Refund
        fields = (
            "id",
            "payment",
            "operation_id",
            "status",
            "amount",
            "currency",
            "reason",
            "stripe_refund_id",
            "created_at",
            "updated_at",
            "created",
        )
        read_only_fields = fields


class StripeWebhookPayloadSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    type = serializers.CharField(required=False)
    data = serializers.JSONField(required=False)


class StripeWebhookResponseSerializer(serializers.Serializer):
    webhook_event_id = serializers.UUIDField()
    created = serializers.BooleanField()
    status = serializers.CharField()
