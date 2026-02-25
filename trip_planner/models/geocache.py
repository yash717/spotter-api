import uuid

from django.db import models


class GeocodeCache(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    raw_input = models.CharField(max_length=500, db_index=True)
    resolved_lat = models.DecimalField(max_digits=10, decimal_places=7)
    resolved_lng = models.DecimalField(max_digits=10, decimal_places=7)
    canonical_address = models.CharField(max_length=500, blank=True, default="")
    provider = models.CharField(max_length=30, default="openrouteservice")
    confidence_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "geocode_cache"

    def __str__(self):
        return f"{self.raw_input} → ({self.resolved_lat}, {self.resolved_lng})"
