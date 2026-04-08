from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone

from apps.orders.models import OrderStatus, OrderStatusEvent
from apps.orders.validators import (
    ad_space_allows_marketplace_reservation,
    contract_meets_min_months,
    hold_expires_at_from_now,
    line_subtotal,
    order_item_conflicts,
)

if TYPE_CHECKING:
    from apps.orders.models import Order


def log_order_status_transition(
    order: "Order",
    from_status: str,
    to_status: str,
    *,
    actor: AbstractBaseUser | None = None,
    note: str = "",
    created_at=None,
) -> OrderStatusEvent:
    """Registra un paso en la línea de tiempo de la orden."""
    return OrderStatusEvent.objects.create(
        order=order,
        from_status=from_status or "",
        to_status=to_status,
        actor=actor,
        note=note or "",
        created_at=created_at if created_at is not None else timezone.now(),
    )


def submit_draft_order(order: "Order", *, actor: AbstractBaseUser | None = None) -> "Order":
    """
    Pasa una orden de borrador a enviada (misma lógica que POST .../submit/).
    Lanza ValidationError de DRF si no aplica.
    """
    from rest_framework import serializers

    if order.status != OrderStatus.DRAFT:
        raise serializers.ValidationError({"detail": "Solo se pueden enviar órdenes en borrador."})

    for item in order.items.select_related("ad_space"):
        if not contract_meets_min_months(item.start_date, item.end_date):
            raise serializers.ValidationError(
                {
                    "detail": f"La línea {item.ad_space.code} no cumple el mínimo de 5 meses.",
                }
            )
        if not ad_space_allows_marketplace_reservation(item.ad_space):
            raise serializers.ValidationError(
                {
                    "detail": (
                        f"La toma {item.ad_space.code} no admite enviar la solicitud "
                        f"(estado: {item.ad_space.get_status_display()}). "
                        "Quítala del carrito o elige otra toma."
                    ),
                }
            )
        if order_item_conflicts(
            item.ad_space_id,
            item.start_date,
            item.end_date,
            exclude_order_id=order.id,
        ):
            title = (item.ad_space.title or "").strip() or "esta toma"
            raise serializers.ValidationError(
                {
                    "detail": (f'Las fechas de «{title}» chocan con otra reserva o bloqueo.'),
                }
            )

    total = Decimal("0")
    for item in order.items.select_related("ad_space"):
        monthly = item.ad_space.monthly_price_usd
        sub = line_subtotal(monthly, item.start_date, item.end_date)
        item.monthly_price = monthly
        item.subtotal = sub
        item.save(update_fields=["monthly_price", "subtotal"])
        total += sub
    order.total_amount = total.quantize(Decimal("0.01"))
    order.status = OrderStatus.SUBMITTED
    order.submitted_at = timezone.now()
    order.hold_expires_at = hold_expires_at_from_now(72)
    order.save(
        update_fields=[
            "total_amount",
            "status",
            "submitted_at",
            "hold_expires_at",
        ]
    )

    log_order_status_transition(
        order,
        OrderStatus.DRAFT,
        OrderStatus.SUBMITTED,
        actor=actor,
        note="Solicitud enviada por el cliente.",
    )
    order.refresh_from_db()
    return order
