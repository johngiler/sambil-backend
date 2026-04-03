from django.contrib import admin

from apps.users.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "client", "workspace")
    list_filter = ("role",)
    list_select_related = ("user", "client", "workspace")
    search_fields = ("user__username", "user__email")
