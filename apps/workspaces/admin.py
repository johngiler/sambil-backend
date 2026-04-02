from django.contrib import admin

from apps.workspaces.models import Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("slug", "name", "legal_name")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {"fields": ("slug", "name", "legal_name", "is_active")}),
        ("Branding", {"fields": ("logo", "logo_mark", "favicon", "primary_color", "secondary_color")}),
        ("Marketplace", {"fields": ("marketplace_title", "marketplace_tagline", "support_email")}),
    )
