"""
Centralized constants for the ELD Trip Planner.
All enum values use UPPER_SNAKE_CASE.
"""


class MemberRole:
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    ORG_ADMIN = "ORG_ADMIN"
    DISPATCHER = "DISPATCHER"
    DRIVER = "DRIVER"
    FLEET_MANAGER = "FLEET_MANAGER"
    VIEWER = "VIEWER"

    CHOICES = [
        (PLATFORM_ADMIN, "Platform Admin"),
        (ORG_ADMIN, "Org Admin"),
        (DISPATCHER, "Dispatcher"),
        (DRIVER, "Driver"),
        (FLEET_MANAGER, "Fleet Manager"),
        (VIEWER, "Viewer"),
    ]

    INVITABLE_CHOICES = [
        (DISPATCHER, "Dispatcher"),
        (DRIVER, "Driver"),
        (FLEET_MANAGER, "Fleet Manager"),
        (VIEWER, "Viewer"),
    ]

    ALL = {PLATFORM_ADMIN, ORG_ADMIN, DISPATCHER, DRIVER, FLEET_MANAGER, VIEWER}


class InvitationStatus:
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

    CHOICES = [
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (EXPIRED, "Expired"),
        (REVOKED, "Revoked"),
    ]


class TripStatus:
    DRAFT = "DRAFT"
    ASSIGNED = "ASSIGNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"

    CHOICES = [
        (DRAFT, "Draft"),
        (ASSIGNED, "Assigned"),
        (ACTIVE, "Active"),
        (COMPLETED, "Completed"),
        (ARCHIVED, "Archived"),
    ]
    ALL = [DRAFT, ASSIGNED, ACTIVE, COMPLETED, ARCHIVED]


class StopType:
    INITIAL_PICKUP = "INITIAL_PICKUP"
    FINAL_DROPOFF = "FINAL_DROPOFF"
    FUEL = "FUEL"
    REST_30MIN = "REST_30MIN"
    REST_10HR = "REST_10HR"
    SLEEPER = "SLEEPER"
    WAYPOINT = "WAYPOINT"

    CHOICES = [
        (INITIAL_PICKUP, "Initial Pickup"),
        (FINAL_DROPOFF, "Final Dropoff"),
        (FUEL, "Fuel Stop"),
        (REST_30MIN, "30-Minute Break"),
        (REST_10HR, "10-Hour Rest"),
        (SLEEPER, "Sleeper Berth"),
        (WAYPOINT, "Waypoint"),
    ]


class DutyStatus:
    DRIVING = "DRIVING"
    ON_DUTY_ND = "ON_DUTY_ND"
    SLEEPER_BERTH = "SLEEPER_BERTH"
    OFF_DUTY = "OFF_DUTY"

    CHOICES = [
        (DRIVING, "Driving"),
        (ON_DUTY_ND, "On Duty (Not Driving)"),
        (SLEEPER_BERTH, "Sleeper Berth"),
        (OFF_DUTY, "Off Duty"),
    ]


class ViolationType:
    CYCLE_LIMIT_EXCEEDED = "CYCLE_LIMIT_EXCEEDED"
    DRIVING_OVER_11HR = "DRIVING_OVER_11HR"
    WINDOW_OVER_14HR = "WINDOW_OVER_14HR"
    MISSING_30MIN_BREAK = "MISSING_30MIN_BREAK"

    CHOICES = [
        (CYCLE_LIMIT_EXCEEDED, "70-Hour Cycle Limit Exceeded"),
        (DRIVING_OVER_11HR, "Driving Over 11 Hours"),
        (WINDOW_OVER_14HR, "On-Duty Window Over 14 Hours"),
        (MISSING_30MIN_BREAK, "Missing 30-Minute Break"),
    ]


class Severity:
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

    CHOICES = [
        (WARNING, "Warning"),
        (CRITICAL, "Critical"),
    ]


class AuditAction:
    INVITATION_SENT = "INVITATION_SENT"
    INVITATION_ACCEPTED = "INVITATION_ACCEPTED"
    INVITATION_REVOKED = "INVITATION_REVOKED"
    MEMBER_DEACTIVATED = "MEMBER_DEACTIVATED"
    VEHICLE_ASSIGNED = "VEHICLE_ASSIGNED"
    VEHICLE_UNASSIGNED = "VEHICLE_UNASSIGNED"
    TRIP_ASSIGNED = "TRIP_ASSIGNED"
    TRIP_CREATED = "TRIP_CREATED"
    ORG_CREATED = "ORG_CREATED"

    CHOICES = [
        (INVITATION_SENT, "Invitation Sent"),
        (INVITATION_ACCEPTED, "Invitation Accepted"),
        (INVITATION_REVOKED, "Invitation Revoked"),
        (MEMBER_DEACTIVATED, "Member Deactivated"),
        (VEHICLE_ASSIGNED, "Vehicle Assigned"),
        (VEHICLE_UNASSIGNED, "Vehicle Unassigned"),
        (TRIP_ASSIGNED, "Trip Assigned"),
        (TRIP_CREATED, "Trip Created"),
        (ORG_CREATED, "Organization Created"),
    ]
