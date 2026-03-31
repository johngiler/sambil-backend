from django.contrib import admin

from apps.availability.models import AvailabilityBlock


@admin.register(AvailabilityBlock)
class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ("ad_space", "start_date", "end_date", "type")
