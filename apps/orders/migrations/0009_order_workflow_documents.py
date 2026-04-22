import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0008_rename_public_reference_to_code_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="installation_verified_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Cuando mercadeo del CC validó la instalación conforme.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="invoice_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Número o referencia de factura (opcional, en PDF).",
                max_length=64,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="invoice_pdf",
            field=models.FileField(
                blank=True,
                help_text="Factura PDF generada al marcar como facturada.",
                null=True,
                upload_to="orders/generated/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="municipality_authorization_pdf",
            field=models.FileField(
                blank=True,
                help_text="Carta de autorización para trámite en alcaldía.",
                null=True,
                upload_to="orders/generated/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="negotiation_observations",
            field=models.TextField(blank=True, default="", help_text="Observaciones en hoja de negociación (líneas del pedido, texto libre)."),
        ),
        migrations.AddField(
            model_name="order",
            name="negotiation_sheet_pdf",
            field=models.FileField(
                blank=True,
                help_text="Hoja de negociación generada al aprobar la solicitud.",
                null=True,
                upload_to="orders/generated/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="negotiation_sheet_signed",
            field=models.FileField(
                blank=True,
                help_text="Hoja de negociación firmada por el cliente.",
                null=True,
                upload_to="orders/signed/%Y/%m/",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_conditions",
            field=models.TextField(blank=True, default="", help_text="Condiciones de pago (hoja de negociación)."),
        ),
        migrations.CreateModel(
            name="OrderArtAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("file", models.FileField(upload_to="orders/arts/%Y/%m/")),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="art_attachments",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.CreateModel(
            name="OrderInstallationPermit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("mounting_date", models.DateField()),
                ("installation_company_name", models.CharField(max_length=255)),
                (
                    "staff_members",
                    models.JSONField(
                        default=list,
                        help_text='Lista: [{"full_name": "...", "id_number": "V-12345678"}]',
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
                ("municipal_reference", models.CharField(blank=True, default="", help_text="Referencia o expediente municipal si aplica.", max_length=255)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="installation_permit",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
