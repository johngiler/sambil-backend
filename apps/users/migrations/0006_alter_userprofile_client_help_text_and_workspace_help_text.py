from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0007_client_workspace_rif_per_workspace"),
        ("users", "0005_remove_userprofile_for_staff_users"),
        ("workspaces", "0003_workspace_branding_verbose_labels"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="client",
            field=models.ForeignKey(
                blank=True,
                help_text="Obligatorio si el rol es cliente marketplace (misma empresa que el usuario).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="member_profiles",
                to="clients.client",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                help_text="Administrador marketplace: obligatorio (owner del panel). "
                "Cliente marketplace: obligatorio y debe ser el workspace de la empresa vinculada.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="staff_profiles",
                to="workspaces.workspace",
            ),
        ),
    ]
