from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from trip_planner.models import DriverProfile


class DriverProfileSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email", read_only=True)
    assigned_vehicle_number = serializers.SerializerMethodField()

    class Meta:
        model = DriverProfile
        fields = [
            "id",
            "email",
            "full_name",
            "license_number",
            "license_state",
            "home_terminal_address",
            "co_driver_name",
            "current_cycle_used_hours",
            "cycle_reset_at",
            "profile_completed_at",
            "assigned_vehicle_number",
        ]
        read_only_fields = [
            "id",
            "email",
            "cycle_reset_at",
            "profile_completed_at",
            "assigned_vehicle_number",
        ]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_assigned_vehicle_number(self, obj):
        vehicle = getattr(obj, "assigned_vehicle", None)
        return vehicle.truck_number if vehicle else None
