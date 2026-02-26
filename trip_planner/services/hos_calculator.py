"""
HOS (Hours of Service) calculator implementing FMCSA rules.

Rules:
  1. 11-hour driving limit per shift
  2. 14-hour on-duty window per shift
  3. 30-minute break after 8 hours cumulative driving
  4. 10-hour off-duty reset clears rules 1 + 2
  5. 70-hour / 8-day cycle limit
"""

from dataclasses import dataclass


@dataclass
class HOSState:
    driving_hours: float = 0.0
    on_duty_hours: float = 0.0
    hours_since_last_break: float = 0.0
    cycle_hours: float = 0.0
    shift_elapsed: float = 0.0

    MAX_DRIVING = 11.0
    MAX_SHIFT_WINDOW = 14.0
    BREAK_THRESHOLD = 8.0
    BREAK_DURATION = 0.5
    RESET_DURATION = 10.0
    MAX_CYCLE = 70.0

    @property
    def remaining_driving(self) -> float:
        return max(0, self.MAX_DRIVING - self.driving_hours)

    @property
    def remaining_window(self) -> float:
        return max(0, self.MAX_SHIFT_WINDOW - self.shift_elapsed)

    @property
    def remaining_cycle(self) -> float:
        return max(0, self.MAX_CYCLE - self.cycle_hours)

    @property
    def time_until_break(self) -> float:
        return max(0, self.BREAK_THRESHOLD - self.hours_since_last_break)

    @property
    def max_drivable_now(self) -> float:
        """Max hours drivable right now before any rule is hit."""
        return min(
            self.remaining_driving,
            self.remaining_window,
            self.remaining_cycle,
            self.time_until_break,
        )

    def needs_break(self) -> bool:
        return self.hours_since_last_break >= self.BREAK_THRESHOLD

    def needs_reset(self) -> bool:
        return self.remaining_driving <= 0 or self.remaining_window <= 0

    def cycle_exhausted(self) -> bool:
        return self.remaining_cycle <= 0

    def apply_driving(self, hours: float):
        self.driving_hours += hours
        self.on_duty_hours += hours
        self.hours_since_last_break += hours
        self.cycle_hours += hours
        self.shift_elapsed += hours

    def apply_on_duty_not_driving(self, hours: float):
        self.on_duty_hours += hours
        self.cycle_hours += hours
        self.shift_elapsed += hours

    def apply_break(self):
        self.hours_since_last_break = 0
        self.shift_elapsed += self.BREAK_DURATION

    def apply_reset(self):
        self.driving_hours = 0
        self.on_duty_hours = 0
        self.hours_since_last_break = 0
        self.shift_elapsed = 0


def compute_driving_segments(
    total_distance_miles: float,
    cycle_used_hours: float,
    avg_speed_mph: float = 55.0,
) -> list[dict]:
    """
    Simulates a trip by breaking it into segments honoring HOS rules.
    Returns a list of segment dicts:
      {type, duration_hours, miles, hos_state_snapshot, notes}
    """
    state = HOSState(cycle_hours=cycle_used_hours)
    segments = []
    miles_remaining = total_distance_miles
    segment_seq = 0

    FUEL_INTERVAL_MILES = 1000.0
    FUEL_STOP_DURATION = 0.5
    miles_since_fuel = 0.0
    PICKUP_DURATION = 1.0
    DROPOFF_DURATION = 1.0

    # Pre-trip inspection (on-duty, not driving)
    segment_seq += 1
    state.apply_on_duty_not_driving(0.25)
    segments.append(
        {
            "sequence": segment_seq,
            "type": "on_duty_nd",
            "duration_hours": 0.25,
            "miles": 0,
            "notes": "Pre-trip inspection",
        }
    )

    while miles_remaining > 0.01:
        if state.cycle_exhausted():
            segments.append(
                {
                    "sequence": segment_seq + 1,
                    "type": "violation",
                    "duration_hours": 0,
                    "miles": 0,
                    "notes": f"70-hour cycle exhausted with {miles_remaining:.1f} miles remaining",
                }
            )
            break

        if state.needs_reset():
            segment_seq += 1
            state.apply_reset()
            segments.append(
                {
                    "sequence": segment_seq,
                    "type": "off_duty",
                    "duration_hours": HOSState.RESET_DURATION,
                    "miles": 0,
                    "notes": "10-hour mandatory rest (reset driving & window)",
                    "is_hos_mandated": True,
                }
            )
            # Pre-trip after rest
            segment_seq += 1
            state.apply_on_duty_not_driving(0.25)
            segments.append(
                {
                    "sequence": segment_seq,
                    "type": "on_duty_nd",
                    "duration_hours": 0.25,
                    "miles": 0,
                    "notes": "Pre-trip inspection after rest",
                }
            )
            continue

        if state.needs_break():
            segment_seq += 1
            state.apply_break()
            segments.append(
                {
                    "sequence": segment_seq,
                    "type": "off_duty",
                    "duration_hours": HOSState.BREAK_DURATION,
                    "miles": 0,
                    "notes": "30-minute mandatory break (8hr driving threshold)",
                    "is_hos_mandated": True,
                }
            )
            continue

        drivable_hours = state.max_drivable_now
        if drivable_hours <= 0:
            continue

        drivable_miles = drivable_hours * avg_speed_mph
        drive_miles = min(miles_remaining, drivable_miles)

        # Check fuel stop
        if miles_since_fuel + drive_miles >= FUEL_INTERVAL_MILES:
            drive_miles = FUEL_INTERVAL_MILES - miles_since_fuel
            needs_fuel_after = True
        else:
            needs_fuel_after = False

        drive_hours = drive_miles / avg_speed_mph

        segment_seq += 1
        state.apply_driving(drive_hours)
        miles_remaining -= drive_miles
        miles_since_fuel += drive_miles

        segments.append(
            {
                "sequence": segment_seq,
                "type": "driving",
                "duration_hours": round(drive_hours, 2),
                "miles": round(drive_miles, 1),
                "notes": f"Driving ({drive_miles:.1f} mi)",
            }
        )

        if needs_fuel_after and miles_remaining > 0.01:
            segment_seq += 1
            state.apply_on_duty_not_driving(FUEL_STOP_DURATION)
            miles_since_fuel = 0.0
            segments.append(
                {
                    "sequence": segment_seq,
                    "type": "on_duty_nd",
                    "duration_hours": FUEL_STOP_DURATION,
                    "miles": 0,
                    "notes": "Fuel stop",
                }
            )

    return segments


def check_violations(
    total_driving_hours: float,
    total_on_duty_hours: float,
    cycle_used_hours: float,
    segments: list[dict],
) -> list[dict]:
    """
    Scans segment list for HOS violations that couldn't be avoided.
    Returns list of violation dicts.
    """
    violations = []

    total_cycle = cycle_used_hours + total_driving_hours + total_on_duty_hours
    if total_cycle > HOSState.MAX_CYCLE:
        violations.append(
            {
                "type": "cycle_limit_exceeded",
                "severity": "critical",
                "description": (
                    f"70-hour cycle limit would be exceeded. Total cycle hours: {total_cycle:.1f}"
                ),
            }
        )

    for seg in segments:
        if seg.get("type") == "violation":
            violations.append(
                {
                    "type": "cycle_limit_exceeded",
                    "severity": "critical",
                    "description": seg.get("notes", "HOS violation detected"),
                }
            )

    return violations
