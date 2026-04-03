"""Reglas de negocio Fase 1: duración mínima, solapamiento, hold 72h."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from apps.availability.models import AvailabilityBlock, AvailabilityBlockType
from apps.orders.models import OrderItem, OrderStatus


# Órdenes que reservan el espacio en el calendario (no borrador / cancelada / rechazada / vencida)
PIPELINE_STATUSES: tuple[str, ...] = (
    OrderStatus.SUBMITTED,
    OrderStatus.CLIENT_APPROVED,
    OrderStatus.ART_APPROVED,
    OrderStatus.INVOICED,
    OrderStatus.PAID,
    OrderStatus.PERMIT_PENDING,
    OrderStatus.INSTALLATION,
    OrderStatus.ACTIVE,
)


def contract_months_inclusive(start: date, end: date) -> int:
    """Meses de calendario cubiertos de forma inclusiva (regla comercial simple)."""
    if end < start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def contract_meets_min_months(start: date, end: date, min_months: int = 5) -> bool:
    return contract_months_inclusive(start, end) >= min_months


def date_ranges_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and b_start <= a_end


def order_item_conflicts(
    ad_space_id: int,
    start: date,
    end: date,
    *,
    exclude_order_id: int | None = None,
) -> bool:
    """True si ya hay una orden en pipeline u otro bloqueo que choque con [start, end]."""
    q_items = OrderItem.objects.filter(ad_space_id=ad_space_id).filter(
        order__status__in=PIPELINE_STATUSES
    )
    if exclude_order_id is not None:
        q_items = q_items.exclude(order_id=exclude_order_id)

    for row in q_items.iterator():
        if date_ranges_overlap(start, end, row.start_date, row.end_date):
            return True

    blocks = AvailabilityBlock.objects.filter(
        ad_space_id=ad_space_id,
        is_active=True,
        type__in=(
            AvailabilityBlockType.OCCUPIED,
            AvailabilityBlockType.BLOCKED,
            AvailabilityBlockType.RESERVED,
        ),
    )
    for b in blocks.iterator():
        if date_ranges_overlap(start, end, b.start_date, b.end_date):
            return True

    return False


def line_subtotal(monthly_price: Decimal, start: date, end: date) -> Decimal:
    months = contract_months_inclusive(start, end)
    return (monthly_price * months).quantize(Decimal("0.01"))


def hold_expires_at_from_now(hours: int = 72) -> datetime:
    return timezone.now() + timedelta(hours=hours)
