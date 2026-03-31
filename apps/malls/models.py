from django.db import models

from apps.common.models import TimeStampedActiveModel


class ShoppingCenter(TimeStampedActiveModel):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=8, unique=True, db_index=True)
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
        help_text="Si se lista en la portada del marketplace.",
    )
    listing_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Orden en portada (menor primero).",
    )
    marketplace_catalog_enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Si el catálogo público de tomas está habilitado para este centro (reservas en marketplace).",
    )

    class Meta:
        ordering = ["listing_order", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"
