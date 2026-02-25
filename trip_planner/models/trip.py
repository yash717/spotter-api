import uuid

from django.conf import settings
from django.db import models

from trip_planner.constants import TripStatus

from .organization import Organization
from .vehicle import Vehicle


class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="trips"
    )
    assigned_driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_trips",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="created_trips",
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.SET_NULL, null=True, blank=True, related_name="trips",
    )
    input_current_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    input_current_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    input_pickup_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    input_pickup_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    input_dropoff_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    input_dropoff_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    input_current_address = models.CharField(max_length=500, blank=True, default="")
    input_pickup_address = models.CharField(max_length=500, blank=True, default="")
    input_dropoff_address = models.CharField(max_length=500, blank=True, default="")
    input_cycle_used_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    remaining_cycle_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    total_trip_distance_miles = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True)
    total_trip_duration_hours = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    total_driving_hours = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    calculated_trip_days = models.IntegerField(null=True, blank=True)
    route_polyline_json = models.TextField(blank=True, default="")
    cycle_exhausted_mid_trip = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=TripStatus.CHOICES, default=TripStatus.DRAFT)
    planned_start_datetime = models.DateTimeField(null=True, blank=True)
    planned_end_datetime = models.DateTimeField(null=True, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "trips"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Trip {self.id} ({self.status})"
