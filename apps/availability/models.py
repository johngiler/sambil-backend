from django.db import models

from apps.common.models import TimeStampedActiveModel


class AvailabilityBlockType(models.TextChoices):
    RESERVED = "reserved", "Reserved"
    OCCUPIED = "occupied", "Occupied"
    BLOCKED = "blocked", "Blocked"


class AvailabilityBlock(TimeStampedActiveModel):
    ad_space = models.ForeignKey(
        "ad_spaces.AdSpace",
        on_delete=models.CASCADE,
        related_name="availability_blocks",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    type = models.CharField(max_length=20, choices=AvailabilityBlockType.choices)

    class Meta:
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.ad_space_id} {self.start_date}–{self.end_date}"
