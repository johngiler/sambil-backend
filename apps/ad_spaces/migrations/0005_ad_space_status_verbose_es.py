from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ad_spaces", "0004_timestamped_active"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adspace",
            name="status",
            field=models.CharField(
                choices=[
                    ("available", "Disponible"),
                    ("reserved", "Reservado"),
                    ("occupied", "Ocupado"),
                    ("blocked", "Bloqueado"),
                ],
                default="available",
                max_length=20,
            ),
        ),
    ]
