# Generated manually for gallery images per toma.

from django.db import migrations, models
import django.db.models.deletion


def forwards_copy_cover_to_gallery(apps, schema_editor):
    AdSpace = apps.get_model("ad_spaces", "AdSpace")
    AdSpaceImage = apps.get_model("ad_spaces", "AdSpaceImage")
    for ad in AdSpace.objects.exclude(cover_image="").iterator():
        AdSpaceImage.objects.create(ad_space=ad, image=ad.cover_image, sort_order=0)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ad_spaces", "0006_adspace_code_help_text"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdSpaceImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="spaces/gallery/%Y/%m/")),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                (
                    "ad_space",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gallery_images",
                        to="ad_spaces.adspace",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.RunPython(forwards_copy_cover_to_gallery, backwards_noop),
    ]
