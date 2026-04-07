from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_timestamped_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Borrador"),
                    ("submitted", "Enviada"),
                    ("client_approved", "Solicitud aprobada"),
                    ("art_approved", "Arte aprobado"),
                    ("invoiced", "Facturada"),
                    ("paid", "Pagada"),
                    ("permit_pending", "Permiso alcaldía"),
                    ("installation", "Instalación"),
                    ("active", "Activa"),
                    ("expired", "Vencida"),
                    ("cancelled", "Cancelada"),
                    ("rejected", "Rechazada"),
                ],
                default="draft",
                max_length=32,
            ),
        ),
    ]
