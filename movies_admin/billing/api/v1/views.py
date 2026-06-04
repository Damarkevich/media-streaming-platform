import stripe
from billing.api.v1.serializers import (
    PaymentCreateResponseSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
    RefundCreateResponseSerializer,
    RefundCreateSerializer,
    RefundSerializer,
    StripeWebhookPayloadSerializer,
    StripeWebhookResponseSerializer,
)
from billing.models import Payment
from billing.services.payments import create_payment_intent_for_user
from billing.services.refunds import create_refund_for_payment
from billing.services.webhooks import process_stripe_event
from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class BillingPaymentCreateAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Create a payment",
        request=PaymentCreateSerializer,
        responses={status.HTTP_200_OK: PaymentCreateResponseSerializer},
    )
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = create_payment_intent_for_user(
            request.user,
            operation_id=serializer.validated_data["operation_id"],
            amount=serializer.validated_data["amount"],
            currency=serializer.validated_data["currency"],
        )
        payload = PaymentSerializer(result.payment).data
        payload["client_secret"] = result.client_secret
        payload["created"] = result.created
        return Response(payload, status=status.HTTP_200_OK)


class BillingPaymentDetailAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Get payment details",
        responses={status.HTTP_200_OK: PaymentSerializer},
    )
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id, user=request.user)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)


class BillingRefundCreateAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        summary="Create a refund",
        request=RefundCreateSerializer,
        responses={status.HTTP_200_OK: RefundCreateResponseSerializer},
    )
    def post(self, request):
        serializer = RefundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = get_object_or_404(
            Payment,
            pk=serializer.validated_data["payment_id"],
            user=request.user,
        )
        result = create_refund_for_payment(
            payment=payment,
            operation_id=serializer.validated_data["operation_id"],
            amount=serializer.validated_data.get("amount"),
            reason=serializer.validated_data.get("reason", ""),
        )
        payload = RefundSerializer(result.refund).data
        payload["created"] = result.created
        return Response(payload, status=status.HTTP_200_OK)


class StripeWebhookAPIView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(
        summary="Stripe webhook receiver",
        request=StripeWebhookPayloadSerializer,
        parameters=[
            OpenApiParameter(
                name="Stripe-Signature",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Stripe signature header for webhook validation.",
            )
        ],
        responses={status.HTTP_200_OK: StripeWebhookResponseSerializer},
    )
    def post(self, request):
        payload = request.body
        signature = request.headers.get("Stripe-Signature", "")

        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
        webhook_event, created = process_stripe_event(event=event, raw_payload=payload)
        return Response(
            {
                "webhook_event_id": str(webhook_event.id),
                "created": created,
                "status": webhook_event.status,
            },
            status=status.HTTP_200_OK,
        )
