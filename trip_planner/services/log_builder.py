"""
Builds DailyLogSheet and DutyStatusSegment records from trip simulation output.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from trip_planner.constants import DutyStatus
from trip_planner.models import DailyLogSheet, DutyStatusSegment

logger = logging.getLogger(__name__)

STATUS_MAP = {
    "driving": DutyStatus.DRIVING,
    "on_duty_nd": DutyStatus.ON_DUTY_ND,
    "off_duty": DutyStatus.OFF_DUTY,
    "sleeper": DutyStatus.SLEEPER_BERTH,
}


def build_daily_logs(trip, segments: list[dict], start_dt: datetime) -> list[DailyLogSheet]:
    """
    Takes simulated segments and creates DailyLogSheet + DutyStatusSegment records.
    Splits segments at midnight boundaries into separate days.
    """
    if not segments:
        return []

    current_time = start_dt
    timed_segments = []

    for seg in segments:
        duration_hours = seg.get("duration_hours", 0)
        end_time = current_time + timedelta(hours=duration_hours)
        timed_segments.append({
            **seg,
            "start_time": current_time,
            "end_time": end_time,
        })
        current_time = end_time

    days = _group_by_day(timed_segments, start_dt)

    log_sheets = []
    cumulative_hos = float(trip.input_cycle_used_hours or 0)
    start_odometer = float(trip.vehicle.odometer_current) if trip.vehicle else 0

    for day_num, (log_date, day_segments) in enumerate(sorted(days.items()), start=1):
        day_driving = sum(
            s["duration_hours"] for s in day_segments if s["type"] == "driving"
        )
        day_on_duty = sum(
            s["duration_hours"] for s in day_segments if s["type"] == "on_duty_nd"
        )
        day_off_duty = sum(
            s["duration_hours"] for s in day_segments if s["type"] == "off_duty"
        )
        day_sleeper = sum(
            s["duration_hours"] for s in day_segments if s["type"] == "sleeper"
        )
        day_miles = sum(s.get("miles", 0) for s in day_segments)

        hos_start = cumulative_hos
        cumulative_hos += day_driving + day_on_duty
        hos_end = cumulative_hos

        carrier_name = ""
        driver_name = ""
        vehicle_numbers = ""

        if trip.organization:
            carrier_name = trip.organization.name
        if trip.assigned_driver:
            profile = getattr(trip.assigned_driver, "driver_profile", None)
            driver_name = profile.full_name if profile else ""
        if trip.vehicle:
            vehicle_numbers = f"{trip.vehicle.truck_number}"
            if trip.vehicle.trailer_number:
                vehicle_numbers += f" / {trip.vehicle.trailer_number}"

        log_sheet = DailyLogSheet.objects.create(
            trip=trip,
            log_date=log_date,
            day_number_in_trip=day_num,
            total_driving_hours_day=Decimal(str(round(day_driving, 1))),
            total_on_duty_nd_hours_day=Decimal(str(round(day_on_duty, 1))),
            total_sleeper_hours_day=Decimal(str(round(day_sleeper, 1))),
            total_off_duty_hours_day=Decimal(str(round(day_off_duty, 1))),
            cumulative_hos_start=Decimal(str(round(hos_start, 1))),
            cumulative_hos_end=Decimal(str(round(hos_end, 1))),
            start_day_odometer=Decimal(str(round(start_odometer, 1))),
            end_day_odometer=Decimal(str(round(start_odometer + day_miles, 1))),
            carrier_name=carrier_name,
            driver_name=driver_name,
            vehicle_numbers=vehicle_numbers,
        )
        start_odometer += day_miles

        for seq, seg in enumerate(day_segments, start=1):
            DutyStatusSegment.objects.create(
                daily_log_sheet=log_sheet,
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                status=STATUS_MAP.get(seg["type"], "off_duty"),
                duration_minutes=int(seg["duration_hours"] * 60),
                distance_traveled_miles=(
                    Decimal(str(seg.get("miles", 0))) if seg["type"] == "driving" else None
                ),
                segment_label=seg.get("notes", ""),
                sequence_in_day=seq,
            )

        log_sheets.append(log_sheet)

    return log_sheets


def _group_by_day(segments: list[dict], start_dt: datetime) -> dict[date, list]:
    """Groups segments by calendar date, splitting at midnight."""
    days: dict[date, list] = {}

    for seg in segments:
        seg_start = seg["start_time"]
        seg_end = seg["end_time"]
        seg_date = seg_start.date()

        midnight = datetime.combine(
            seg_date + timedelta(days=1), datetime.min.time(), tzinfo=seg_start.tzinfo
        )

        if seg_end <= midnight:
            days.setdefault(seg_date, []).append(seg)
        else:
            # Split at midnight
            first_part = {**seg, "end_time": midnight}
            first_hours = (midnight - seg_start).total_seconds() / 3600
            first_part["duration_hours"] = first_hours
            if seg["type"] == "driving" and seg["duration_hours"] > 0:
                ratio = first_hours / seg["duration_hours"]
                first_part["miles"] = seg.get("miles", 0) * ratio
            days.setdefault(seg_date, []).append(first_part)

            second_part = {**seg, "start_time": midnight}
            second_hours = (seg_end - midnight).total_seconds() / 3600
            second_part["duration_hours"] = second_hours
            if seg["type"] == "driving" and seg["duration_hours"] > 0:
                ratio = second_hours / seg["duration_hours"]
                second_part["miles"] = seg.get("miles", 0) * ratio
            next_date = midnight.date()
            days.setdefault(next_date, []).append(second_part)

    return days
