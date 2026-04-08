from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_alter_order_status_client_approved_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Sin indicar"),
                    ("card", "Tarjeta"),
                    ("bank_transfer", "Transferencia bancaria"),
                    ("mobile_payment", "Pago móvil"),
                    ("zelle", "Zelle"),
                    ("crypto", "Cripto"),
                    ("cash", "Efectivo"),
                    ("other", "Otro"),
                ],
                db_index=True,
                default="",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_receipt",
            field=models.FileField(
                blank=True,
                help_text="Comprobante subido por el cliente en checkout.",
                null=True,
                upload_to="orders/receipts/%Y/%m/",
            ),
        ),
    ]
