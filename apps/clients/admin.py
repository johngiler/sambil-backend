from django.contrib import admin

from apps.clients.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("company_name", "rif", "email", "status")
    search_fields = ("company_name", "rif", "email")
