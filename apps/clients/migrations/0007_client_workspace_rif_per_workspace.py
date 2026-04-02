from django.db import migrations, models


def assign_default_workspace(apps, schema_editor):
    Workspace = apps.get_model("workspaces", "Workspace")
    Client = apps.get_model("clients", "Client")
    ws, _ = Workspace.objects.get_or_create(
        slug="sambil",
        defaults={
            "name": "Sambil",
            "marketplace_title": "Sambil Marketplace",
            "is_active": True,
        },
    )
    Client.objects.filter(workspace_id__isnull=True).update(workspace_id=ws.id)


class Migration(migrations.Migration):

    dependencies = [
        ("clients", "0006_timestamped_active"),
        ("malls", "0008_shoppingcenter_workspace"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="workspace",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="clients",
                to="workspaces.workspace",
                help_text="Tenant al que pertenece la empresa cliente (RIF único por workspace).",
            ),
        ),
        migrations.RunPython(assign_default_workspace, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="client",
            name="rif",
            field=models.CharField(max_length=32),
        ),
        migrations.AddConstraint(
            model_name="client",
            constraint=models.UniqueConstraint(
                fields=("workspace", "rif"),
                name="clients_client_workspace_rif_uniq",
            ),
        ),
        migrations.AlterField(
            model_name="client",
            name="workspace",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="clients",
                to="workspaces.workspace",
                help_text="Tenant al que pertenece la empresa cliente (RIF único por workspace).",
            ),
        ),
    ]
