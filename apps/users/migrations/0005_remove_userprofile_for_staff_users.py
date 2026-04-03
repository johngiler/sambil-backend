from django.db import migrations
from django.db.models import Q


def remove_profiles_for_platform_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("users", "UserProfile")
    staff_ids = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).values_list(
        "id", flat=True
    )
    UserProfile.objects.filter(user_id__in=staff_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_userprofile_workspace"),
    ]

    operations = [
        migrations.RunPython(remove_profiles_for_platform_users, migrations.RunPython.noop),
    ]
