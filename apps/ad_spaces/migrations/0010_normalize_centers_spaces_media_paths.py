# Rutas de media: tomas bajo media/spaces/{gallery|covers}/AÑO/MES/ (portada antes covers/spaces/…).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ad_spaces", "0009_alter_adspace_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adspace",
            name="cover_image",
            field=models.ImageField(
                blank=True,
                help_text="Copia de la primera imagen de galería; media/spaces/covers/AÑO/MES/ (la galería va en spaces/gallery/…).",
                null=True,
                upload_to="spaces/covers/%Y/%m/",
            ),
        ),
        migrations.AlterField(
            model_name="adspaceimage",
            name="image",
            field=models.ImageField(
                help_text="Galería de la toma: media/spaces/gallery/AÑO/MES/ (misma familia «spaces» que portada).",
                upload_to="spaces/gallery/%Y/%m/",
            ),
        ),
    ]
