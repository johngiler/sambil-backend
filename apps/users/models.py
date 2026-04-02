from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Rol de aplicación (JWT + permisos DRF). Distinto de is_staff de Django."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        CLIENT = "client", "Cliente marketplace"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.CLIENT,
        db_index=True,
    )
    cover_image = models.ImageField(
        upload_to="covers/users/%Y/%m/",
        blank=True,
        null=True,
    )
    client = models.ForeignKey(
        "clients.Client",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="member_profiles",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_profiles",
        help_text="Admin comercial del owner: acota el panel a este workspace. Vacío si no aplica.",
    )

    class Meta:
        ordering = ["user_id"]

    def __str__(self):
        return f"{self.user.username} ({self.role})"
