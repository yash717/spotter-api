"""
Seeds development database with 24 users across all roles,
plus sample vehicles, trips, stops, logs, and invitations.

Usage: python manage.py seed_dev_data
Only for development — production should only seed the superadmin.
"""

import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from trip_planner.constants import (
    AuditAction,
    DutyStatus,
    InvitationStatus,
    MemberRole,
    Severity,
    StopType,
    TripStatus,
    ViolationType,
)
from trip_planner.models import (
    AuditLog,
    CustomUser,
    DailyLogSheet,
    DriverProfile,
    DutyStatusSegment,
    HOSViolation,
    Invitation,
    Organization,
    OrganizationMember,
    Stop,
    Trip,
    Vehicle,
)

SEED_PASSWORD = "SpotterDev123!"

USERS_DATA = [
    # Org 1: Swift Logistics (16 members)
    {"email": "admin@swift.com", "first": "John", "last": "Smith", "role": MemberRole.ORG_ADMIN, "org": 0},
    {"email": "admin2@swift.com", "first": "Jane", "last": "Doe", "role": MemberRole.ORG_ADMIN, "org": 0},
    {"email": "dispatch1@swift.com", "first": "Sarah", "last": "Kim", "role": MemberRole.DISPATCHER, "org": 0},
    {"email": "dispatch2@swift.com", "first": "Mark", "last": "Wilson", "role": MemberRole.DISPATCHER, "org": 0},
    {"email": "fleet1@swift.com", "first": "Lisa", "last": "Park", "role": MemberRole.FLEET_MANAGER, "org": 0},
    {"email": "driver1@swift.com", "first": "Mike", "last": "Torres", "role": MemberRole.DRIVER, "org": 0},
    {"email": "driver2@swift.com", "first": "Dave", "last": "Chen", "role": MemberRole.DRIVER, "org": 0},
    {"email": "driver3@swift.com", "first": "Carlos", "last": "Reyes", "role": MemberRole.DRIVER, "org": 0},
    {"email": "driver4@swift.com", "first": "James", "last": "Brown", "role": MemberRole.DRIVER, "org": 0},
    {"email": "driver5@swift.com", "first": "Alex", "last": "Garcia", "role": MemberRole.DRIVER, "org": 0},
    {"email": "driver6@swift.com", "first": "Brian", "last": "Lee", "role": MemberRole.DRIVER, "org": 0},
    {"email": "driver7@swift.com", "first": "Kevin", "last": "Wang", "role": MemberRole.DRIVER, "org": 0},
    {"email": "driver8@swift.com", "first": "Daniel", "last": "Martinez", "role": MemberRole.DRIVER, "org": 0},
    {"email": "viewer1@swift.com", "first": "Tom", "last": "Hughes", "role": MemberRole.VIEWER, "org": 0},
    {"email": "viewer2@swift.com", "first": "Amy", "last": "Clark", "role": MemberRole.VIEWER, "org": 0},
    {"email": "viewer3@swift.com", "first": "Rachel", "last": "Adams", "role": MemberRole.VIEWER, "org": 0},
    # Org 2: Apex Freight (8 members)
    {"email": "admin@apex.com", "first": "Robert", "last": "Johnson", "role": MemberRole.ORG_ADMIN, "org": 1},
    {"email": "dispatch@apex.com", "first": "Emily", "last": "Taylor", "role": MemberRole.DISPATCHER, "org": 1},
    {"email": "fleet@apex.com", "first": "Chris", "last": "Anderson", "role": MemberRole.FLEET_MANAGER, "org": 1},
    {"email": "driver1@apex.com", "first": "Steve", "last": "Thompson", "role": MemberRole.DRIVER, "org": 1},
    {"email": "driver2@apex.com", "first": "Ryan", "last": "White", "role": MemberRole.DRIVER, "org": 1},
    {"email": "driver3@apex.com", "first": "Nathan", "last": "Harris", "role": MemberRole.DRIVER, "org": 1},
    {"email": "driver4@apex.com", "first": "Tyler", "last": "Moore", "role": MemberRole.DRIVER, "org": 1},
    {"email": "viewer@apex.com", "first": "Patricia", "last": "Davis", "role": MemberRole.VIEWER, "org": 1},
]

US_STATES = ["TX", "CA", "IL", "FL", "OH", "PA", "NY", "GA", "MI", "NC"]

CITIES = [
    ("Chicago, IL", 41.8781, -87.6298),
    ("Dallas, TX", 32.7767, -96.7970),
    ("Memphis, TN", 35.1495, -90.0490),
    ("Atlanta, GA", 33.7490, -84.3880),
    ("Houston, TX", 29.7604, -95.3698),
    ("Los Angeles, CA", 34.0522, -118.2437),
    ("Denver, CO", 39.7392, -104.9903),
    ("Nashville, TN", 36.1627, -86.7816),
    ("Phoenix, AZ", 33.4484, -112.0740),
    ("Indianapolis, IN", 39.7684, -86.1581),
]


class Command(BaseCommand):
    help = "Seeds development database with 24 users and sample data"

    @transaction.atomic
    def handle(self, *args, **options):
        if CustomUser.objects.filter(email="admin@swift.com").exists():
            self.stdout.write(self.style.WARNING("Seed data already exists. Skipping."))
            return

        self.stdout.write("Creating superadmin...")
        superadmin = CustomUser.objects.create_superuser(
            username="superadmin", email="superadmin@spotter.ai",
            password=SEED_PASSWORD, first_name="Super", last_name="Admin",
        )

        self.stdout.write("Creating organizations...")
        orgs = [
            Organization.objects.create(
                name="Swift Logistics", dot_number="DOT123456",
                mc_number="MC654321", primary_contact_email="admin@swift.com",
                address="100 Fleet Way, Dallas TX 75201", phone="214-555-0100",
            ),
            Organization.objects.create(
                name="Apex Freight", dot_number="DOT789012",
                mc_number="MC210987", primary_contact_email="admin@apex.com",
                address="200 Carrier Blvd, Atlanta GA 30301", phone="404-555-0200",
            ),
        ]

        self.stdout.write("Creating users and memberships...")
        users = {}
        driver_idx = 0
        for ud in USERS_DATA:
            user = CustomUser.objects.create_user(
                username=ud["email"], email=ud["email"], password=SEED_PASSWORD,
                first_name=ud["first"], last_name=ud["last"],
            )
            users[ud["email"]] = user

            member = OrganizationMember.objects.create(
                organization=orgs[ud["org"]], user=user, role=ud["role"],
            )

            if ud["role"] == MemberRole.DRIVER:
                state = US_STATES[driver_idx % len(US_STATES)]
                cycle_hrs = round(random.uniform(5, 55), 1)
                profile = DriverProfile.objects.create(
                    user=user, org_member=member,
                    full_name=f"{ud['first']} {ud['last']}",
                    license_number=f"{state}-{random.randint(100000, 999999)}",
                    license_state=state,
                    home_terminal_address=f"{random.randint(100,999)} Trucker Ln, {CITIES[driver_idx % len(CITIES)][0]}",
                    current_cycle_used_hours=Decimal(str(cycle_hrs)),
                    profile_completed_at=datetime.now(timezone.utc),
                )
                truck_num = f"T-{1000 + driver_idx}"
                Vehicle.objects.create(
                    organization=orgs[ud["org"]],
                    assigned_driver_profile=profile,
                    truck_number=truck_num,
                    trailer_number=f"TR-{7000 + driver_idx}",
                    license_plate=f"{state}D-{random.randint(1000,9999)}",
                    vin=f"1HGCM{random.randint(10000,99999)}A{random.randint(100000,999999)}",
                    odometer_current=Decimal(str(random.randint(50000, 300000))),
                )
                driver_idx += 1
            else:
                DriverProfile.objects.create(
                    user=user, org_member=member,
                    full_name=f"{ud['first']} {ud['last']}",
                    profile_completed_at=datetime.now(timezone.utc),
                )

        self.stdout.write("Creating unassigned vehicles...")
        for i in range(4):
            Vehicle.objects.create(
                organization=orgs[0],
                truck_number=f"T-{2000 + i}",
                trailer_number=f"TR-{8000 + i}",
                license_plate=f"TX-{random.randint(1000,9999)}",
                odometer_current=Decimal(str(random.randint(10000, 80000))),
            )

        self.stdout.write("Creating sample trips...")
        admin_user = users["admin@swift.com"]
        for i in range(6):
            c1 = CITIES[i % len(CITIES)]
            c2 = CITIES[(i + 2) % len(CITIES)]
            c3 = CITIES[(i + 4) % len(CITIES)]
            driver_email = f"driver{i+1}@swift.com"
            driver = users.get(driver_email)
            distance = round(random.uniform(400, 1800), 1)
            driving_hrs = round(distance / 55, 1)
            trip_days = max(1, int(driving_hrs / 10))

            trip = Trip.objects.create(
                organization=orgs[0], created_by=admin_user,
                assigned_driver=driver,
                status=random.choice([TripStatus.DRAFT, TripStatus.ASSIGNED, TripStatus.ACTIVE, TripStatus.COMPLETED]),
                input_current_address=c1[0], input_pickup_address=c2[0], input_dropoff_address=c3[0],
                input_current_lat=Decimal(str(c1[1])), input_current_lng=Decimal(str(c1[2])),
                input_pickup_lat=Decimal(str(c2[1])), input_pickup_lng=Decimal(str(c2[2])),
                input_dropoff_lat=Decimal(str(c3[1])), input_dropoff_lng=Decimal(str(c3[2])),
                input_cycle_used_hours=Decimal(str(round(random.uniform(5, 40), 1))),
                total_trip_distance_miles=Decimal(str(distance)),
                total_trip_duration_hours=Decimal(str(round(driving_hrs * 1.5, 1))),
                total_driving_hours=Decimal(str(driving_hrs)),
                calculated_trip_days=trip_days,
                remaining_cycle_hours=Decimal(str(round(70 - driving_hrs, 1))),
            )

            Stop.objects.create(
                trip=trip, type=StopType.WAYPOINT, sequence_number=1,
                location_lat=Decimal(str(c1[1])), location_lng=Decimal(str(c1[2])),
                address_text=c1[0], duration_minutes=0,
            )
            Stop.objects.create(
                trip=trip, type=StopType.FUEL, sequence_number=2,
                location_lat=Decimal(str((c1[1]+c2[1])/2)), location_lng=Decimal(str((c1[2]+c2[2])/2)),
                address_text="Fuel Stop", duration_minutes=30,
            )
            Stop.objects.create(
                trip=trip, type=StopType.FINAL_DROPOFF, sequence_number=3,
                location_lat=Decimal(str(c3[1])), location_lng=Decimal(str(c3[2])),
                address_text=c3[0], duration_minutes=0,
            )

            sheet = DailyLogSheet.objects.create(
                trip=trip, log_date=date.today(),
                day_number_in_trip=1,
                total_driving_hours_day=Decimal(str(min(driving_hrs, 11))),
                total_on_duty_nd_hours_day=Decimal("1.5"),
                total_off_duty_hours_day=Decimal(str(round(24 - min(driving_hrs, 11) - 1.5, 1))),
                carrier_name="Swift Logistics",
                driver_name=f"{driver.first_name} {driver.last_name}" if driver else "",
            )
            DutyStatusSegment.objects.create(
                daily_log_sheet=sheet,
                start_time=datetime.now(timezone.utc).replace(hour=6, minute=0),
                end_time=datetime.now(timezone.utc).replace(hour=17, minute=0),
                status=DutyStatus.DRIVING, duration_minutes=int(min(driving_hrs, 11) * 60),
                segment_label=f"Driving {c1[0]} to {c3[0]}", sequence_in_day=1,
            )

        self.stdout.write("Creating sample pending invitations...")
        for i, (email, role) in enumerate([
            ("pending1@trucking.com", MemberRole.DRIVER),
            ("pending2@trucking.com", MemberRole.DISPATCHER),
            ("pending3@trucking.com", MemberRole.VIEWER),
        ]):
            Invitation.objects.create(
                organization=orgs[0], invited_by=admin_user,
                email=email, role=role, token_hash=f"seed_placeholder_{i}",
                status=InvitationStatus.PENDING,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                personal_message="Welcome to Swift Logistics!",
            )

        self.stdout.write("Creating audit log entries...")
        for action in [AuditAction.ORG_CREATED, AuditAction.INVITATION_SENT,
                       AuditAction.INVITATION_ACCEPTED, AuditAction.VEHICLE_ASSIGNED,
                       AuditAction.TRIP_CREATED]:
            AuditLog.objects.create(
                organization=orgs[0], actor_user=admin_user,
                action=action, metadata={"seed": True},
            )

        total_users = CustomUser.objects.count()
        total_members = OrganizationMember.objects.count()
        total_vehicles = Vehicle.objects.count()
        total_trips = Trip.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed complete!\n"
            f"  Organizations: {Organization.objects.count()}\n"
            f"  Users: {total_users} (incl. superadmin)\n"
            f"  Org Members: {total_members}\n"
            f"  Vehicles: {total_vehicles}\n"
            f"  Trips: {total_trips}\n"
            f"  Invitations: {Invitation.objects.count()}\n"
            f"  Audit Logs: {AuditLog.objects.count()}\n"
            f"\n  All users password: {SEED_PASSWORD}\n"
            f"  Superadmin: superadmin@spotter.ai / {SEED_PASSWORD}\n"
        ))
