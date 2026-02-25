from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from trip_planner.models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    assigned_driver_name = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = [
            "id", "truck_number", "trailer_number",
            "license_plate", "vin", "odometer_current",
            "is_active", "updated_at", "assigned_driver_name",
        ]
        read_only_fields = ["id", "updated_at", "assigned_driver_name"]

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_assigned_driver_name(self, obj):
        profile = obj.assigned_driver_profile
        return profile.full_name if profile else None


class VehicleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "truck_number", "trailer_number",
            "license_plate", "vin", "odometer_current",
        ]

    def validate_truck_number(self, value):
        org = self.context.get("organization")
        if org and Vehicle.objects.filter(organization=org, truck_number=value).exists():
            raise serializers.ValidationError(
                f"Truck number '{value}' already exists in this organization."
            )
        return value


class VehicleAssignSerializer(serializers.Serializer):
    driver_profile_id = serializers.UUIDField()
