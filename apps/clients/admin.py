from django.contrib import admin

from apps.clients.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("company_name", "workspace", "rif", "email", "status")
    list_filter = ("workspace", "status")
    search_fields = ("company_name", "rif", "email")
