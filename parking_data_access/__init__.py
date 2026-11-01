"""Data access component -- part of C.1.2 External Data Acquisition Module.

Sits behind the A1 interface its ICOMs define (contracts/api-v1.yaml,
prepareEligibleParkingInformation): A1 sends an Availability Data Request or
an Updated Availability Request to Parking Availability Data Sources (X.C.2)
and receives Parking Availability Data (a list of SensorEvent) or Updated
Parking Availability. This component makes that exchange: it pulls the
source's events, stores them in the schema.sql database after the SPEC Data
Contract section 1 field checks, and answers with the latest stored event per
space at or before the decision time.

It does not judge freshness. Staleness (SR-09, 120 s) is decided by A1.3
Validate Parking and Context Information from each event's timestamp.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import parking_availability_data_sources as source

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
STATUSES = ("occupied", "vacant", "unknown")
EVENT_FIELDS = ("space_id", "lot_id", "zone", "status", "timestamp")
FUTURE_TOLERANCE = timedelta(seconds=5)  # SPEC Data Contract section 1


def _parse_offset_aware(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


class ParkingDataStore:
    """SQLite store of pilot lot metadata and simulated sensor events."""

    def __init__(self, path: str = ":memory:", data_source=source):
        self._source = data_source
        self._db = sqlite3.connect(path)
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(SCHEMA_PATH.read_text())
        self.load_inventory(data_source.get_lot_inventory(), data_source.get_space_inventory())

    def load_inventory(self, lots: list[dict], spaces: list[dict]) -> None:
        """Store lot and space metadata; space counts must reconcile with capacity_by_zone."""
        for lot in lots:
            counted = {zone: 0 for zone in lot["capacity_by_zone"]}
            for space in spaces:
                if space["lot_id"] == lot["lot_id"]:
                    if space["zone"] not in counted:
                        raise ValueError(f"{space['space_id']} is in an undeclared zone {space['zone']}")
                    counted[space["zone"]] += 1
            if counted != lot["capacity_by_zone"]:
                raise ValueError(f"{lot['lot_id']} space inventory does not reconcile with capacity_by_zone")
        with self._db:
            for lot in lots:
                self._db.execute(
                    "INSERT OR REPLACE INTO lots VALUES (?, ?, ?, ?, ?, ?)",
                    (lot["lot_id"], lot["name"], lot["latitude"], lot["longitude"],
                     lot["source_type"], lot["reviewed_at"]))
                for zone, capacity in lot["capacity_by_zone"].items():
                    self._db.execute("INSERT OR REPLACE INTO lot_zone_capacity VALUES (?, ?, ?)",
                                     (lot["lot_id"], zone, capacity))
            self._db.executemany("INSERT OR REPLACE INTO spaces VALUES (?, ?, ?)",
                                 [(s["space_id"], s["lot_id"], s["zone"]) for s in spaces])

    def _rejection_reason(self, event: dict, received_at: datetime) -> str | None:
        if not isinstance(event, dict) or any(field not in event for field in EVENT_FIELDS):
            return "missing_field"
        row = self._db.execute("SELECT lot_id, zone FROM spaces WHERE space_id = ?",
                               (event["space_id"],)).fetchone()
        if row is None:
            return "unknown_space"
        if row != (event["lot_id"], event["zone"]):
            return "lot_or_zone_mismatch"
        if event["status"] not in STATUSES:
            return "invalid_status"
        observed = _parse_offset_aware(event["timestamp"])
        if observed is None:
            return "invalid_timestamp"
        if observed > received_at + FUTURE_TOLERANCE:
            return "future_timestamp"
        return None

    def ingest(self, events: list[dict], received_at: datetime) -> int:
        """Store valid events; record the others in rejected_events. Returns the number rejected."""
        rejected = 0
        with self._db:
            for event in events:
                reason = self._rejection_reason(event, received_at)
                if reason is not None:
                    rejected += 1
                    space_id = event.get("space_id") if isinstance(event, dict) else None
                    self._db.execute("INSERT INTO rejected_events VALUES (?, ?, ?)",
                                     (received_at.isoformat(), space_id, reason))
                    continue
                observed = _parse_offset_aware(event["timestamp"])
                self._db.execute(
                    "INSERT OR IGNORE INTO sensor_events VALUES (?, ?, ?, ?, ?, ?)",
                    (event["space_id"], event["lot_id"], event["zone"], event["status"],
                     event["timestamp"], observed.timestamp()))
        return rejected

    def latest_events(self, lot_ids: list[str], as_of: datetime) -> list[dict]:
        """Latest stored event per space at or before as_of. A late event never replaces a newer one."""
        placeholders = ", ".join("?" for _ in lot_ids)
        rows = self._db.execute(
            f"""SELECT e.space_id, e.lot_id, e.zone, e.status, e.timestamp
                FROM sensor_events e
                JOIN (SELECT space_id, MAX(observed_epoch) AS latest
                      FROM sensor_events
                      WHERE lot_id IN ({placeholders}) AND observed_epoch <= ?
                      GROUP BY space_id) x
                  ON e.space_id = x.space_id AND e.observed_epoch = x.latest
                ORDER BY e.space_id""",
            (*lot_ids, as_of.timestamp())).fetchall()
        return [dict(zip(EVENT_FIELDS, row)) for row in rows]

    def rejected_events(self) -> list[dict]:
        rows = self._db.execute("SELECT received_at, space_id, reason FROM rejected_events").fetchall()
        return [dict(zip(("received_at", "space_id", "reason"), row)) for row in rows]

    def request_parking_availability(self, availability_data_request: dict) -> list[dict]:
        """Availability Data Request -> Parking Availability Data (list of SensorEvent).

        availability_data_request: {"lot_ids": [...], "as_of": offset-aware ISO 8601}.
        """
        as_of = datetime.fromisoformat(availability_data_request["as_of"])
        lot_ids = availability_data_request["lot_ids"]
        events = self._source.get_current_parking_availability(lot_ids, as_of)
        self.ingest(events, received_at=datetime.now(timezone.utc))
        return self.latest_events(lot_ids, as_of)

    def request_updated_parking_availability(self, updated_availability_request: dict) -> dict:
        """Updated Availability Request -> Updated Parking Availability for one lot.

        updated_availability_request: {"lot_id": ..., "as_of": offset-aware ISO 8601}.
        """
        as_of = datetime.fromisoformat(updated_availability_request["as_of"])
        lot_id = updated_availability_request["lot_id"]
        events = self._source.get_updated_parking_availability(lot_id, as_of)
        self.ingest(events, received_at=datetime.now(timezone.utc))
        return {"lot_id": lot_id, "observations": self.latest_events([lot_id], as_of)}
