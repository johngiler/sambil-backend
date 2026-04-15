from django.db import models

from apps.common.image_webp import ensure_imagefields_webp
from apps.common.models import TimeStampedActiveModel


class ShoppingCenter(TimeStampedActiveModel):
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="shopping_centers",
        help_text="Owner / tenant al que pertenece este centro comercial.",
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(
        max_length=80,
        help_text="Identificador en URL pública (?center=, detalle /api/catalog/centers/{slug}/). Único por workspace.",
    )
    city = models.CharField(max_length=120)
    district = models.CharField(
        max_length=120,
        blank=True,
        help_text="Zona o urbanización para el titular de la tarjeta en portada (ej. Chacao).",
    )
    address = models.TextField(blank=True)
    country = models.CharField(max_length=120, blank=True, default="Venezuela")
    phone = models.CharField(max_length=64, blank=True)
    contact_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(
        upload_to="covers/centers/%Y/%m/",
        blank=True,
        null=True,
    )
    on_homepage = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Si se incluye en el listado público GET /api/centers/ (la portada del sitio lista tomas).",
    )
    listing_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Orden en ese listado de centros (menor primero).",
    )
    marketplace_catalog_enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Si el catálogo público de tomas está habilitado para este centro (reservas en marketplace).",
    )

    class Meta:
        ordering = ["listing_order", "slug"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="malls_shoppingcenter_workspace_slug_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.slug} — {self.name}"

    def save(self, *args, **kwargs):
        _webp_fields = ("cover_image",)
        _uf = kwargs.get("update_fields")
        if _uf is None or any(f in _uf for f in _webp_fields):
            ensure_imagefields_webp(self, _webp_fields)
        return super().save(*args, **kwargs)
