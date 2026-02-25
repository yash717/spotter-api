import uuid

from django.db import models

from .organization import Organization


class Vehicle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="vehicles"
    )
    assigned_driver_profile = models.OneToOneField(
        "trip_planner.DriverProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_vehicle",
    )
    truck_number = models.CharField(max_length=50)
    trailer_number = models.CharField(max_length=50, blank=True, default="")
    license_plate = models.CharField(max_length=20, blank=True, default="")
    vin = models.CharField(max_length=17, blank=True, default="")
    odometer_current = models.DecimalField(
        max_digits=10, decimal_places=1, default=0
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vehicles"
        unique_together = [("organization", "truck_number")]

    def __str__(self):
        return f"{self.truck_number} ({self.organization.name})"
