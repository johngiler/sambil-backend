from django.db import models

from apps.common.models import TimeStampedActiveModel


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ISSUED = "issued", "Issued"
    PAID = "paid", "Paid"
    VOID = "void", "Void"


class Invoice(TimeStampedActiveModel):
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="invoice",
    )
    number = models.CharField(max_length=32, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    issued_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )

    def __str__(self):
        return self.number
