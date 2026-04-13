from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workspaces", "0006_workspace_catalog_seed_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="can_create_shopping_centers",
            field=models.BooleanField(
                default=True,
                help_text="Si está desactivado, el panel no permite crear CCs (API y UI).",
                verbose_name="Puede crear centros comerciales",
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="can_create_ad_spaces",
            field=models.BooleanField(
                default=True,
                help_text="Si está desactivado, el panel no permite crear tomas / espacios publicitarios.",
                verbose_name="Puede crear tomas",
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="can_create_marketplace_admin_users",
            field=models.BooleanField(
                default=True,
                help_text="Si está desactivado, no se pueden crear ni promover usuarios con rol administrador del panel.",
                verbose_name="Puede crear administradores marketplace",
            ),
        ),
    ]
