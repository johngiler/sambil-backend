from django.core.validators import FileExtensionValidator
from django.db import migrations, models

_brand_validators = [
    FileExtensionValidator(
        allowed_extensions=["svg", "png", "jpg", "jpeg", "gif", "webp"],
        message="Formato no admitido. Usa SVG, PNG, JPEG, GIF o WebP.",
    )
]

_favicon_validators = [
    FileExtensionValidator(
        allowed_extensions=["svg", "png", "jpg", "jpeg", "gif", "webp", "ico"],
        message="Formato no admitido. Usa SVG, PNG, ICO, JPEG, GIF o WebP.",
    )
]


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workspace",
            name="logo",
            field=models.FileField(
                blank=True,
                help_text="Logo principal (marketplace / emails). SVG, PNG, JPEG, GIF o WebP.",
                null=True,
                upload_to="workspaces/logos/%Y/%m/",
                validators=_brand_validators,
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="logo_mark",
            field=models.FileField(
                blank=True,
                help_text="Isotipo o marca reducida (header compacto). SVG, PNG, JPEG, GIF o WebP.",
                null=True,
                upload_to="workspaces/logo_marks/%Y/%m/",
                validators=_brand_validators,
            ),
        ),
        migrations.AlterField(
            model_name="workspace",
            name="favicon",
            field=models.FileField(
                blank=True,
                help_text="Favicon. SVG, PNG, ICO, JPEG, GIF o WebP.",
                null=True,
                upload_to="workspaces/favicons/%Y/%m/",
                validators=_favicon_validators,
            ),
        ),
    ]
