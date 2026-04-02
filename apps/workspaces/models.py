"""
Tenant lógico del SaaS: un owner (marca operadora) con sus CCs, tomas y aislamiento de datos.

- Subdominio: `slug` estable por owner → `https://{slug}.<dominio apex>`.
- Branding macro: logos, colores, textos de soporte (el front puede leer un endpoint público por slug).
- Publivalla (plataforma): staff Django / superusuarios ven todo; no necesitan `workspace` en perfil.
- Admin comercial del owner: `UserProfile.role=admin` + `workspace` = solo su árbol.
"""

from django.db import models

from apps.common.models import TimeStampedActiveModel


class Workspace(TimeStampedActiveModel):
    slug = models.SlugField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Identificador estable para subdominio y APIs (solo letras minúsculas, números, guiones).",
    )
    name = models.CharField(
        max_length=200,
        help_text="Nombre comercial del owner (marca operadora del marketplace).",
    )
    legal_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Razón social u organismo propietario (opcional).",
    )
    logo = models.ImageField(
        upload_to="workspaces/logos/%Y/%m/",
        blank=True,
        null=True,
        help_text="Logo principal (marketplace / emails).",
    )
    logo_mark = models.ImageField(
        upload_to="workspaces/logo_marks/%Y/%m/",
        blank=True,
        null=True,
        help_text="Isotipo o marca reducida (header compacto).",
    )
    favicon = models.ImageField(
        upload_to="workspaces/favicons/%Y/%m/",
        blank=True,
        null=True,
    )
    primary_color = models.CharField(
        max_length=32,
        blank=True,
        help_text="Color de marca principal (hex, ej. #2c2c81).",
    )
    secondary_color = models.CharField(
        max_length=32,
        blank=True,
        help_text="Color secundario / acentos (hex).",
    )
    support_email = models.EmailField(blank=True)
    marketplace_title = models.CharField(
        max_length=120,
        blank=True,
        help_text="Título corto del marketplace (si vacío, se usa `name`).",
    )
    marketplace_tagline = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["slug"]
        verbose_name = "Workspace (owner)"
        verbose_name_plural = "Workspaces (owners)"

    def __str__(self):
        return f"{self.slug} — {self.name}"
