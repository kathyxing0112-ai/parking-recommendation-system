"""Black-box DO-04 tests; the supplied table is draft simulator policy only.

Expected outputs are literal, requirement-derived sets, not an implementation
of the eligibility algorithm. Synthetic S-* rules isolate decision boundaries.
Run from the project root: pytest -q tests/test_eligibility_filter_independent.py
"""

from copy import deepcopy

import pytest

from cornell_transportation_and_parking_services import get_rule_table
from prepare_eligible_parking_information.determine_eligible_parking_areas import (
    determine_eligible_parking_areas,
)


def trip(**overrides):
    value = dict(
        destination="Cornell",
        arrival_time="2026-11-02T09:00:00-05:00",
        departure_time="2026-11-02T10:00:00-05:00",
        vehicle_category="car",
        declared_eligibility="permit_O",
        access_needs=False,
    )
    value.update(overrides)
    return value


def rule(rule_id, **overrides):
    value = dict(
        rule_id=rule_id, lot_id="LOT-1", eligibility_class="permit_O",
        allowed=True, closure=False,
    )
    value.update(overrides)
    return value


def window(rule_id, start, end, **overrides):
    value = rule(
        rule_id, time_zone="America/New_York", days_of_week=[1],
        valid_from="2026-11-02", valid_until="2026-11-02",
        start_local_time=start, end_local_time=end,
    )
    value.update(overrides)
    return value


def check(policy, requirements, expected, candidates=None, context=None, status=None):
    if candidates is None:
        candidates = ["LOT-1", "LOT-2", "LOT-3"]
    data = [
        dict(lot_id=lot, occupied=2, capacity=10,
             observed_at="2026-11-02T08:59:00-05:00")
        for lot in candidates
    ]
    result = determine_eligible_parking_areas(
        data, deepcopy(requirements),
        deepcopy(context if context is not None else []),
        deepcopy(status if status is not None else {}),
        parking_policy_constraints=deepcopy(policy),
    )
    assert result == [{"lot_id": lot} for lot in expected]


@pytest.fixture
def draft_policy():
    return deepcopy(get_rule_table())


@pytest.mark.parametrize("requirements,expected", [
    # R-01/R-07 allow LOT-1, R-08 allows LOT-2, R-02 allows LOT-3.
    pytest.param(trip(), ["LOT-1", "LOT-2", "LOT-3"], id="matching-permit"),
    # R-07/R-08 allow LOT-1/2 via '*'; no rule allows permit_X at LOT-3.
    pytest.param(trip(declared_eligibility="permit_X"), ["LOT-1", "LOT-2"], id="nonmatching-permit"),
    # R-03 blocks only LOT-1's permit zone; R-07/R-08 allow LOT-1/2; R-04 blocks LOT-3.
    pytest.param(trip(declared_eligibility="visitor"), ["LOT-1", "LOT-2"], id="visitor"),
    # R-01/R-07+R-09, R-08+R-10, and R-02+R-11 satisfy both classes in separate zones.
    pytest.param(trip(access_needs=True), ["LOT-1", "LOT-2", "LOT-3"], id="accessible-separate-zones"),
    # R-07+R-09 and R-08+R-10 allow LOT-1/2; LOT-3 lacks a visitor allowance despite R-11.
    pytest.param(trip(declared_eligibility="visitor", access_needs=True), ["LOT-1", "LOT-2"], id="accessible-is-additional"),
    # R-12 overrides LOT-3's R-02/R-11 allowances; R-07/R-09 and R-08/R-10 allow LOT-1/2.
    pytest.param(trip(arrival_time="2026-11-04T09:00:00-05:00", departure_time="2026-11-04T10:00:00-05:00", access_needs=True), ["LOT-1", "LOT-2"], id="closure-overrides"),
    # LOT-3's R-02 ends at 17:00; R-07/R-08 cover the entire stay at LOT-1/2.
    pytest.param(trip(arrival_time="2026-11-02T16:30:00-05:00", departure_time="2026-11-02T17:30:00-05:00"), ["LOT-1", "LOT-2"], id="window-ends-before-departure"),
    # R-06/R-07 and R-08 allow LOT-1/2 on Sunday; LOT-3 has no visitor rule that allows.
    pytest.param(trip(arrival_time="2026-11-08T09:00:00-05:00", departure_time="2026-11-08T10:00:00-05:00", declared_eligibility="visitor"), ["LOT-1", "LOT-2"], id="weekend"),
    # All R-01..R-12 are outside their valid dates; every candidate is unresolved.
    pytest.param(trip(arrival_time="2027-01-02T09:00:00-05:00", departure_time="2027-01-02T10:00:00-05:00"), [], id="outside-valid-dates"),
    # DO-04 invalid interval overrides all R-01..R-12 allowances.
    pytest.param(trip(departure_time="2026-11-02T09:00:00-05:00"), [], id="zero-duration"),
    # DO-04 reversed interval overrides all R-01..R-12 allowances.
    pytest.param(trip(departure_time="2026-11-02T08:59:00-05:00"), [], id="reversed-interval"),
])
def test_draft_policy_scenarios(draft_policy, requirements, expected):
    # Each parameter's preceding comment identifies its allowing/blocking rules.
    check(draft_policy, requirements, expected)


@pytest.mark.parametrize("bad_access", [None, 0, 1, "true", "false", [], {}])
def test_access_needs_requires_actual_boolean(draft_policy, bad_access):
    # DO-04 rejects non-booleans before any R-01..R-12 allowance can apply.
    check(draft_policy, trip(access_needs=bad_access), [])


@pytest.mark.parametrize("field", list(trip()))
def test_missing_required_trip_field(draft_policy, field):
    # Missing any required trip field invalidates the trip despite R-01/R-02/R-07/R-08.
    requirements = trip()
    del requirements[field]
    check(draft_policy, requirements, [])


@pytest.mark.parametrize("field", ["arrival_time", "departure_time"])
@pytest.mark.parametrize("bad_time", ["not-a-time", "2026-11-02T09:30:00", None])
def test_unreadable_or_naive_trip_time(draft_policy, field, bad_time):
    # Unparseable/offset-naive trip time invalidates all R-01..R-12 allowances.
    check(draft_policy, trip(**{field: bad_time}), [])


@pytest.mark.parametrize("rules,expected", [
    # S-min allows only LOT-1 without optional restrictions; LOT-2/3 have no rule.
    pytest.param([rule("S-min")], ["LOT-1"], id="minimal-rule-and-unresolved-lots"),
    # S-deny blocks S-allow's same class and zone at LOT-1; LOT-2/3 are unresolved.
    pytest.param([rule("S-allow"), rule("S-deny", allowed=False)], [], id="deny-overrides-allow"),
    # S-other-class denies visitors only, so S-allow still allows permit_O at LOT-1.
    pytest.param([rule("S-allow"), rule("S-other-class", eligibility_class="visitor", allowed=False)], ["LOT-1"], id="unrelated-class-denial"),
    # S-east-deny blocks east only; S-west allows LOT-1 through west; LOT-2/3 unresolved.
    pytest.param([rule("S-east", zone="east"), rule("S-east-deny", zone="east", allowed=False), rule("S-west", zone="west")], ["LOT-1"], id="alternative-zone"),
    # S-close closes the whole lot despite its unrelated zone/class and S-allow's allowance.
    pytest.param([rule("S-allow", zone="east"), rule("S-close", zone="west", eligibility_class="visitor", allowed=False, closure=True)], [], id="closure-any-zone-and-class"),
    # S-close-allowed remains a closure even when allowed=true, overriding S-allow.
    pytest.param([rule("S-allow"), rule("S-close-allowed", allowed=True, closure=True)], [], id="closure-flag-prevails"),
    # S-wild covers both required classes at every zone; only LOT-1 has a rule.
    pytest.param([rule("S-wild", zone="*", eligibility_class="*")], ["LOT-1"], id="both-wildcards"),
])
def test_isolated_rule_decisions(rules, expected):
    # The parameter comments derive each exact set; only S-wild also tests access needs.
    needs_access = any(r["rule_id"] == "S-wild" for r in rules)
    check({"rules": rules}, trip(access_needs=needs_access), expected)


@pytest.mark.parametrize("rules,expected", [
    # S-a and S-b join exactly at 09:30 and cover LOT-1's whole interval.
    pytest.param([window("S-a", "09:00", "09:30"), window("S-b", "09:30", "10:00")], ["LOT-1"], id="adjacent-windows"),
    # S-a/S-b leave a one-minute gap at 09:30, making LOT-1 unresolved.
    pytest.param([window("S-a", "09:00", "09:30"), window("S-b", "09:31", "10:00")], [], id="coverage-gap"),
    # S-east/S-west cover complementary times in different zones; neither zone covers the trip.
    pytest.param([window("S-east", "09:00", "09:30", zone="east"), window("S-west", "09:30", "10:00", zone="west")], [], id="no-cross-zone-stitching"),
    # S-short ends before departure and cannot resolve the remaining half-hour.
    pytest.param([window("S-short", "09:00", "09:30")], [], id="short-allowance"),
    # S-full includes arrival and excludes departure, exactly covering LOT-1's trip.
    pytest.param([window("S-full", "09:00", "10:00")], ["LOT-1"], id="exact-coverage"),
    # S-close begins at departure and does not intersect S-full's covered trip.
    pytest.param([window("S-full", "09:00", "10:00"), window("S-close", "10:00", "11:00", closure=True, allowed=False)], ["LOT-1"], id="closure-at-departure"),
    # S-close ends at arrival and does not intersect S-full's covered trip.
    pytest.param([window("S-full", "09:00", "10:00"), window("S-close", "08:00", "09:00", closure=True, allowed=False)], ["LOT-1"], id="closure-ends-at-arrival"),
    # S-close intersects just the last minute, overriding S-full for LOT-1.
    pytest.param([window("S-full", "09:00", "10:00"), window("S-close", "09:59", "11:00", closure=True, allowed=False)], [], id="partial-closure"),
    # S-deny intersects just one minute, overriding S-full for the same zone/class.
    pytest.param([window("S-full", "09:00", "10:00"), window("S-deny", "09:30", "09:31", allowed=False)], [], id="partial-denial"),
    # S-equal has equal endpoints and resolves nothing at LOT-1.
    pytest.param([window("S-equal", "09:00", "09:00")], [], id="equal-window-invalid"),
    # Invalid S-equal resolves nothing but does not cancel valid S-full.
    pytest.param([window("S-full", "09:00", "10:00"), window("S-equal", "09:00", "09:00")], ["LOT-1"], id="invalid-allowance-ignored"),
    # Invalid S-close still closes named candidate LOT-1 despite S-full.
    pytest.param([window("S-full", "09:00", "10:00"), window("S-close", "09:00", "09:00", closure=True)], [], id="invalid-closure-fails-closed"),
])
def test_window_coverage_and_boundaries(rules, expected):
    # The parameter comments derive LOT-1; LOT-2/3 have no applicable rule.
    check({"rules": rules}, trip(), expected)


@pytest.mark.parametrize("missing", ["lot_id", "eligibility_class", "allowed", "closure"])
def test_rule_missing_required_field_resolves_nothing(missing):
    # Incomplete S-bad cannot allow any lot; LOT-2/3 have no rules.
    broken = rule("S-bad")
    del broken[missing]
    check({"rules": [broken]}, trip(), [])


@pytest.mark.parametrize("changes", [
    {"time_zone": "Invalid/Zone"},
    {"valid_from": "not-a-date"},
    {"valid_until": "2026-99-99"},
    {"start_local_time": "25:00", "end_local_time": "26:00"},
])
@pytest.mark.parametrize("is_closure", [False, True])
def test_unreadable_rule_is_ignored_or_fails_closed(changes, is_closure):
    # S-good allows LOT-1 unless unreadable S-bad has closure=true and names LOT-1.
    broken = rule("S-bad", closure=is_closure, **changes)
    check({"rules": [rule("S-good"), broken]}, trip(), [] if is_closure else ["LOT-1"])


def test_incomplete_closure_excludes_named_candidate():
    # S-close lacks eligibility_class but still closes LOT-1 despite S-good.
    broken = rule("S-close", closure=True)
    del broken["eligibility_class"]
    check({"rules": [rule("S-good"), broken]}, trip(), [])


def test_candidates_order_duplicates_staleness_and_context():
    # S-1/S-2 allow LOT-1/2; S-extra cannot add a noncandidate, regardless of context/staleness.
    policy = {"rules": [rule("S-1"), rule("S-2", lot_id="LOT-2"), rule("S-extra", lot_id="EXTRA")]}
    check(policy, trip(), ["LOT-2", "LOT-1"],
          candidates=["LOT-2", "LOT-1", "LOT-2"],
          context=[{"lot_id": "EXTRA", "walking_time_minutes": 1}],
          status={"LOT-1": "stale", "LOT-2": "current"})


def test_no_candidates():
    # S-1 allows LOT-1, but no candidate input means no output.
    check({"rules": [rule("S-1")]}, trip(), [], candidates=[])


def test_other_lot_closure_does_not_block():
    # S-good allows LOT-1; malformed S-other closes only noncandidate EXTRA.
    check({"rules": [rule("S-good"), {"rule_id": "S-other", "lot_id": "EXTRA", "closure": True}]}, trip(), ["LOT-1"])


def test_default_time_zone_and_utc_input():
    # S-local defaults to New York: 14:00Z..15:00Z is Monday 09:00..10:00 EST.
    local = window("S-local", "09:00", "10:00")
    del local["time_zone"]
    check({"rules": [local]}, trip(arrival_time="2026-11-02T14:00:00+00:00", departure_time="2026-11-02T15:00:00+00:00"), ["LOT-1"])


@pytest.mark.parametrize("arrival,departure,expected", [
    # S-night starts Monday within its inclusive dates; Tuesday's tail still belongs to Monday.
    pytest.param("2026-11-03T01:00:00-05:00", "2026-11-03T02:00:00-05:00", ["LOT-1"], id="overnight-start-day"),
    # S-night's Monday window cannot cover Monday morning, whose start day would be Sunday.
    pytest.param("2026-11-02T01:00:00-05:00", "2026-11-02T02:00:00-05:00", [], id="no-wrong-start-day"),
    # S-night's Monday-start window covers the entire cross-midnight stay.
    pytest.param("2026-11-02T23:30:00-05:00", "2026-11-03T01:30:00-05:00", ["LOT-1"], id="cross-midnight"),
])
def test_overnight_start_day_and_inclusive_dates(arrival, departure, expected):
    # S-night is valid only on its Monday start day; LOT-2/3 have no rules.
    check({"rules": [window("S-night", "22:00", "02:00")]}, trip(arrival_time=arrival, departure_time=departure), expected)


@pytest.mark.parametrize("arrival,departure,expected", [
    # S-day covers Monday through 24:00, exactly reaching Tuesday arrival of midnight.
    pytest.param("2026-11-02T23:00:00-05:00", "2026-11-03T00:00:00-05:00", ["LOT-1"], id="24-hour-end"),
    # S-day's valid_until Monday cannot cover any minute of Tuesday.
    pytest.param("2026-11-02T23:00:00-05:00", "2026-11-03T00:01:00-05:00", [], id="after-valid-until"),
    # S-day's valid_from Monday cannot cover the preceding Sunday.
    pytest.param("2026-11-01T23:00:00-05:00", "2026-11-02T00:00:00-05:00", [], id="before-valid-from"),
])
def test_full_day_and_date_boundaries(arrival, departure, expected):
    # S-day covers only Monday 00:00..24:00; LOT-2/3 are unresolved.
    check({"rules": [window("S-day", "00:00", "24:00")]}, trip(arrival_time=arrival, departure_time=departure), expected)


def test_daylight_saving_fall_back_crosses_offset_change():
    # S-DST covers Oct 31 22:00 EDT..Nov 1 03:00 EST, including both repeated 01:30 instants.
    overnight = window("S-DST", "22:00", "03:00", days_of_week=[6], valid_from="2026-10-31", valid_until="2026-10-31")
    check({"rules": [overnight]}, trip(arrival_time="2026-11-01T01:30:00-04:00", departure_time="2026-11-01T01:30:00-05:00"), ["LOT-1"])
