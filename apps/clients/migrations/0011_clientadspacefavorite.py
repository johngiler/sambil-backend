import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ad_spaces", "0009_alter_adspace_code"),
        ("clients", "0010_client_status_active_suspended_only"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientAdSpaceFavorite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Si está desmarcado, el registro se considera inactivo (no borrado).",
                    ),
                ),
                (
                    "ad_space",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_favorites",
                        to="ad_spaces.adspace",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ad_space_favorites",
                        to="clients.client",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="clientadspacefavorite",
            constraint=models.UniqueConstraint(
                fields=("client", "ad_space"),
                name="clients_favorite_client_ad_space_uniq",
            ),
        ),
    ]
