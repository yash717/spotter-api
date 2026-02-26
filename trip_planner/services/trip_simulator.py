"""
Master trip orchestrator.

Pipeline: geocode → route → HOS simulation → stops → daily logs → persist
"""

import json
import logging
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone as dj_tz

from trip_planner.constants import TripStatus
from trip_planner.models import HOSViolation, Stop, Trip

from .geocoding import geocode_address
from .hos_calculator import check_violations, compute_driving_segments
from .log_builder import build_daily_logs
from .routing import get_multi_leg_route

logger = logging.getLogger(__name__)

PICKUP_DURATION_HOURS = 1.0
DROPOFF_DURATION_HOURS = 1.0
AVG_SPEED_MPH = 55.0


@transaction.atomic
def plan_trip(
    organization,
    created_by,
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    cycle_used_hours: float,
    planned_start_datetime: datetime | None = None,
    assigned_driver=None,
    vehicle=None,
) -> Trip:
    """
    Runs the full trip planning pipeline and persists results.
    """
    # 1. Geocode all three locations
    current_geo = geocode_address(current_location)
    pickup_geo = geocode_address(pickup_location)
    dropoff_geo = geocode_address(dropoff_location)

    if not all([current_geo, pickup_geo, dropoff_geo]):
        failed = []
        if not current_geo:
            failed.append("current location")
        if not pickup_geo:
            failed.append("pickup location")
        if not dropoff_geo:
            failed.append("dropoff location")
        raise ValueError(f"Could not geocode: {', '.join(failed)}")

    # 2. Get multi-leg route
    waypoints = [
        (current_geo["lat"], current_geo["lng"]),
        (pickup_geo["lat"], pickup_geo["lng"]),
        (dropoff_geo["lat"], dropoff_geo["lng"]),
    ]
    route = get_multi_leg_route(waypoints)
    if not route:
        raise ValueError("Could not compute driving route between the locations.")

    total_distance = route["distance_miles"]

    # 3. HOS simulation
    segments = compute_driving_segments(
        total_distance_miles=total_distance,
        cycle_used_hours=cycle_used_hours,
        avg_speed_mph=AVG_SPEED_MPH,
    )

    total_driving = sum(s["duration_hours"] for s in segments if s["type"] == "driving")
    total_on_duty = sum(s["duration_hours"] for s in segments if s["type"] == "on_duty_nd")
    total_off_duty = sum(
        s["duration_hours"] for s in segments if s["type"] in ("off_duty", "sleeper")
    )
    total_duration = total_driving + total_on_duty + total_off_duty
    trip_days = max(1, int(total_duration / 24) + (1 if total_duration % 24 > 0 else 0))

    cycle_exhausted = any(s.get("type") == "violation" for s in segments)
    remaining_cycle = max(0, 70 - cycle_used_hours - total_driving - total_on_duty)

    start_dt = planned_start_datetime or dj_tz.now()

    # 4. Create Trip record
    trip = Trip.objects.create(
        organization=organization,
        assigned_driver=assigned_driver,
        created_by=created_by,
        vehicle=vehicle,
        input_current_lat=Decimal(str(current_geo["lat"])),
        input_current_lng=Decimal(str(current_geo["lng"])),
        input_pickup_lat=Decimal(str(pickup_geo["lat"])),
        input_pickup_lng=Decimal(str(pickup_geo["lng"])),
        input_dropoff_lat=Decimal(str(dropoff_geo["lat"])),
        input_dropoff_lng=Decimal(str(dropoff_geo["lng"])),
        input_current_address=current_geo.get("canonical_address", current_location),
        input_pickup_address=pickup_geo.get("canonical_address", pickup_location),
        input_dropoff_address=dropoff_geo.get("canonical_address", dropoff_location),
        input_cycle_used_hours=Decimal(str(cycle_used_hours)),
        remaining_cycle_hours=Decimal(str(round(remaining_cycle, 1))),
        total_trip_distance_miles=Decimal(str(round(total_distance, 1))),
        total_trip_duration_hours=Decimal(str(round(total_duration, 1))),
        total_driving_hours=Decimal(str(round(total_driving, 1))),
        calculated_trip_days=trip_days,
        route_polyline_json=json.dumps(route.get("geometry", {})),
        cycle_exhausted_mid_trip=cycle_exhausted,
        status=TripStatus.DRAFT,
        planned_start_datetime=start_dt,
    )

    # 5. Create stops from route and simulation
    _create_stops(trip, segments, waypoints, start_dt)

    # 6. Build daily log sheets
    build_daily_logs(trip, segments, start_dt)

    # 7. Record violations
    violations = check_violations(total_driving, total_on_duty, cycle_used_hours, segments)
    for v in violations:
        HOSViolation.objects.create(
            trip=trip,
            violation_type=v["type"],
            description=v["description"],
            severity=v["severity"],
        )

    return trip


def _create_stops(trip, segments, waypoints, start_dt):
    """Creates Stop records from simulation segments."""
    from datetime import timedelta

    current_time = start_dt
    seq = 0
    cumulative_miles = 0
    start_odometer = float(trip.vehicle.odometer_current) if trip.vehicle else 0

    # Initial current location stop
    seq += 1
    Stop.objects.create(
        trip=trip,
        type="waypoint",
        sequence_number=seq,
        location_lat=Decimal(str(waypoints[0][0])),
        location_lng=Decimal(str(waypoints[0][1])),
        address_text=trip.input_current_address,
        scheduled_arrival_time=current_time,
        scheduled_departure_time=current_time,
        duration_minutes=0,
        odometer_at_stop=Decimal(str(start_odometer)),
        distance_from_prev_stop=Decimal("0"),
        notes="Trip start - current location",
    )

    for seg in segments:
        duration_td = timedelta(hours=seg["duration_hours"])
        seg_end = current_time + duration_td
        miles = seg.get("miles", 0)
        cumulative_miles += miles

        if seg["type"] == "driving":
            current_time = seg_end
            continue

        if seg["type"] in ("off_duty", "on_duty_nd", "sleeper"):
            seq += 1
            stop_type = "waypoint"
            if (
                "mandatory rest" in seg.get("notes", "").lower()
                or "10-hour" in seg.get("notes", "").lower()
            ):
                stop_type = "rest_10hr"
            elif (
                "30-minute" in seg.get("notes", "").lower()
                or "break" in seg.get("notes", "").lower()
            ):
                stop_type = "rest_30min"
            elif "fuel" in seg.get("notes", "").lower():
                stop_type = "fuel"

            lat, lng = _interpolate_position(
                waypoints, cumulative_miles, float(trip.total_trip_distance_miles or 1)
            )

            Stop.objects.create(
                trip=trip,
                type=stop_type,
                sequence_number=seq,
                location_lat=Decimal(str(lat)),
                location_lng=Decimal(str(lng)),
                address_text=seg.get("notes", ""),
                scheduled_arrival_time=current_time,
                scheduled_departure_time=seg_end,
                duration_minutes=int(seg["duration_hours"] * 60),
                odometer_at_stop=Decimal(str(round(start_odometer + cumulative_miles, 1))),
                distance_from_prev_stop=Decimal(str(round(miles, 1))),
                notes=seg.get("notes", ""),
                is_hos_mandated=seg.get("is_hos_mandated", False),
            )

        current_time = seg_end

    # Final dropoff stop
    seq += 1
    Stop.objects.create(
        trip=trip,
        type="final_dropoff",
        sequence_number=seq,
        location_lat=trip.input_dropoff_lat,
        location_lng=trip.input_dropoff_lng,
        address_text=trip.input_dropoff_address,
        scheduled_arrival_time=current_time,
        scheduled_departure_time=current_time,
        duration_minutes=0,
        odometer_at_stop=Decimal(str(round(start_odometer + cumulative_miles, 1))),
        distance_from_prev_stop=Decimal("0"),
        notes="Final dropoff",
    )


def _interpolate_position(waypoints, miles_traveled, total_miles):
    """Rough linear interpolation along waypoint chain."""
    if total_miles <= 0 or not waypoints:
        return waypoints[0] if waypoints else (0, 0)

    ratio = min(miles_traveled / total_miles, 1.0)
    n = len(waypoints) - 1
    idx = ratio * n
    lower = int(idx)
    upper = min(lower + 1, n)
    frac = idx - lower

    lat = waypoints[lower][0] + frac * (waypoints[upper][0] - waypoints[lower][0])
    lng = waypoints[lower][1] + frac * (waypoints[upper][1] - waypoints[lower][1])
    return (round(lat, 7), round(lng, 7))
