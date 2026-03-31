import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_status_events(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    OrderStatusEvent = apps.get_model("orders", "OrderStatusEvent")
    DRAFT = "draft"
    SUBMITTED = "submitted"

    for o in Order.objects.all().order_by("id"):
        if OrderStatusEvent.objects.filter(order_id=o.id).exists():
            continue

        OrderStatusEvent.objects.create(
            order_id=o.id,
            from_status="",
            to_status=DRAFT,
            created_at=o.created_at,
            actor_id=None,
            note="",
        )
        if o.status == DRAFT:
            continue

        t_sub = o.submitted_at or o.created_at
        OrderStatusEvent.objects.create(
            order_id=o.id,
            from_status=DRAFT,
            to_status=SUBMITTED,
            created_at=t_sub,
            actor_id=None,
            note="",
        )
        if o.status == SUBMITTED:
            continue

        OrderStatusEvent.objects.create(
            order_id=o.id,
            from_status=SUBMITTED,
            to_status=o.status,
            created_at=t_sub,
            actor_id=None,
            note="Registro histórico aproximado (antes del seguimiento detallado).",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_workflow_phase1"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderStatusEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("from_status", models.CharField(blank=True, max_length=32)),
                ("to_status", models.CharField(max_length=32)),
                ("created_at", models.DateTimeField(db_index=True)),
                ("note", models.TextField(blank=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="order_status_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="status_events",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.RunPython(backfill_status_events, migrations.RunPython.noop),
    ]
