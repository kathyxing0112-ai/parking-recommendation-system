"""Parking Availability Data Sources (X.C.2) -- simulated sensor feed.

The pilot has no live Cornell sensor API (SPEC.md scope), so this external
source is a seeded simulator. It reports one SPEC Data Contract section 1
sensor event per space, and the pilot lot inventory in the section 3 shape.
Every lot, capacity and occupancy value here is a simulator assumption, not
Cornell inventory or observed data (source_type "simulated_inventory").

The system reaches this source only through the data access component
(parking_data_access); see docs/deployment.md.
"""

import random
from datetime import datetime, timedelta

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

# Weekday occupancy rate by local hour; weekends use WEEKEND_FACTOR of it.
HOURLY_RATE = [0.10] * 7 + [0.35, 0.65, 0.85, 0.92, 0.93, 0.90, 0.90, 0.88, 0.80, 0.60, 0.40] + [0.20] * 6
WEEKEND_FACTOR = 0.4


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


def _occupancy_rate(lot: dict, at: datetime) -> float:
    # Straight line between hourly rates, so the rate moves every slot.
    this_hour, next_hour = HOURLY_RATE[at.hour], HOURLY_RATE[(at.hour + 1) % 24]
    rate = this_hour + (next_hour - this_hour) * at.minute / 60
    if at.weekday() >= 5:
        rate *= WEEKEND_FACTOR
    return min(max(rate + lot["occupancy_offset"], 0.0), 1.0)


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
    lots = {lot["lot_id"]: lot for lot in PILOT_LOTS}
    events = []
    for space in get_space_inventory():
        if space["lot_id"] not in lot_ids:
            continue
        # Each space keeps one number for the whole day, so a parked car stays
        # parked between slots and the lot fills and empties gradually.
        day_draw = random.Random(f"{SIMULATOR_SEED}|{space['space_id']}|{slot_start.date()}").random()
        slot_draw = random.Random(f"{SIMULATOR_SEED}|{space['space_id']}|{slot_start.isoformat()}").random()
        if day_draw + SLOT_JITTER * (slot_draw - 0.5) < _occupancy_rate(lots[space["lot_id"]], slot_start):
            status = "occupied"
        else:
            status = "vacant"
        events.append({**space, "status": status, "timestamp": reported_at.isoformat()})
    return events


def get_updated_parking_availability(lot_id: str, as_of: datetime) -> list[dict]:
    """UC.1.19 Request / UC.1.20 Provide Updated Parking Availability for one lot."""
    return get_current_parking_availability([lot_id], as_of)
