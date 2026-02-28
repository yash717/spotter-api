from rest_framework import serializers
from django.db.models import Count, Q
from django.utils import timezone
from trip_planner.models import Trip, DailyLogSheet, User
from trip_planner.constants import TripStatus
from datetime import timedelta


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for driver dashboard statistics"""

    cycle_used_hours = serializers.DecimalField(
        max_digits=5, decimal_places=1, help_text="Total hours used in current cycle"
    )
    cycle_remaining_hours = serializers.DecimalField(
        max_digits=5, decimal_places=1, help_text="Remaining hours in current cycle"
    )
    weekly_trip_count = serializers.IntegerField(
        help_text="Number of trips completed this week"
    )
    total_miles_driven = serializers.DecimalField(
        max_digits=8, decimal_places=1, help_text="Total miles driven in current cycle"
    )
    active_violations = serializers.IntegerField(
        help_text="Count of active HOS violations"
    )
    cycle_percentage = serializers.IntegerField(
        help_text="Percentage of 70-hour cycle used"
    )
    on_duty_hours = serializers.DecimalField(
        max_digits=5, decimal_places=1, help_text="Total on-duty hours"
    )
    driving_hours = serializers.DecimalField(
        max_digits=5, decimal_places=1, help_text="Total driving hours"
    )


class DashboardTripSummarySerializer(serializers.ModelSerializer):
    """Serializer for trip summary in dashboard"""

    class Meta:
        model = Trip
        fields = [
            "id",
            "status",
            "input_pickup_address",
            "input_dropoff_address",
            "planned_start_datetime",
            "planned_end_datetime",
            "total_trip_distance_miles",
            "total_trip_duration_hours",
            "total_driving_hours",
        ]


class DriverDashboardSerializer(serializers.Serializer):
    """Combined dashboard serializer with stats and upcoming trips"""

    stats = DashboardStatsSerializer()
    upcoming_trips = DashboardTripSummarySerializer(many=True)
    current_trip = DashboardTripSummarySerializer(allow_null=True)
