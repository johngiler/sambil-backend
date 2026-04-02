from django.db import models

from apps.common.models import TimeStampedActiveModel


class ClientStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class Client(TimeStampedActiveModel):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="clients",
        help_text="Tenant al que pertenece la empresa cliente (RIF único por workspace).",
    )
    company_name = models.CharField(max_length=255)
    rif = models.CharField(max_length=32)
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
        constraints = [
            models.UniqueConstraint(
                fields=("workspace", "rif"),
                name="clients_client_workspace_rif_uniq",
            ),
        ]

    def __str__(self):
        return self.company_name
