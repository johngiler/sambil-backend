# Unifica «rechazada» en «cancelada» y elimina el valor de estado en el modelo.

from django.db import migrations, models


def forwards_coalesce_rejected(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    OrderStatusEvent = apps.get_model("orders", "OrderStatusEvent")
    Order.objects.filter(status="rejected").update(status="cancelled")
    OrderStatusEvent.objects.filter(to_status="rejected").update(to_status="cancelled")
    OrderStatusEvent.objects.filter(from_status="rejected").update(from_status="cancelled")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0012_orderinstallationpermit_request_pdf"),
    ]

    operations = [
        migrations.RunPython(forwards_coalesce_rejected, noop_reverse),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Borrador"),
                    ("submitted", "Enviada"),
                    ("client_approved", "Solicitud aprobada"),
                    ("invoiced", "Facturada"),
                    ("paid", "Pagada"),
                    ("art_approved", "Arte aprobado"),
                    ("permit_pending", "Permiso alcaldía"),
                    ("installation", "Instalación"),
                    ("active", "Activa"),
                    ("expired", "Vencida"),
                    ("cancelled", "Cancelada"),
                ],
                default="draft",
                max_length=32,
            ),
        ),
    ]
