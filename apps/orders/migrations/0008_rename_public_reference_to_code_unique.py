from django.db import migrations, models


def forwards_empty_to_null(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.filter(code="").update(code=None)


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_order_public_reference"),
    ]

    operations = [
        migrations.RenameField(
            model_name="order",
            old_name="public_reference",
            new_name="code",
        ),
        migrations.RunPython(forwards_empty_to_null, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Código único de pedido (#SLUG-ORDER-000001). Se asigna al crear.",
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
    ]
