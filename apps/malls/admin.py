from django.contrib import admin

from apps.malls.models import ShoppingCenter


@admin.register(ShoppingCenter)
class ShoppingCenterAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "workspace",
        "city",
        "is_active",
        "marketplace_catalog_enabled",
        "created_at",
    )
    list_filter = ("is_active", "marketplace_catalog_enabled", "workspace")
    search_fields = ("code", "name")
