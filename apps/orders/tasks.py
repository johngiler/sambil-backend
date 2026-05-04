"""Tareas Celery del dominio de pedidos (correo fuera del ciclo request/response)."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def send_order_status_emails_task(self, order_id: int, from_status: str, to_status: str) -> None:
    from apps.orders.email_notifications import try_send_order_status_emails
    from apps.orders.models import Order

    try:
        order = Order.objects.select_related("client__workspace").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("send_order_status_emails_task: pedido %s no encontrado.", order_id)
        return
    try_send_order_status_emails(order, from_status or "", to_status)


@shared_task(bind=True, ignore_result=True)
def notify_client_activation_after_approval_task(self, order_id: int) -> None:
    from apps.clients.notifications import notify_client_after_order_client_approved
    from apps.orders.models import Order

    try:
        order = Order.objects.select_related("client__workspace").get(pk=order_id)
    except Order.DoesNotExist:
        logger.warning("notify_client_activation_after_approval_task: pedido %s no encontrado.", order_id)
        return
    notify_client_after_order_client_approved(order)
