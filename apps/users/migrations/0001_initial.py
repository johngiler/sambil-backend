import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_profiles_for_existing_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("users", "UserProfile")
    db_alias = schema_editor.connection.alias
    for u in User.objects.using(db_alias).iterator():
        role = "admin" if (u.is_superuser or u.is_staff) else "client"
        UserProfile.objects.using(db_alias).get_or_create(
            user_id=u.pk,
            defaults={"role": role},
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[("admin", "Administrador"), ("client", "Cliente marketplace")],
                        db_index=True,
                        default="client",
                        max_length=16,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["user_id"],
            },
        ),
        migrations.RunPython(create_profiles_for_existing_users, migrations.RunPython.noop),
    ]
