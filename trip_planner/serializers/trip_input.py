from rest_framework import serializers


class TripPlanInputSerializer(serializers.Serializer):
    current_location = serializers.CharField(
        max_length=500, help_text="Current location address or coordinates"
    )
    pickup_location = serializers.CharField(
        max_length=500, help_text="Pickup location address or coordinates"
    )
    dropoff_location = serializers.CharField(
        max_length=500, help_text="Dropoff location address or coordinates"
    )
    cycle_used_hours = serializers.DecimalField(
        max_digits=5, decimal_places=1,
        min_value=0, max_value=70,
        help_text="Hours already used in current 70-hour/8-day cycle",
    )
    planned_start_datetime = serializers.DateTimeField(
        required=False, help_text="Optional planned departure time"
    )
