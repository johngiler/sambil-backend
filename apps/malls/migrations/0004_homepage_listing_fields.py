# Generated manually for homepage catalog fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("malls", "0003_pdf_and_catalog_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingcenter",
            name="district",
            field=models.CharField(
                blank=True,
                help_text="Zona o urbanización para el titular de la tarjeta en portada (ej. Chacao).",
                max_length=120,
            ),
        ),
        migrations.AddField(
            model_name="shoppingcenter",
            name="on_homepage",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="Si se lista en la portada del marketplace.",
            ),
        ),
        migrations.AddField(
            model_name="shoppingcenter",
            name="listing_order",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Orden en portada (menor primero).",
            ),
        ),
        migrations.AlterModelOptions(
            name="shoppingcenter",
            options={"ordering": ["listing_order", "code"]},
        ),
    ]
