# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_orderartattachment_order_item"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderinstallationpermit",
            name="request_pdf",
            field=models.FileField(
                blank=True,
                help_text="PDF generado al enviar la solicitud (correo / expediente interno).",
                null=True,
                upload_to="orders/installation_permits/%Y/%m/",
            ),
        ),
    ]
