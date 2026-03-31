from django.db import models

from apps.common.models import TimeStampedActiveModel


class ClientStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class Client(TimeStampedActiveModel):
    company_name = models.CharField(max_length=255)
    rif = models.CharField(max_length=32, unique=True)
    contact_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ClientStatus.choices,
        default=ClientStatus.PENDING,
    )
    cover_image = models.ImageField(
        upload_to="covers/clients/%Y/%m/",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name
