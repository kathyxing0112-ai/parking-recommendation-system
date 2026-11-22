"""Parking Availability Data Sources (X.C.2) -- simulated sensor feed.

The pilot has no live Cornell sensor API (SPEC.md scope), so this external
source is a seeded simulator. It reports one SPEC Data Contract section 1
sensor event per space, and the pilot lot inventory in the section 3 shape.
Every lot, capacity and occupancy value here is a simulator assumption, not
Cornell inventory or observed data (source_type "simulated_inventory").

Occupancy follows a class-day hourly profile, lowered on weekends and
no-class weekdays, raised when precipitation falls and during major campus
events, with a slow per-lot drift. Calendar, events and the weather forecast
come from contextual_information_sources (X.C.3).

The system reaches this source only through the data access component
(parking_data_access); see docs/deployment.md.
"""

import random
import threading
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import contextual_information_sources as context

SIMULATOR_SEED = 5151
FEED_INTERVAL_SECONDS = 30   # SR-08: the simulated feed targets one update every 30 s
OCCUPANCY_SLOT_MINUTES = 5   # occupancy changes once per 5-minute slot
SLOT_JITTER = 0.12           # a few spaces change every slot even when the rate is flat

ZONE_CODES = {"permit_O": "O", "visitor": "V", "accessible": "A"}

# Simulator assumptions, labeled as such (SPEC Data Contract section 3).
# Names are real Cornell parking areas; zone mix follows public Cornell
# sources where found (Peterson Lot is an hourly pay lot in the August 2026
# Parkmobile map). Capacities and coordinates are simulated, not Cornell
# inventory. The mapping was agreed by the team on 2026-11-01.
PILOT_LOTS = [
    {"lot_id": "LOT-1", "name": "Hoy Road Garage", "latitude": 42.4440, "longitude": -76.4820,
     "capacity_by_zone": {"permit_O": 150, "visitor": 40, "accessible": 10},
     "occupancy_offset": 0.05},
    {"lot_id": "LOT-2", "name": "Peterson Lot", "latitude": 42.4460, "longitude": -76.4790,
     "capacity_by_zone": {"permit_O": 0, "visitor": 110, "accessible": 10},
     "occupancy_offset": 0.0},
    {"lot_id": "LOT-3", "name": "Robert Purcell Community Center Parking Lot", "latitude": 42.4490, "longitude": -76.4760,
     "capacity_by_zone": {"permit_O": 140, "visitor": 0, "accessible": 10},
     "occupancy_offset": -0.10},
]
INVENTORY_REVIEWED_AT = "2026-10-28T09:00:00-04:00"

LOCAL_TIME = ZoneInfo("America/New_York")

# Simulator assumptions (not observed Cornell data). Class-day occupancy rate
# by local hour; a weekend uses WEEKEND_FACTOR of it and a weekday with no
# classes (holiday or break) uses BREAK_FACTOR.
HOURLY_RATE = [0.10] * 7 + [0.35, 0.65, 0.85, 0.92, 0.93, 0.90, 0.90, 0.88, 0.80, 0.60, 0.40] + [0.20] * 6
WEEKEND_FACTOR = 0.4
BREAK_FACTOR = 0.5
# Precipitation that actually falls brings more cars (fewer people walk or bike).
RAIN_FACTOR = 1.06
SNOW_FACTOR = 1.10
# Each lot drifts above or below its usual level and returns slowly: a
# first-order autoregressive deviation on the 5-minute slot grid, relative to
# the usual rate. Recent occupancy therefore says something about the next
# few hours but little about the next day.
DRIFT_START = datetime(2026, 8, 24, tzinfo=LOCAL_TIME)
DRIFT_HALF_LIFE_MINUTES = 90
DRIFT_SD = 0.08
_DRIFT_PHI = 0.5 ** (OCCUPANCY_SLOT_MINUTES / DRIFT_HALF_LIFE_MINUTES)
_drift_paths: dict = {}
_drift_lock = threading.Lock()


def get_lot_inventory() -> list[dict]:
    """Pilot lot metadata in the SPEC Data Contract section 3 shape."""
    return [
        {
            "lot_id": lot["lot_id"],
            "name": lot["name"],
            "latitude": lot["latitude"],
            "longitude": lot["longitude"],
            "capacity_by_zone": dict(lot["capacity_by_zone"]),
            "source_type": "simulated_inventory",
            "reviewed_at": INVENTORY_REVIEWED_AT,
        }
        for lot in PILOT_LOTS
    ]


def get_space_inventory() -> list[dict]:
    """Each space_id mapped to exactly one lot_id and zone."""
    spaces = []
    for number, lot in enumerate(PILOT_LOTS, start=1):
        for zone, capacity in lot["capacity_by_zone"].items():
            for index in range(1, capacity + 1):
                spaces.append({
                    "space_id": f"L{number}-{ZONE_CODES[zone]}-{index:03d}",
                    "lot_id": lot["lot_id"],
                    "zone": zone,
                })
    return spaces


def _drift(lot_id: str, at: datetime) -> float:
    """The lot's relative deviation from its usual rate in the slot containing at.

    The path is generated in slot order from DRIFT_START with one seeded
    generator per lot, so a slot's value does not depend on which times were
    asked for before it. Slots before DRIFT_START have no deviation.
    """
    step = int((at - DRIFT_START).total_seconds() // (OCCUPANCY_SLOT_MINUTES * 60))
    if step < 0:
        return 0.0
    with _drift_lock:
        rng, path = _drift_paths.setdefault(
            lot_id, (random.Random(f"{SIMULATOR_SEED}|drift|{lot_id}"), [0.0]))
        innovation_sd = DRIFT_SD * (1 - _DRIFT_PHI ** 2) ** 0.5
        while len(path) <= step:
            path.append(_DRIFT_PHI * path[-1] + rng.gauss(0, innovation_sd))
        return path[step]


def precipitation_fell(day: date) -> bool:
    """Whether precipitation actually fell on a local date, drawn from that day's forecast chance."""
    chance = context.get_weather_forecast(day)["precipitation_probability"]
    return random.Random(f"{SIMULATOR_SEED}|precipitation|{day.isoformat()}").random() < chance


def _occupancy_rate(lot: dict, at: datetime) -> float:
    local = at.astimezone(LOCAL_TIME)
    day = local.date()
    # Straight line between hourly rates, so the rate moves every slot.
    this_hour, next_hour = HOURLY_RATE[local.hour], HOURLY_RATE[(local.hour + 1) % 24]
    rate = this_hour + (next_hour - this_hour) * local.minute / 60
    calendar = context.get_calendar_day(day)
    if calendar["is_weekend"]:
        rate *= WEEKEND_FACTOR
    elif calendar["is_break"]:
        rate *= BREAK_FACTOR
    if precipitation_fell(day):
        rate *= SNOW_FACTOR if context.get_weather_forecast(day)["snow_flag"] else RAIN_FACTOR
    rate = (rate + lot["occupancy_offset"]) * (1 + _drift(lot["lot_id"], at))
    for event in context.get_events(day):
        if lot["lot_id"] in event["lot_ids"] and event["start_hour"] <= local.hour < event["end_hour"]:
            rate += event["occupancy_increase"]
    return min(max(rate, 0.0), 1.0)


def _latest_report_time(as_of: datetime) -> datetime:
    """The feed reports on a 30-second cadence; the newest report at or before as_of."""
    seconds = as_of.second - as_of.second % FEED_INTERVAL_SECONDS
    return as_of.replace(second=seconds, microsecond=0)


def get_current_parking_availability(lot_ids: list[str], as_of: datetime) -> list[dict]:
    """UC.1.4 Request / UC.1.5 Provide Current Parking Availability.

    Returns the feed's latest report for every space in lot_ids, as SPEC Data
    Contract section 1 sensor events. The same seed, lot and time always give
    the same events.
    """
    reported_at = _latest_report_time(as_of)
    slot_start = reported_at - timedelta(
        minutes=reported_at.minute % OCCUPANCY_SLOT_MINUTES, seconds=reported_at.second)
    rates = {lot["lot_id"]: _occupancy_rate(lot, slot_start) for lot in PILOT_LOTS if lot["lot_id"] in lot_ids}
    events = []
    for space in get_space_inventory():
        if space["lot_id"] not in lot_ids:
            continue
        # Each space keeps one number for the whole day, so a parked car stays
        # parked between slots and the lot fills and empties gradually.
        day_draw = random.Random(f"{SIMULATOR_SEED}|{space['space_id']}|{slot_start.date()}").random()
        slot_draw = random.Random(f"{SIMULATOR_SEED}|{space['space_id']}|{slot_start.isoformat()}").random()
        if day_draw + SLOT_JITTER * (slot_draw - 0.5) < rates[space["lot_id"]]:
            status = "occupied"
        else:
            status = "vacant"
        events.append({**space, "status": status, "timestamp": reported_at.isoformat()})
    return events


def get_updated_parking_availability(lot_id: str, as_of: datetime) -> list[dict]:
    """UC.1.19 Request / UC.1.20 Provide Updated Parking Availability for one lot."""
    return get_current_parking_availability([lot_id], as_of)
