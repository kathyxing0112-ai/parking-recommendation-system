"""C.1.4 Eligibility Filter Module: DO-04 verification scenarios.

Generated once from prompts/2026-10-31-c14-eligibility-filter.md (commit
d90bf3f), then corrected per docs/deviation-log.md. DO-04 MOP:
the output equals the expected eligible set in 100% of scenarios, with zero
returned areas that violate a confirmed rule. Scenarios 1-8 use the team-
confirmed rule table (not Cornell policy).
"""

import pytest

from cornell_transportation_and_parking_services import get_rule_table
from prepare_eligible_parking_information.determine_eligible_parking_areas import (
    determine_eligible_parking_areas,
)

CANDIDATES = [
    {"lot_id": lot_id, "occupied": 10, "capacity": 100, "observed_at": "2026-11-02T09:59:30-05:00"}
    for lot_id in ("LOT-1", "LOT-2", "LOT-3")
]


def trip(declared_eligibility, access_needs, arrival, departure):
    return {
        "destination": "Upson Hall",
        "arrival_time": arrival,
        "departure_time": departure,
        "vehicle_category": "sedan",
        "declared_eligibility": declared_eligibility,
        "access_needs": access_needs,
    }


def eligible_lots(trip_request, candidates=CANDIDATES, rules=None, freshness=None):
    areas = determine_eligible_parking_areas(
        candidates, trip_request, [], freshness or {},
        parking_policy_constraints=rules if rules is not None else get_rule_table())
    return [area["lot_id"] for area in areas]


MON_10 = "2026-11-02T10:00:00-05:00"
MON_12 = "2026-11-02T12:00:00-05:00"


@pytest.mark.parametrize("case, trip_request, expected", [
    # Visitor zones are paid parking open to anyone, permit holders included
    # (confirmed by the team on 2026-11-03), so an O-permit trip may use LOT-2.
    ("1 matching permit",
     trip("permit_O", False, MON_10, MON_12), ["LOT-1", "LOT-2", "LOT-3"]),
    ("3 visitor eligibility",
     trip("visitor", False, MON_10, MON_12), ["LOT-1", "LOT-2"]),
    ("4 requested accessible space",
     trip("permit_O", True, MON_10, MON_12), ["LOT-1", "LOT-2", "LOT-3"]),
    ("5 requested accessible space, visitor",
     trip("visitor", True, MON_10, MON_12), ["LOT-1", "LOT-2"]),
    ("6 closure overrides an allowance",
     trip("permit_O", False, "2026-11-04T10:00:00-05:00", "2026-11-04T12:00:00-05:00"), ["LOT-1", "LOT-2"]),
    ("7 rule window ends before departure",
     trip("permit_O", False, "2026-11-02T16:00:00-05:00", "2026-11-02T18:00:00-05:00"), ["LOT-1", "LOT-2"]),
    ("8 overnight window, chained rules",
     trip("permit_O", False, "2026-11-02T18:00:00-05:00", "2026-11-03T09:00:00-05:00"), ["LOT-1", "LOT-2"]),
])
def test_draft_rule_table_scenarios(case, trip_request, expected):
    assert eligible_lots(trip_request) == expected


def test_2_non_matching_permit_is_left_out():
    """A trip without an O permit may not use an O-permit-only area (deviation log row 1)."""
    only_lot_3 = [area for area in CANDIDATES if area["lot_id"] == "LOT-3"]
    assert eligible_lots(trip("visitor", False, MON_10, MON_12), only_lot_3) == []


def test_area_with_no_applicable_rule_is_left_out():
    unknown_lot = [{"lot_id": "LOT-9", "occupied": 1, "capacity": 10, "observed_at": MON_10}]
    assert eligible_lots(trip("permit_O", False, MON_10, MON_12), CANDIDATES + unknown_lot) == \
        ["LOT-1", "LOT-2", "LOT-3"]


@pytest.mark.parametrize("departure", [MON_10, "2026-11-02T09:00:00-05:00"])
def test_departure_not_after_arrival_returns_nothing(departure):
    """Deviation log row 2."""
    assert eligible_lots(trip("permit_O", False, MON_10, departure)) == []


def test_non_boolean_access_needs_returns_nothing():
    """Deviation log row 3."""
    assert eligible_lots(trip("visitor", "yes", MON_10, MON_12)) == []


def test_rule_window_with_equal_start_and_end_resolves_nothing():
    """Deviation log row 5: start equal to end is an invalid rule, not a full day."""
    rules = {"rules": [{"lot_id": "LOT-1", "eligibility_class": "permit_O", "allowed": True,
                        "closure": False, "start_local_time": "09:00", "end_local_time": "09:00"}]}
    assert eligible_lots(trip("permit_O", False, MON_10, MON_12), CANDIDATES, rules) == []


def test_9_minimal_contract_rules_mirror_fr_1_4_1():
    rules = {"rules": [
        {"lot_id": "LOT-1", "eligibility_class": "permit_O", "allowed": True, "closure": False},
        {"lot_id": "LOT-2", "eligibility_class": "permit_O", "allowed": True, "closure": True},
        {"lot_id": "LOT-3", "eligibility_class": "permit_O", "allowed": True, "closure": False},
        {"lot_id": "LOT-4", "eligibility_class": "permit_O", "allowed": False, "closure": False},
    ]}
    candidates = [{"lot_id": f"LOT-{n}", "occupied": 1, "capacity": 10,
                   "observed_at": "2026-10-02T10:29:30-04:00"} for n in range(1, 5)]
    trip_request = trip("permit_O", False, "2026-10-02T11:20:00-04:00", "2026-10-02T13:00:00-04:00")
    assert eligible_lots(trip_request, candidates, rules, {"LOT-3": "stale"}) == ["LOT-1", "LOT-3"]


def test_10_incomplete_trip_returns_nothing():
    trip_request = trip("permit_O", False, MON_10, MON_12)
    del trip_request["access_needs"]
    assert eligible_lots(trip_request) == []
