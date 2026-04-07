from django.db import migrations, models


def forwards_pending_to_active(apps, schema_editor):
    Client = apps.get_model("clients", "Client")
    Client.objects.filter(status="pending").update(status="active")


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0009_alter_client_workspace"),
    ]

    operations = [
        migrations.RunPython(forwards_pending_to_active, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="client",
            name="status",
            field=models.CharField(
                choices=[("active", "Activo"), ("suspended", "Suspendido")],
                default="active",
                max_length=20,
            ),
        ),
    ]
