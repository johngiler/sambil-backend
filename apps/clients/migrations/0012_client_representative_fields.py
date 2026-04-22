from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0011_clientadspacefavorite"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="representative_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Representante legal o firmante (hoja de negociación, cartas).",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="representative_id_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Cédula de identidad del representante (ej. V-17.311.805).",
                max_length=32,
            ),
        ),
    ]
