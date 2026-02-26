import uuid

from django.db import models

from trip_planner.constants import StopType

from .trip import Trip


class Stop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stops")
    type = models.CharField(max_length=20, choices=StopType.CHOICES)
    sequence_number = models.IntegerField()
    location_lat = models.DecimalField(max_digits=10, decimal_places=7)
    location_lng = models.DecimalField(max_digits=10, decimal_places=7)
    address_text = models.CharField(max_length=500, blank=True, default="")
    scheduled_arrival_time = models.DateTimeField(null=True, blank=True)
    scheduled_departure_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    odometer_at_stop = models.DecimalField(max_digits=10, decimal_places=1, null=True, blank=True)
    distance_from_prev_stop = models.DecimalField(
        max_digits=8, decimal_places=1, null=True, blank=True
    )
    notes = models.TextField(blank=True, default="")
    is_hos_mandated = models.BooleanField(default=False)

    class Meta:
        db_table = "stops"
        ordering = ["trip", "sequence_number"]

    def __str__(self):
        return f"Stop #{self.sequence_number} ({self.type}) - Trip {self.trip_id}"
