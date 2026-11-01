# C.1.4 independent test prompt (for deviation-log row 7)

Purpose: Lab Manual p.21, "Never let one generation write both the code and
its test". The K6 component and its first tests came from one generation
(commit `d90bf3f`). This prompt lets a team member who did not run that
generation produce requirement-based tests in a **new, separate AI session**.

How to use it:

1. Open a new conversation. Do not use the session that generated C.1.4.
2. Paste everything below the line `---- PASTE FROM HERE ----` into it.
3. Do **not** paste the C.1.4 code
   (`prepare_eligible_parking_information/determine_eligible_parking_areas.py`),
   the existing tests (`tests/test_eligibility_filter.py`), or the "Success
   criteria" table from `prompts/2026-10-31-c14-eligibility-filter.md`.
4. Save the reply as `tests/test_eligibility_filter_independent.py`.
5. Run `python -m pytest tests/test_eligibility_filter_independent.py -v`.
6. Check each test's comment against the rule table. Record in
   `docs/deviation-log.md`, row 7, who ran it, the date, the AI used, the
   number passed and failed, and for each failure whether the code or the
   test is wrong.

The requirements below are the current ones, including the DO-04 and
Parking Policy Constraints text that was added in Innoslate on 2026-11-01.

---- PASTE FROM HERE ----

You are writing requirement-based tests for a Python function you have NOT seen.
Use only the requirements, interface description, decisions and rule table below.

## Requirements (verbatim, with identifiers)

- **1.4.4 Determine Eligible Parking Areas** (C.1 Component Specification): "The Parking Information Subsystem shall determine eligible parking areas using validated parking availability data, normalized trip requirements, and approved parking policy constraints."
- **1.1.7 Accept Parking Policy Constraints**: "The Parking Information Subsystem shall accept Parking Policy Constraints from the Cornell Transportation and Parking Services."
- **1.2.8 Provide Eligible Parking Areas (Driver Presentation Subsystem)**: "The Parking Information Subsystem shall provide Eligible Parking Areas to the Driver Presentation Subsystem."
- **2.1.2 C.1 Parking Eligibility and Policy Compliance**: "The Parking Information Subsystem shall exclude all parking areas that violate confirmed permission, closure, or time restrictions from the eligible parking area output for every approved pilot scenario."
- **DO-04 Eligible Parking Area Output**: "The Eligibility Filter Module shall include a parking area in Eligible Parking Areas only when a confirmed rule allows the trip's declared eligibility, and accessible parking when access needs is true, and no confirmed closure applies at any time between the trip's arrival time and departure time; an area whose eligibility no confirmed rule resolves shall be left out. If the trip's departure time is not later than its arrival time, or access needs is not true or false, the Eligibility Filter Module shall return no parking areas."
  - MOP: "Returned areas that violate a confirmed permit, accessibility, closure or time rule: 0 areas. Scenarios whose output equals the expected eligible set: 100% of scenarios."
  - Verification (Test): "Pass when, in scenarios covering a matching permit, a non-matching permit, visitor eligibility, a requested accessible space, a closure that overrides an allowance, a rule window that ends before the departure time, an area with no applicable rule and an invalid trip interval, the output equals the expected eligible set in every scenario."
- **Parking Policy Constraints** (Innoslate Input/Output, description): "Each rule window recurs on its listed weekdays between its valid-from and valid-until dates. A window whose start time is later than its end time runs past midnight into the next day; a window whose start time equals its end time is invalid and resolves no eligibility."
- **NFR.4 Parking Rule Compliance**: "The system shall return zero parking options that violate confirmed permission, closure or time restrictions in the approved pilot scenario set."
- **SR-10** (SPEC.md, SN-08): "Before ranking, exclude options that violate confirmed permit, accessibility, closure, or time rules for the trip. Every returned option passes the 100% rule-consistency check specified under SN-06; an option whose eligibility is not resolved by a confirmed rule is not asserted as eligible."

## Interface of the function under test (do not implement it)

```python
# module: prepare_eligible_parking_information.determine_eligible_parking_areas
def determine_eligible_parking_areas(
    validated_parking_data: list[dict],
    normalized_trip_requirements: dict,
    validated_context_information: list[dict],
    data_quality_and_freshness_status: dict,
    *,
    parking_policy_constraints: dict,
) -> list[dict]:
```

- **Input `validated_parking_data`**: a list of `{lot_id, occupied, capacity, observed_at}`. The candidate areas are the distinct `lot_id` values in this list, in first-seen order.
- **Input `normalized_trip_requirements`**: the six fields `destination`, `arrival_time`, `departure_time`, `vehicle_category`, `declared_eligibility` and `access_needs`. The times are offset-aware ISO 8601 strings.
- **Input `validated_context_information`** (`{lot_id, walking_time_minutes}`): received, but not used in the decision.
- **Input `data_quality_and_freshness_status`** (`{lot_id: "current" | "stale"}`): received, but not used in the decision. A stale area is not excluded.
- **Control `parking_policy_constraints`**: `{"rules": [...]}`.
  - Required fields in each rule: `lot_id`, `eligibility_class`, `allowed` and `closure`.
  - Optional fields: `zone`, `valid_from`, `valid_until`, `time_zone`, `days_of_week` (ISO, 1 = Monday), `start_local_time` and `end_local_time`. Other fields are ignored.
  - An absent field means "no restriction". With no `zone`, the rule covers the whole lot. With no dates, it covers every date. With no `days_of_week`, it covers every day. With no start and end times, it covers the whole day.
  - `"*"` in `zone` or `eligibility_class` matches every value.
  - Times are local wall-clock `HH:MM` in `time_zone` (default `America/New_York`). `"24:00"` means the end of the day.
  - A start later than the end runs past midnight into the next day, and the next-day part still belongs to the window's start day for `days_of_week`. A start equal to the end is invalid.
  - `valid_from` and `valid_until` are inclusive dates, applied to the window's start day.
  - The actual UTC offset of each date is used, including daylight-saving changes.
- **Output**: a list of `{"lot_id": ...}` in candidate order, with no duplicates and no other fields.
- **Decision rule.** The trip interval is `[arrival_time, departure_time)`.
  1. The trip's required classes are `declared_eligibility`, plus `"accessible"` when `access_needs` is true.
  2. A rule applies to class C when its `eligibility_class` is C or `"*"`.
  3. A class C is satisfied at a lot when, for at least one zone of that lot, two things hold. A zone counts if a rule for the lot names it; a rule with no zone or `"*"` counts for every zone.
     - Every instant of the trip interval is covered by rules with `allowed` true and `closure` false that apply to C in that zone. Coverage may come from several consecutive rules.
     - No instant is covered by a rule with `allowed` false that applies to C in that zone.
  4. A lot is excluded if any rule for that lot with `closure` true covers any instant of the trip interval, whatever its zone or class.
  5. A lot is included only if every required class is satisfied there and step 4 does not exclude it.
  6. Rules for other lots, and rules for lots that are not candidates, are ignored.
- **Error conditions** (the function returns `[]` and raises nothing):
  - `normalized_trip_requirements` is missing any of the six fields.
  - A time cannot be parsed as offset-aware ISO 8601.
  - `departure_time` is not later than `arrival_time`.
  - `access_needs` is not `true` or `false`.
- **Unreadable rules.** A rule that lacks a required field, or has a value that cannot be parsed (including a start time equal to its end time), resolves nothing and can never make an area eligible. If such a rule has `closure` true and names a candidate lot, that lot is excluded.

## Decisions confirmed by the team (2026-11-01)

1. When `access_needs` is true, the declared eligibility and the accessible class may be satisfied by different zones of the same lot.
2. Stale areas stay eligible; freshness is handled elsewhere.
3. Candidate areas come only from `validated_parking_data`.
4. Rules may use only the four required fields, or the full set of optional fields.

## Rule table (draft, simulated; not Cornell policy)

Load it in the tests with `from cornell_transportation_and_parking_services import get_rule_table`. Its content is:

```json
{
  "table": "SPEC Data Contract section 4 parking-rule table",
  "status": "DRAFT, NOT CONFIRMED. Not Cornell policy. Built from public Cornell pages plus labeled simulator assumptions; the team must review and confirm before evaluation (SR-10).",
  "version": "draft-2026-11-01c",
  "conventions": {
    "days_of_week": "ISO weekday numbers, 1 = Monday ... 7 = Sunday",
    "times": "Local wall-clock HH:MM in time_zone. The rule recurs on every date from valid_from to valid_until whose weekday is in days_of_week. end_local_time 24:00 means the end of the day. An end time earlier than the start time means the window runs past midnight into the next date, and belongs to the date it starts on. A start equal to the end is invalid",
    "wildcard": "* in zone or eligibility_class means every value. lot_id is always a single pilot lot, and a rule names a zone only where that lot has spaces in it",
    "eligibility_class": "permit_O and visitor are the declared_eligibility values; accessible means the trip has access_needs true. A valid accessible-parking placard is still required and is not checked by the system. No rule disallows placard holders, because an accessible space is only reached through the accessible class",
    "closure": "A rule with closure true overrides any allowance in the same window",
    "unresolved": "A trip interval not fully covered by an allowing rule is unresolved and must not be shown as eligible (SPEC section 4)"
  },
  "rules": [
    {
      "rule_id": "R-01",
      "version": 1,
      "lot_id": "LOT-1",
      "zone": "permit_O",
      "eligibility_class": "permit_O",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5
      ],
      "start_local_time": "07:30",
      "end_local_time": "17:00",
      "allowed": true,
      "closure": false,
      "source": "Simulator assumption: an O-permit zone accepts O permits during enforcement hours. Enforcement hours from https://fcs.cornell.edu/node/2296 (undated)",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-02",
      "version": 1,
      "lot_id": "LOT-3",
      "zone": "permit_O",
      "eligibility_class": "permit_O",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5
      ],
      "start_local_time": "07:30",
      "end_local_time": "17:00",
      "allowed": true,
      "closure": false,
      "source": "Simulator assumption: an O-permit zone accepts O permits during enforcement hours. Enforcement hours from https://fcs.cornell.edu/node/2296 (undated)",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-03",
      "version": 1,
      "lot_id": "LOT-1",
      "zone": "permit_O",
      "eligibility_class": "visitor",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5
      ],
      "start_local_time": "07:30",
      "end_local_time": "17:00",
      "allowed": false,
      "closure": false,
      "source": "https://fcs.cornell.edu/node/2296 (undated): permit areas are enforced on weekdays outside the 5 P.M.-7:30 A.M. open-parking period",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-04",
      "version": 1,
      "lot_id": "LOT-3",
      "zone": "permit_O",
      "eligibility_class": "visitor",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5
      ],
      "start_local_time": "07:30",
      "end_local_time": "17:00",
      "allowed": false,
      "closure": false,
      "source": "https://fcs.cornell.edu/node/2296 (undated): permit areas are enforced on weekdays outside the 5 P.M.-7:30 A.M. open-parking period",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-05",
      "version": 1,
      "lot_id": "LOT-1",
      "zone": "permit_O",
      "eligibility_class": "*",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5
      ],
      "start_local_time": "17:00",
      "end_local_time": "07:30",
      "allowed": true,
      "closure": false,
      "source": "https://fcs.cornell.edu/node/2296 (undated): Hoy Road Parking Garage (LOT-1) is open parking weekdays 5 P.M.-7:30 A.M.",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-06",
      "version": 1,
      "lot_id": "LOT-1",
      "zone": "permit_O",
      "eligibility_class": "*",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        6,
        7
      ],
      "start_local_time": "00:00",
      "end_local_time": "24:00",
      "allowed": true,
      "closure": false,
      "source": "https://fcs.cornell.edu/node/2296 (undated): Hoy Road Parking Garage (LOT-1) is open parking all day on weekends",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-07",
      "version": 1,
      "lot_id": "LOT-1",
      "zone": "visitor",
      "eligibility_class": "*",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5,
        6,
        7
      ],
      "start_local_time": "00:00",
      "end_local_time": "24:00",
      "allowed": true,
      "closure": false,
      "source": "Simulator assumption: visitor zones are paid hourly parking open to anyone who pays, including permit holders (team decision 2026-11-01). Hourly pay lots are listed in https://fcs.cornell.edu/sites/default/files/2026-08/ParkmobileMap26.pdf (August 2026); rates are not modeled",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-08",
      "version": 1,
      "lot_id": "LOT-2",
      "zone": "visitor",
      "eligibility_class": "*",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5,
        6,
        7
      ],
      "start_local_time": "00:00",
      "end_local_time": "24:00",
      "allowed": true,
      "closure": false,
      "source": "https://fcs.cornell.edu/sites/default/files/2026-08/ParkmobileMap26.pdf (August 2026): Peterson Lot (LOT-2) is an hourly pay lot. Treating it as paid parking open to anyone, including permit holders, at all hours is a simulator assumption (team decision 2026-11-01); rates are not modeled",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-09",
      "version": 1,
      "lot_id": "LOT-1",
      "zone": "accessible",
      "eligibility_class": "accessible",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5,
        6,
        7
      ],
      "start_local_time": "00:00",
      "end_local_time": "24:00",
      "allowed": true,
      "closure": false,
      "source": "Simulator assumption: accessible spaces accept trips with access_needs true. A valid placard is required and is not checked. Accessible spaces are restricted to placard holders at all times per https://fcs.cornell.edu/node/2296 (undated)",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-10",
      "version": 1,
      "lot_id": "LOT-2",
      "zone": "accessible",
      "eligibility_class": "accessible",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5,
        6,
        7
      ],
      "start_local_time": "00:00",
      "end_local_time": "24:00",
      "allowed": true,
      "closure": false,
      "source": "Simulator assumption: accessible spaces accept trips with access_needs true. A valid placard is required and is not checked. Accessible spaces are restricted to placard holders at all times per https://fcs.cornell.edu/node/2296 (undated)",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-11",
      "version": 1,
      "lot_id": "LOT-3",
      "zone": "accessible",
      "eligibility_class": "accessible",
      "valid_from": "2026-11-01",
      "valid_until": "2026-12-31",
      "time_zone": "America/New_York",
      "days_of_week": [
        1,
        2,
        3,
        4,
        5,
        6,
        7
      ],
      "start_local_time": "00:00",
      "end_local_time": "24:00",
      "allowed": true,
      "closure": false,
      "source": "Simulator assumption: accessible spaces accept trips with access_needs true. A valid placard is required and is not checked. Accessible spaces are restricted to placard holders at all times per https://fcs.cornell.edu/node/2296 (undated)",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    },
    {
      "rule_id": "R-12",
      "version": 1,
      "lot_id": "LOT-3",
      "zone": "*",
      "eligibility_class": "*",
      "valid_from": "2026-11-04",
      "valid_until": "2026-11-04",
      "time_zone": "America/New_York",
      "days_of_week": [
        3
      ],
      "start_local_time": "08:00",
      "end_local_time": "18:00",
      "allowed": false,
      "closure": true,
      "source": "Simulator assumption: a simulated event-day closure (Wednesday 2026-11-04), so the closure case can be tested. Not a real Cornell closure",
      "owner": "Katherine Xing (draft)",
      "reviewed_at": "2026-11-01T00:00:00-04:00"
    }
  ]
}
```

## What to write

Write one pytest file, `tests/test_eligibility_filter_independent.py`, that tests
`prepare_eligible_parking_information.determine_eligible_parking_areas.determine_eligible_parking_areas`.

Cover each DO-04 verification case at least once, choosing your own dates and times:

- a matching permit;
- a non-matching permit;
- visitor eligibility;
- a requested accessible space;
- a closure that overrides an allowance;
- a rule window that ends before the departure time;
- an area with no applicable rule;
- an invalid trip interval.

Also cover a rule whose start time equals its end time, and an `access_needs` that is not a boolean. Times are America/New_York; after 2026-11-01 the offset is -05:00.

For every test, write a one-line comment that shows how you derived the expected eligible set from the rules (which rule IDs allow or block each lot).

Output only the Python file.
