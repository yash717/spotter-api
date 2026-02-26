from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from trip_planner.models import DailyLogSheet, DutyStatusSegment, HOSViolation, Stop, Trip


class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = [
            "id",
            "type",
            "sequence_number",
            "location_lat",
            "location_lng",
            "address_text",
            "scheduled_arrival_time",
            "scheduled_departure_time",
            "duration_minutes",
            "odometer_at_stop",
            "distance_from_prev_stop",
            "notes",
            "is_hos_mandated",
        ]


class DutyStatusSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DutyStatusSegment
        fields = [
            "id",
            "start_time",
            "end_time",
            "status",
            "duration_minutes",
            "start_location_lat",
            "start_location_lng",
            "end_location_lat",
            "end_location_lng",
            "distance_traveled_miles",
            "segment_label",
            "sequence_in_day",
        ]


class DailyLogSheetSerializer(serializers.ModelSerializer):
    segments = DutyStatusSegmentSerializer(many=True, read_only=True)

    class Meta:
        model = DailyLogSheet
        fields = [
            "id",
            "log_date",
            "day_number_in_trip",
            "total_driving_hours_day",
            "total_on_duty_nd_hours_day",
            "total_sleeper_hours_day",
            "total_off_duty_hours_day",
            "cumulative_hos_start",
            "cumulative_hos_end",
            "start_day_odometer",
            "end_day_odometer",
            "from_location",
            "to_location",
            "carrier_name",
            "driver_name",
            "vehicle_numbers",
            "shipping_doc_number",
            "segments",
        ]


class HOSViolationSerializer(serializers.ModelSerializer):
    class Meta:
        model = HOSViolation
        fields = [
            "id",
            "violation_type",
            "violation_time",
            "description",
            "severity",
            "acknowledged",
        ]


class TripListSerializer(serializers.ModelSerializer):
    assigned_driver_email = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()
    vehicle_number = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "status",
            "input_current_address",
            "input_pickup_address",
            "input_dropoff_address",
            "total_trip_distance_miles",
            "total_trip_duration_hours",
            "total_driving_hours",
            "calculated_trip_days",
            "cycle_exhausted_mid_trip",
            "remaining_cycle_hours",
            "assigned_driver_email",
            "created_by_email",
            "vehicle_number",
            "planned_start_datetime",
            "planned_end_datetime",
            "assigned_at",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_assigned_driver_email(self, obj):
        return obj.assigned_driver.email if obj.assigned_driver else None

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_vehicle_number(self, obj):
        return obj.vehicle.truck_number if obj.vehicle else None


class TripDetailSerializer(serializers.ModelSerializer):
    stops = StopSerializer(many=True, read_only=True)
    daily_logs = DailyLogSheetSerializer(many=True, read_only=True)
    violations = HOSViolationSerializer(many=True, read_only=True)
    assigned_driver_email = serializers.SerializerMethodField()
    created_by_email = serializers.SerializerMethodField()
    vehicle_number = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "status",
            "input_current_address",
            "input_pickup_address",
            "input_dropoff_address",
            "input_current_lat",
            "input_current_lng",
            "input_pickup_lat",
            "input_pickup_lng",
            "input_dropoff_lat",
            "input_dropoff_lng",
            "input_cycle_used_hours",
            "remaining_cycle_hours",
            "total_trip_distance_miles",
            "total_trip_duration_hours",
            "total_driving_hours",
            "calculated_trip_days",
            "route_polyline_json",
            "cycle_exhausted_mid_trip",
            "planned_start_datetime",
            "planned_end_datetime",
            "assigned_driver_email",
            "created_by_email",
            "vehicle_number",
            "assigned_at",
            "created_at",
            "updated_at",
            "stops",
            "daily_logs",
            "violations",
        ]

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_assigned_driver_email(self, obj):
        return obj.assigned_driver.email if obj.assigned_driver else None

    @extend_schema_field(serializers.EmailField(allow_null=True))
    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_vehicle_number(self, obj):
        return obj.vehicle.truck_number if obj.vehicle else None
