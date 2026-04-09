from django.db import migrations, models


def forwards_fill_public_reference(apps, schema_editor):
    from apps.orders.references import format_order_public_reference

    Order = apps.get_model("orders", "Order")
    Client = apps.get_model("clients", "Client")
    for o in Order.objects.all().order_by("id").iterator():
        if (o.public_reference or "").strip():
            continue
        slug = ""
        if o.client_id:
            try:
                c = Client.objects.select_related("workspace").get(pk=o.client_id)
                if c.workspace_id:
                    slug = c.workspace.slug or ""
            except Client.DoesNotExist:
                pass
        ref = format_order_public_reference(o.pk, slug)
        Order.objects.filter(pk=o.pk).update(public_reference=ref)


def backwards_clear(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.all().update(public_reference="")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0006_order_payment_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="public_reference",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Referencia fija para UI y soporte (#SLUG-ORDER-000001). Se asigna al crear el pedido.",
                max_length=64,
            ),
        ),
        migrations.RunPython(forwards_fill_public_reference, backwards_clear),
    ]
