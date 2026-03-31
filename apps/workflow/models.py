from django.db import models

from apps.common.models import TimeStampedActiveModel


class WorkflowTransition(TimeStampedActiveModel):
    """Audit log for order status changes."""

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="workflow_transitions",
    )
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.from_status} → {self.to_status}"
