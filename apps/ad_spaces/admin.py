from django.contrib import admin

from apps.ad_spaces.models import AdSpace


@admin.register(AdSpace)
class AdSpaceAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "shopping_center", "monthly_price_usd", "status")
    list_filter = ("shopping_center", "status", "type")
