from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0001_initial"),
        ("users", "0003_userprofile_client"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="staff_profiles",
                to="workspaces.workspace",
                help_text="Si el usuario es admin comercial del marketplace, limita su alcance a este owner. Vacío = no aplica o operación plataforma.",
            ),
        ),
    ]
