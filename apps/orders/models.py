from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedActiveModel


class OrderPaymentMethod(models.TextChoices):
    """Medio de pago indicado por el cliente (checkout); visible en el panel admin."""

    UNSET = "", "Sin indicar"
    CARD = "card", "Tarjeta"
    BANK_TRANSFER = "bank_transfer", "Transferencia bancaria"
    MOBILE_PAYMENT = "mobile_payment", "Pago móvil"
    ZELLE = "zelle", "Zelle"
    CRYPTO = "crypto", "Cripto"
    CASH = "cash", "Efectivo"
    OTHER = "other", "Otro"


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
    payment_method = models.CharField(
        max_length=32,
        choices=OrderPaymentMethod.choices,
        default=OrderPaymentMethod.UNSET,
        blank=True,
        db_index=True,
    )
    payment_receipt = models.FileField(
        upload_to="orders/receipts/%Y/%m/",
        blank=True,
        null=True,
        help_text="Comprobante subido por el cliente en checkout.",
    )
    code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
        help_text="Código único de pedido (#SLUG-ORDER-000001). Se asigna al crear.",
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not (self.code or "").strip():
            self._assign_code()

    def _assign_code(self):
        from apps.clients.models import Client
        from apps.orders.references import format_order_public_reference

        slug = ""
        if self.client_id:
            row = (
                Client.objects.select_related("workspace")
                .filter(pk=self.client_id)
                .only("workspace__slug")
                .first()
            )
            if row and row.workspace_id:
                slug = row.workspace.slug or ""
        ref = format_order_public_reference(self.pk, slug)
        Order.objects.filter(pk=self.pk).update(code=ref)
        self.code = ref

    def __str__(self):
        ref = (self.code or "").strip()
        if ref:
            return f"{ref} ({self.get_status_display()})"
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
