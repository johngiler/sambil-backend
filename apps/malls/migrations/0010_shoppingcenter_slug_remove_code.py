from django.db import migrations, models
from django.utils.text import slugify


def fill_slugs_from_legacy_code(apps, schema_editor):
    ShoppingCenter = apps.get_model("malls", "ShoppingCenter")
    for sc in ShoppingCenter.objects.order_by("id"):
        raw = (getattr(sc, "code", None) or "").strip()
        base = slugify(raw.lower()) if raw else ""
        if not base:
            base = slugify((sc.name or "").strip()) or f"centro-{sc.pk}"
        base = base[:80]
        slug = base
        n = 0
        while (
            ShoppingCenter.objects.filter(workspace_id=sc.workspace_id, slug=slug)
            .exclude(pk=sc.pk)
            .exists()
        ):
            n += 1
            suffix = f"-{n}"
            slug = (base[: 80 - len(suffix)] + suffix)[:80]
        sc.slug = slug
        sc.save(update_fields=["slug"])


class Migration(migrations.Migration):
    dependencies = [
        ("malls", "0009_alter_shoppingcenter_listing_order_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="shoppingcenter",
            name="slug",
            field=models.SlugField(blank=True, max_length=80, null=True),
        ),
        migrations.RunPython(fill_slugs_from_legacy_code, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="shoppingcenter",
            name="code",
        ),
        migrations.AlterField(
            model_name="shoppingcenter",
            name="slug",
            field=models.SlugField(
                max_length=80,
                help_text="Identificador en URL pública (?center=, detalle /api/catalog/centers/{slug}/). Único por workspace.",
            ),
        ),
        migrations.AddConstraint(
            model_name="shoppingcenter",
            constraint=models.UniqueConstraint(
                fields=("workspace", "slug"),
                name="malls_shoppingcenter_workspace_slug_uniq",
            ),
        ),
        migrations.AlterModelOptions(
            name="shoppingcenter",
            options={"ordering": ["listing_order", "slug"]},
        ),
    ]
