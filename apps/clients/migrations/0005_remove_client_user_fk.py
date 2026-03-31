# Migra Client.user -> UserProfile.client y elimina el OneToOne en Client.

from django.db import migrations


def copy_client_user_to_profile(apps, schema_editor):
    Client = apps.get_model("clients", "Client")
    UserProfile = apps.get_model("users", "UserProfile")
    for c in Client.objects.exclude(user_id=None):
        UserProfile.objects.filter(user_id=c.user_id).update(client_id=c.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0004_pdf_and_catalog_fields"),
        ("users", "0003_userprofile_client"),
    ]

    operations = [
        migrations.RunPython(copy_client_user_to_profile, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="client",
            name="user",
        ),
    ]
