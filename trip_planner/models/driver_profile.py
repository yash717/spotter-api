import uuid

from django.conf import settings
from django.db import models

from .organization import OrganizationMember


class DriverProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="driver_profile"
    )
    org_member = models.OneToOneField(
        OrganizationMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="driver_profile",
    )
    full_name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=50, blank=True, default="")
    license_state = models.CharField(max_length=5, blank=True, default="")
    home_terminal_address = models.CharField(max_length=500, blank=True, default="")
    co_driver_name = models.CharField(max_length=255, blank=True, default="")
    current_cycle_used_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    cycle_reset_at = models.DateTimeField(null=True, blank=True)
    profile_completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "driver_profiles"

    def __str__(self):
        return self.full_name
