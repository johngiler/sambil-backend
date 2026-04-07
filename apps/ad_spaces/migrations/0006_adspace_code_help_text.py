from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ad_spaces", "0005_ad_space_status_verbose_es"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adspace",
            name="code",
            field=models.CharField(
                db_index=True,
                help_text="Nomenclatura: {código_centro}-T{número}[sufijo]. Ej. SCC-T1, SLC-T1A.",
                max_length=32,
                unique=True,
            ),
        ),
    ]
