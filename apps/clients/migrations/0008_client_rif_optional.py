from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0007_client_workspace_rif_per_workspace"),
    ]

    operations = [
        migrations.AlterField(
            model_name="client",
            name="rif",
            field=models.CharField(
                blank=True,
                help_text="Identificación fiscal; se puede completar después en Mi empresa.",
                max_length=32,
                null=True,
            ),
        ),
    ]
