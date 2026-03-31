from django.contrib import admin

from apps.orders.models import Order, OrderItem, OrderStatusEvent


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderStatusEventInline(admin.TabularInline):
    model = OrderStatusEvent
    extra = 0
    readonly_fields = ("from_status", "to_status", "created_at", "actor", "note")
    ordering = ("-created_at",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "status", "total_amount", "created_at")
    list_filter = ("status",)
    inlines = [OrderItemInline, OrderStatusEventInline]
