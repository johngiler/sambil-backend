from django.contrib import admin

from apps.workflow.models import WorkflowTransition


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = ("order", "from_status", "to_status", "created_at")
