from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


def _to_minor_units(value):
    if value is None:
        return 0
    if isinstance(value, Decimal):
        normalized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return int(normalized * 100)
    return int(value)


def forward_convert_amounts(apps, schema_editor):
    payment_model = apps.get_model("billing", "Payment")
    refund_model = apps.get_model("billing", "Refund")

    for payment in payment_model.objects.all().only("id", "amount"):
        payment.amount = _to_minor_units(payment.amount)
        payment.save(update_fields=["amount"])

    for refund in refund_model.objects.all().only("id", "amount"):
        refund.amount = _to_minor_units(refund.amount)
        refund.save(update_fields=["amount"])


def backward_convert_amounts(apps, schema_editor):
    payment_model = apps.get_model("billing", "Payment")
    refund_model = apps.get_model("billing", "Refund")

    for payment in payment_model.objects.all().only("id", "amount"):
        payment.amount = Decimal(payment.amount) / Decimal("100")
        payment.save(update_fields=["amount"])

    for refund in refund_model.objects.all().only("id", "amount"):
        refund.amount = Decimal(refund.amount) / Decimal("100")
        refund.save(update_fields=["amount"])


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_payment_refund_webhookevent"),
    ]

    operations = [
        migrations.RunPython(forward_convert_amounts, backward_convert_amounts),
        migrations.AlterField(
            model_name="payment",
            name="amount",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="refund",
            name="amount",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
