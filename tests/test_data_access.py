"""Chapter 8 data access component and simulated X.C.2 feed.

Checks the SPEC Data Contract section 1 and 3 rules the component enforces:
field checks at ingestion, duplicate and late events, the latest event at or
before the decision time, and reproducible simulated data.
"""

from datetime import datetime, timedelta

import pytest

import parking_availability_data_sources as source
from parking_data_access import ParkingDataStore

AS_OF = datetime.fromisoformat("2026-10-02T10:47:15-04:00")
RECEIVED = AS_OF


def event(status="vacant", timestamp="2026-10-02T10:47:00-04:00", **overrides):
    return {"space_id": "L1-O-001", "lot_id": "LOT-1", "zone": "permit_O",
            "status": status, "timestamp": timestamp, **overrides}


def test_simulated_feed_is_reproducible_and_labeled():
    first = source.get_current_parking_availability(["LOT-1", "LOT-2", "LOT-3"], AS_OF)
    second = source.get_current_parking_availability(["LOT-1", "LOT-2", "LOT-3"], AS_OF)
    assert first == second
    assert len(first) == len(source.get_space_inventory())
    assert {e["timestamp"] for e in first} == {"2026-10-02T10:47:00-04:00"}
    assert all(lot["source_type"] == "simulated_inventory" for lot in source.get_lot_inventory())


def test_real_flow_from_simulated_source_through_component():
    store = ParkingDataStore()
    events = store.request_parking_availability({"lot_ids": ["LOT-1", "LOT-2"], "as_of": AS_OF.isoformat()})
    assert {e["lot_id"] for e in events} == {"LOT-1", "LOT-2"}
    assert len(events) == 44 + 30
    assert set(events[0]) == {"space_id", "lot_id", "zone", "status", "timestamp"}
    assert all(e["status"] in ("occupied", "vacant", "unknown") for e in events)


def test_inventory_must_reconcile_with_capacity_by_zone():
    store = ParkingDataStore()
    lots = source.get_lot_inventory()
    spaces = source.get_space_inventory()[1:]
    with pytest.raises(ValueError):
        store.load_inventory(lots, spaces)


@pytest.mark.parametrize("bad, reason", [
    (event(space_id="L9-O-001"), "unknown_space"),
    (event(zone="visitor"), "lot_or_zone_mismatch"),
    (event(status="free"), "invalid_status"),
    (event(timestamp="2026-10-02T10:47:00"), "invalid_timestamp"),
    (event(timestamp="not a time"), "invalid_timestamp"),
    (event(timestamp="2026-10-02T10:47:21-04:00"), "future_timestamp"),
    ({"space_id": "L1-O-001", "lot_id": "LOT-1", "zone": "permit_O", "status": "vacant"}, "missing_field"),
])
def test_invalid_events_are_rejected_and_recorded(bad, reason):
    store = ParkingDataStore()
    assert store.ingest([bad], received_at=RECEIVED) == 1
    assert store.rejected_events()[0]["reason"] == reason
    assert store.latest_events(["LOT-1"], AS_OF) == []


def test_timestamp_within_five_seconds_ahead_is_accepted():
    store = ParkingDataStore()
    assert store.ingest([event(timestamp="2026-10-02T10:47:20-04:00")], received_at=RECEIVED) == 0


def test_latest_event_at_or_before_decision_time_wins_and_late_events_do_not_replace_it():
    store = ParkingDataStore()
    newer = event(status="occupied", timestamp="2026-10-02T10:47:00-04:00")
    older_late = event(status="vacant", timestamp="2026-10-02T10:46:30-04:00")
    after_decision = event(status="vacant", timestamp="2026-10-02T10:47:30-04:00")
    store.ingest([newer, newer], received_at=RECEIVED)                 # duplicate ignored
    store.ingest([older_late], received_at=RECEIVED)                   # arrives late
    store.ingest([after_decision], received_at=RECEIVED + timedelta(minutes=1))
    assert store.latest_events(["LOT-1"], AS_OF) == [newer]


def test_instants_compare_across_utc_offsets():
    store = ParkingDataStore()
    store.ingest([event(status="occupied", timestamp="2026-10-02T14:47:00+00:00")], received_at=RECEIVED)
    assert store.latest_events(["LOT-1"], AS_OF)[0]["status"] == "occupied"


def test_updated_availability_is_for_the_requested_lot_only():
    store = ParkingDataStore()
    updated = store.request_updated_parking_availability({"lot_id": "LOT-3", "as_of": AS_OF.isoformat()})
    assert updated["lot_id"] == "LOT-3"
    assert {o["lot_id"] for o in updated["observations"]} == {"LOT-3"}
