from django.contrib import admin

from .models import (
    AuditLog,
    CustomUser,
    DailyLogSheet,
    DriverProfile,
    DutyStatusSegment,
    GeocodeCache,
    HOSViolation,
    Invitation,
    Organization,
    OrganizationMember,
    Stop,
    Trip,
    Vehicle,
)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ["email", "first_name", "last_name", "is_active", "date_joined"]
    search_fields = ["email", "first_name", "last_name"]
    list_filter = ["is_active", "email_verified"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "dot_number", "mc_number", "is_active", "created_at"]
    search_fields = ["name", "dot_number"]
    list_filter = ["is_active"]


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role", "is_active", "joined_at"]
    list_filter = ["role", "is_active"]
    search_fields = ["user__email", "organization__name"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "organization", "role", "status", "sent_at", "expires_at"]
    list_filter = ["status", "role"]
    search_fields = ["email", "organization__name"]


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ["full_name", "user", "license_number", "license_state", "current_cycle_used_hours"]
    search_fields = ["full_name", "user__email", "license_number"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["truck_number", "organization", "trailer_number", "is_active", "odometer_current"]
    list_filter = ["is_active"]
    search_fields = ["truck_number", "organization__name"]


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = [
        "id", "organization", "status",
        "input_current_address", "input_dropoff_address",
        "total_trip_distance_miles", "calculated_trip_days", "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["input_current_address", "input_pickup_address", "input_dropoff_address"]


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ["trip", "sequence_number", "type", "address_text", "duration_minutes"]
    list_filter = ["type", "is_hos_mandated"]


@admin.register(DailyLogSheet)
class DailyLogSheetAdmin(admin.ModelAdmin):
    list_display = [
        "trip", "log_date", "day_number_in_trip",
        "total_driving_hours_day", "total_off_duty_hours_day",
    ]


@admin.register(DutyStatusSegment)
class DutyStatusSegmentAdmin(admin.ModelAdmin):
    list_display = ["daily_log_sheet", "status", "duration_minutes", "segment_label", "sequence_in_day"]
    list_filter = ["status"]


@admin.register(HOSViolation)
class HOSViolationAdmin(admin.ModelAdmin):
    list_display = ["trip", "violation_type", "severity", "acknowledged"]
    list_filter = ["violation_type", "severity"]


@admin.register(GeocodeCache)
class GeocodeCacheAdmin(admin.ModelAdmin):
    list_display = ["raw_input", "resolved_lat", "resolved_lng", "provider", "created_at"]
    search_fields = ["raw_input"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "actor_user", "organization", "created_at", "ip_address"]
    list_filter = ["action"]
    search_fields = ["actor_user__email", "organization__name"]
