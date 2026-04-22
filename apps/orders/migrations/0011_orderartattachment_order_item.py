# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def backfill_art_order_item(apps, schema_editor):
    OrderArtAttachment = apps.get_model("orders", "OrderArtAttachment")
    OrderItem = apps.get_model("orders", "OrderItem")
    for att in OrderArtAttachment.objects.filter(order_item__isnull=True).iterator():
        items = list(OrderItem.objects.filter(order_id=att.order_id).order_by("id"))
        if len(items) == 1:
            OrderArtAttachment.objects.filter(pk=att.pk).update(order_item_id=items[0].pk)


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_alter_orderartattachment_created_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderartattachment",
            name="order_item",
            field=models.ForeignKey(
                blank=True,
                help_text="Línea del pedido (toma) a la que aplica el archivo; obligatorio si el pedido tiene varias líneas.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="art_attachments",
                to="orders.orderitem",
            ),
        ),
        migrations.RunPython(backfill_art_order_item, migrations.RunPython.noop),
    ]
