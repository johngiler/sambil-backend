from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0003_workspace_branding_verbose_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="phone",
            field=models.CharField(
                blank=True,
                help_text="Contacto telefónico público del operador (opcional).",
                max_length=32,
                verbose_name="Teléfono",
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="country",
            field=models.CharField(
                blank=True,
                help_text="País de la sede o operación del owner (opcional).",
                max_length=120,
                verbose_name="País",
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="city",
            field=models.CharField(
                blank=True,
                help_text="Ciudad de la sede o operación del owner (opcional).",
                max_length=120,
                verbose_name="Ciudad",
            ),
        ),
    ]
