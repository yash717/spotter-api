import uuid

from django.db import models

from trip_planner.constants import DutyStatus

from .stop import Stop
from .trip import Trip


class DailyLogSheet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="daily_logs")
    log_date = models.DateField()
    day_number_in_trip = models.IntegerField()
    total_driving_hours_day = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    total_on_duty_nd_hours_day = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    total_sleeper_hours_day = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    total_off_duty_hours_day = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    cumulative_hos_start = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    cumulative_hos_end = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    start_day_odometer = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    end_day_odometer = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    from_location = models.CharField(max_length=255, blank=True, default="")
    to_location = models.CharField(max_length=255, blank=True, default="")
    carrier_name = models.CharField(max_length=255, blank=True, default="")
    driver_name = models.CharField(max_length=255, blank=True, default="")
    vehicle_numbers = models.CharField(max_length=100, blank=True, default="")
    shipping_doc_number = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "daily_log_sheets"
        ordering = ["trip", "day_number_in_trip"]

    def __str__(self):
        return f"Day {self.day_number_in_trip} - {self.log_date} - Trip {self.trip_id}"


class DutyStatusSegment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    daily_log_sheet = models.ForeignKey(
        DailyLogSheet, on_delete=models.CASCADE, related_name="segments"
    )
    stop = models.ForeignKey(
        Stop, on_delete=models.SET_NULL, null=True, blank=True, related_name="segments"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=15, choices=DutyStatus.CHOICES)
    duration_minutes = models.IntegerField(default=0)
    start_location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    start_location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    distance_traveled_miles = models.DecimalField(
        max_digits=8, decimal_places=1, null=True, blank=True
    )
    segment_label = models.CharField(max_length=255, blank=True, default="")
    sequence_in_day = models.IntegerField(default=0)

    class Meta:
        db_table = "duty_status_segments"
        ordering = ["daily_log_sheet", "sequence_in_day"]

    def __str__(self):
        return f"{self.status} ({self.duration_minutes}min) - {self.segment_label}"
