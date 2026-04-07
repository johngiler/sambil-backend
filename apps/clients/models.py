from django.db import models

from apps.common.models import TimeStampedActiveModel


class ClientStatus(models.TextChoices):
    ACTIVE = "active", "Activo"
    SUSPENDED = "suspended", "Suspendido"


class Client(TimeStampedActiveModel):
    """
    Empresa cliente del marketplace. Varios usuarios (UserProfile con rol cliente) pueden
    vincularse a la misma fila; cada usuario solo puede estar vinculado a una empresa a la vez.
    """

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="clients",
        help_text="Tenant al que pertenece la empresa cliente (RIF único por workspace cuando está indicado).",
    )
    company_name = models.CharField(max_length=255)
    rif = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        help_text="Identificación fiscal; se puede completar después en Mi empresa.",
    )
    contact_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ClientStatus.choices,
        default=ClientStatus.ACTIVE,
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
