import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("malls", "0011_shoppingcenter_cover_upload_to_centers"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingcenter",
            name="advertising_regulations",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Normativas de uso de tomas publicitarias (HTML o texto plano).",
            ),
        ),
        migrations.AddField(
            model_name="shoppingcenter",
            name="authorization_letter_city",
            field=models.CharField(
                blank=True,
                default="Caracas",
                help_text="Ciudad en el encabezado de fecha de la carta al municipio.",
                max_length=120,
            ),
        ),
        migrations.AddField(
            model_name="shoppingcenter",
            name="lessor_legal_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Razón social del arrendador (Constructora Sambil, C.A., etc.).",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="shoppingcenter",
            name="lessor_rif",
            field=models.CharField(
                blank=True,
                default="",
                help_text="RIF del arrendador en documentos legales.",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="shoppingcenter",
            name="municipal_authority_line",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Destinatario carta municipio, ej. «Sres. Alcaldía Municipio Chacao».",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="shoppingcenter",
            name="municipal_permit_notice",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Aviso en catálogo: el cliente debe gestionar permiso municipal.",
            ),
        ),
        migrations.CreateModel(
            name="ShoppingCenterMountingProvider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("company_name", models.CharField(max_length=255)),
                ("contact_name", models.CharField(blank=True, default="", max_length=255)),
                ("phone", models.CharField(blank=True, default="", max_length=64)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("rif", models.CharField(blank=True, default="", max_length=32)),
                ("notes", models.TextField(blank=True, default="")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "shopping_center",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mounting_providers",
                        to="malls.shoppingcenter",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
