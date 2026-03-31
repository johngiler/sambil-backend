from django.db import migrations, models


def seed_catalog_flags(apps, schema_editor):
    ShoppingCenter = apps.get_model("malls", "ShoppingCenter")
    for code in ("SCC", "SLC"):
        ShoppingCenter.objects.filter(code=code).update(marketplace_catalog_enabled=True)


class Migration(migrations.Migration):

    dependencies = [
        ("malls", "0006_timestamped_active"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingcenter",
            name="marketplace_catalog_enabled",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Si el catálogo público de tomas está habilitado para este centro (reservas en marketplace).",
            ),
        ),
        migrations.RunPython(seed_catalog_flags, migrations.RunPython.noop),
    ]
