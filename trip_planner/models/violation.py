import uuid

from django.db import models

from trip_planner.constants import Severity, ViolationType

from .log import DailyLogSheet
from .trip import Trip


class HOSViolation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="violations")
    daily_log_sheet = models.ForeignKey(
        DailyLogSheet, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="violations",
    )
    violation_type = models.CharField(max_length=30, choices=ViolationType.CHOICES)
    violation_time = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    severity = models.CharField(max_length=10, choices=Severity.CHOICES, default=Severity.WARNING)
    acknowledged = models.BooleanField(default=False)

    class Meta:
        db_table = "hos_violations"

    def __str__(self):
        return f"{self.violation_type} ({self.severity}) - Trip {self.trip_id}"
