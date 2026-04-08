import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("workspaces", "0005_alter_workspace_is_active_alter_workspace_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="workspace",
            name="catalog_scc_seeded_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Si está definido, el comando seed_production_catalog ya importó tomas SCC para este owner.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="catalog_slc_seeded_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="Si está definido, el comando seed_production_catalog ya importó tomas SLC para este owner.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="workspace",
            name="catalog_seed_feeder",
            field=models.ForeignKey(
                blank=True,
                help_text="Primer usuario administrador marketplace de este workspace (referencia de carga de catálogo).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
