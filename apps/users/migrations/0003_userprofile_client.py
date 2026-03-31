# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0004_pdf_and_catalog_fields"),
        ("users", "0002_userprofile_cover_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="client",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="member_profiles",
                to="clients.client",
            ),
        ),
    ]
