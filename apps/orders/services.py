from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone

from apps.orders.models import OrderStatusEvent

if TYPE_CHECKING:
    from apps.orders.models import Order


def log_order_status_transition(
    order: Order,
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
