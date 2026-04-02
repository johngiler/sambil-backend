from django.db import migrations, models


def create_default_workspace_and_assign(apps, schema_editor):
    Workspace = apps.get_model("workspaces", "Workspace")
    ShoppingCenter = apps.get_model("malls", "ShoppingCenter")
    ws, _ = Workspace.objects.get_or_create(
        slug="sambil",
        defaults={
            "name": "Sambil",
            "marketplace_title": "Sambil Marketplace",
            "is_active": True,
        },
    )
    ShoppingCenter.objects.filter(workspace_id__isnull=True).update(workspace_id=ws.id)


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0001_initial"),
        ("malls", "0007_marketplace_catalog_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingcenter",
            name="workspace",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.CASCADE,
                related_name="shopping_centers",
                to="workspaces.workspace",
                help_text="Owner / tenant al que pertenece este centro comercial.",
            ),
        ),
        migrations.RunPython(create_default_workspace_and_assign, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="shoppingcenter",
            name="workspace",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="shopping_centers",
                to="workspaces.workspace",
                help_text="Owner / tenant al que pertenece este centro comercial.",
            ),
        ),
    ]
