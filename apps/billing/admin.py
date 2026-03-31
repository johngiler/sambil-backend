from django.contrib import admin

from apps.billing.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "amount", "status", "issued_at")
