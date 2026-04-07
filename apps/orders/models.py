from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedActiveModel


class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    SUBMITTED = "submitted", "Enviada"
    CLIENT_APPROVED = "client_approved", "Solicitud aprobada"
    ART_APPROVED = "art_approved", "Arte aprobado"
    INVOICED = "invoiced", "Facturada"
    PAID = "paid", "Pagada"
    PERMIT_PENDING = "permit_pending", "Permiso alcaldía"
    INSTALLATION = "installation", "Instalación"
    ACTIVE = "active", "Activa"
    EXPIRED = "expired", "Vencida"
    CANCELLED = "cancelled", "Cancelada"
    REJECTED = "rejected", "Rechazada"


class Order(TimeStampedActiveModel):
    client = models.ForeignKey(
        "clients.Client",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        max_length=32,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.pk} ({self.status})"


class OrderStatusEvent(models.Model):
    """Historial de cambios de estado (cliente y administración)."""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_events",
    )
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    created_at = models.DateTimeField(db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_status_events",
    )
    note = models.TextField(blank=True)

    class Meta:
        # Cronológico (más antiguo primero): encaja con líneas de tiempo en la UI.
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Order {self.order_id}: {self.from_status!r} → {self.to_status!r}"


class OrderItem(TimeStampedActiveModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    ad_space = models.ForeignKey(
        "ad_spaces.AdSpace",
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Item {self.pk} for order {self.order_id}"
