# Rutas de media: centros bajo media/centers/covers/AÑO/MES/ (antes covers/centers/…).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("malls", "0010_shoppingcenter_slug_remove_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="shoppingcenter",
            name="cover_image",
            field=models.ImageField(
                blank=True,
                help_text="Portada del centro: media/centers/covers/AÑO/MES/ (no mezclar con tomas).",
                null=True,
                upload_to="centers/covers/%Y/%m/",
            ),
        ),
    ]
