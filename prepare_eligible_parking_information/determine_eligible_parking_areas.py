"""C.1.4 Eligibility Filter Module -- A1.4 Determine Eligible Parking Areas.

Generated once from prompts/2026-10-31-c14-eligibility-filter.md (Lab Manual
§9.4, commit d90bf3f), then corrected per docs/deviation-log.md. Requirements: C.1 1.4.4, 1.1.7, 1.2.8, 2.1.2; DO-04; NFR.4; SR-10.

An area is returned only when confirmed rules allow every class the trip
needs (its declared eligibility, plus "accessible" when access_needs is true)
for the whole interval [arrival_time, departure_time), and no closure covers
any part of that interval. An area no rule resolves is left out (DO-04).
Freshness, forecasting, ranking and presentation belong to A1.3, A2, A3 and A4.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TRIP_FIELDS = (
    "destination",
    "arrival_time",
    "departure_time",
    "vehicle_category",
    "declared_eligibility",
    "access_needs",
)
RULE_FIELDS = ("lot_id", "eligibility_class", "allowed", "closure")
DEFAULT_TIME_ZONE = "America/New_York"
WILDCARD = "*"
MINUTES_PER_DAY = 24 * 60


def _offset_aware(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _clock_minutes(value) -> int | None:
    """"HH:MM" as minutes after midnight; "24:00" is the end of the day."""
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return None
    hours, minutes = value[:2], value[3:]
    if not (hours.isdigit() and minutes.isdigit()):
        return None
    total = int(hours) * 60 + int(minutes)
    if int(minutes) > 59 or total > MINUTES_PER_DAY:
        return None
    return total


def _rule_windows(rule: dict, start: datetime, end: datetime) -> list[tuple[datetime, datetime]] | None:
    """The windows in which the rule is in force and that overlap [start, end).

    Returns None if any optional §4 field is present but cannot be parsed.
    """
    try:
        zone = ZoneInfo(rule.get("time_zone", DEFAULT_TIME_ZONE))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return None
    days = rule.get("days_of_week", list(range(1, 8)))
    if not isinstance(days, list) or not all(isinstance(day, int) and 1 <= day <= 7 for day in days):
        return None
    try:
        valid_from = date.fromisoformat(rule["valid_from"]) if "valid_from" in rule else None
        valid_until = date.fromisoformat(rule["valid_until"]) if "valid_until" in rule else None
    except (TypeError, ValueError):
        return None
    opens = _clock_minutes(rule.get("start_local_time", "00:00"))
    closes = _clock_minutes(rule.get("end_local_time", "24:00"))
    # A window that starts and ends at the same time is invalid (deviation log row 5).
    if opens is None or closes is None or opens == closes:
        return None

    windows = []
    # A window that runs past midnight belongs to the day it starts, so look
    # back one day before the trip's first local date.
    day = start.astimezone(zone).date() - timedelta(days=1)
    last_day = end.astimezone(zone).date()
    while day <= last_day:
        in_force = (day.isoweekday() in days
                    and (valid_from is None or day >= valid_from)
                    and (valid_until is None or day <= valid_until))
        if in_force:
            midnight = datetime.combine(day, time())
            window_end_minutes = closes if closes > opens else closes + MINUTES_PER_DAY
            window_start = (midnight + timedelta(minutes=opens)).replace(tzinfo=zone)
            window_end = (midnight + timedelta(minutes=window_end_minutes)).replace(tzinfo=zone)
            if window_start < end and window_end > start:
                windows.append((window_start, window_end))
        day += timedelta(days=1)
    return windows


def _covers(windows: list[tuple[datetime, datetime]], start: datetime, end: datetime) -> bool:
    """Whether the windows together cover every instant of [start, end)."""
    reached = start
    for window_start, window_end in sorted(windows):
        if window_start > reached:
            return False
        reached = max(reached, window_end)
        if reached >= end:
            return True
    return reached >= end


def _is_readable(rule) -> bool:
    return (isinstance(rule, dict)
            and all(field in rule for field in RULE_FIELDS)
            and isinstance(rule["lot_id"], str)
            and isinstance(rule["eligibility_class"], str)
            and isinstance(rule["allowed"], bool)
            and isinstance(rule["closure"], bool)
            and isinstance(rule.get("zone", WILDCARD), str))


def _class_satisfied(trip_class: str, rules: list[tuple[dict, list]], start: datetime, end: datetime) -> bool:
    """Decision rule step 3: some zone allows the class over the whole interval."""
    zones = {rule.get("zone", WILDCARD) for rule, _ in rules} - {WILDCARD} or {WILDCARD}
    for zone in zones:
        applicable = [(rule, windows) for rule, windows in rules
                      if rule["eligibility_class"] in (trip_class, WILDCARD)
                      and rule.get("zone", WILDCARD) in (zone, WILDCARD)]
        if any(not rule["allowed"] and windows for rule, windows in applicable):
            continue
        allowing = [window for rule, windows in applicable
                    if rule["allowed"] and not rule["closure"] for window in windows]
        if _covers(allowing, start, end):
            return True
    return False


def determine_eligible_parking_areas(
    validated_parking_data: list[dict],
    normalized_trip_requirements: dict,
    validated_context_information: list[dict],
    data_quality_and_freshness_status: dict,
    *,
    parking_policy_constraints: dict,
) -> list[dict]:
    """A1.4: the candidate areas whose eligibility confirmed rules resolve for this trip.

    in: validated_parking_data (I-02; candidates are its lot_ids, first-seen order),
    normalized_trip_requirements (the six confirmed fields),
    validated_context_information (I-03; not used in the decision),
    data_quality_and_freshness_status (not used; a stale area is not excluded here).
    control: parking_policy_constraints (E-12, {"rules": [...]}).
    out: Eligible Parking Areas (I-05), [{"lot_id": ...}].
    """
    trip = normalized_trip_requirements
    if not isinstance(trip, dict) or any(field not in trip for field in TRIP_FIELDS):
        return []
    start = _offset_aware(trip["arrival_time"])
    end = _offset_aware(trip["departure_time"])
    # An empty or reversed interval, or a non-boolean access_needs, is an
    # invalid request: nothing is eligible (deviation log rows 2 and 3).
    if start is None or end is None or end <= start or not isinstance(trip["access_needs"], bool):
        return []
    trip_classes = [trip["declared_eligibility"]]
    if trip["access_needs"]:
        trip_classes.append("accessible")

    candidates = []
    for record in validated_parking_data:
        lot_id = record.get("lot_id")
        if lot_id not in candidates:
            candidates.append(lot_id)

    rules = parking_policy_constraints.get("rules", [])
    eligible = []
    for lot_id in candidates:
        closed = False
        readable = []
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("lot_id") != lot_id:
                continue
            windows = _rule_windows(rule, start, end) if _is_readable(rule) else None
            if windows is None:
                # An unreadable rule resolves nothing, but an unreadable closure
                # must not be read as "open".
                if rule.get("closure") is True:
                    closed = True
                continue
            if rule["closure"] and windows:
                closed = True
            readable.append((rule, windows))
        if closed:
            continue
        if all(_class_satisfied(trip_class, readable, start, end) for trip_class in trip_classes):
            eligible.append({"lot_id": lot_id})
    return eligible
