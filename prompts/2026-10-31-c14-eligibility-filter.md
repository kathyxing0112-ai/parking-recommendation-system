# C.1.4 Eligibility Filter Module — Lab 9 Product Build (SENT 2026-11-01, generated once)

Context: SYSEN 5151 Team 26, Lab 9 Product Build (Lab Manual §9.4, p.160–161).
Task sheet item K6. The prompt is sent once and generated once, with no
follow-up corrections. After that, write `docs/deviation-log.md` before
changing any code.

Sources, all read on 2026-11-01:

- The Innoslate export `5151 Team Project- Nov1.xml`, which contains the
  following:
  - The C.1 Parking Information Subsystem Component Specification (X1).
  - DO-04, from the B5 Design Output Requirements.
  - The A1.4 ICOM relationships, NFR.4, and SR-10.
- `SPEC.md` Data Contract §4 and §5.
- `contracts/api-v1.yaml`.
- The draft rule table
  `cornell_transportation_and_parking_services/parking_rules_draft.json`,
  version `draft-2026-11-01b`.

Numbering note: "1.4.4" below is the C.1 component specification's own
number. It is not the system-level FR 1.4.4 in `tests/test_functional_requirements.py`
(A4 Present Parking Recommendations and Status).

## Component Prompt Template

- **Context.**
  - The Cornell Smart Parking Availability & Recommendation System
    recommends eligible parking areas for a Cornell driver's confirmed trip.
  - It uses three pilot lots and simulated occupancy data:
    - LOT-1 Hoy Road Garage
    - LOT-2 Peterson Lot
    - LOT-3 Campus Road O Area
  - It only supports decisions. It does not reserve spaces.
  - This component is the last step of C.1 Parking Information Subsystem.
    It decides which pilot areas the trip may use, before forecasting (C.2),
    ranking (C.3) and presentation (C.4).
  - C.2, C.3 and C.4 only see the areas this module returns, so an area
    that breaks a rule cannot be removed later.

- **Component.** C.1.4 Eligibility Filter Module.

- **Function performed.** A1.4 Determine Eligible Parking Areas.

- **Requirements.** Verbatim, with identifiers:
  - **1.4.4 Determine Eligible Parking Areas** (C.1 Component
    Specification): "The Parking Information Subsystem shall determine
    eligible parking areas using validated parking availability data,
    normalized trip requirements, and approved parking policy constraints."
  - **1.1.7 Accept Parking Policy Constraints**: "The Parking Information
    Subsystem shall accept Parking Policy Constraints from the Cornell
    Transportation and Parking Services."
  - **1.2.8 Provide Eligible Parking Areas (Driver Presentation
    Subsystem)**: "The Parking Information Subsystem shall provide Eligible
    Parking Areas to the Driver Presentation Subsystem."
  - **2.1.2 C.1 Parking Eligibility and Policy Compliance**: "The Parking
    Information Subsystem shall exclude all parking areas that violate
    confirmed permission, closure, or time restrictions from the eligible
    parking area output for every approved pilot scenario."
  - **DO-04 Eligible Parking Area Output**: "The Eligibility Filter Module
    shall include a parking area in Eligible Parking Areas only when a
    confirmed rule allows the trip's declared eligibility, and accessible
    parking when access needs is true, and no confirmed closure applies at
    any time between the trip's arrival time and departure time; an area
    whose eligibility no confirmed rule resolves shall be left out."
    - MOP: "Returned areas that violate a confirmed permit, accessibility,
      closure or time rule: 0 areas. Scenarios whose output equals the
      expected eligible set: 100% of scenarios."
    - Verification (Test): "Pass when, in scenarios covering a matching
      permit, a non-matching permit, visitor eligibility, a requested
      accessible space, a closure that overrides an allowance, a rule
      window that ends before the departure time and an area with no
      applicable rule, the output equals the expected eligible set in
      every scenario."
  - **NFR.4 Parking Rule Compliance**: "The system shall return zero
    parking options that violate confirmed permission, closure or time
    restrictions in the approved pilot scenario set."
  - **SR-10** (SPEC.md, SN-08): "Before ranking, exclude options that
    violate confirmed permit, accessibility, closure, or time rules for the
    trip. Every returned option passes the 100% rule-consistency check
    specified under SN-06; an option whose eligibility is not resolved by a
    confirmed rule is not asserted as eligible."

- **Interfaces.** From the A1.4 relationships in the Innoslate model, with
  types from `contracts/api-v1.yaml`. Write one function with this signature:

  ```python
  def determine_eligible_parking_areas(
      validated_parking_data: list[dict],
      normalized_trip_requirements: dict,
      validated_context_information: list[dict],
      data_quality_and_freshness_status: dict,
      *,
      parking_policy_constraints: dict,
  ) -> list[dict]:
  ```

  - **Input `validated_parking_data`** (`ValidatedParkingData`, I-02): a
    list of `{lot_id, occupied, capacity, observed_at}`. The candidate
    areas are the distinct `lot_id` values in this list, in first-seen
    order.
  - **Input `normalized_trip_requirements`** (`TripRequest`, SPEC §5): the
    six confirmed fields, `destination`, `arrival_time`, `departure_time`,
    `vehicle_category`, `declared_eligibility` and `access_needs`. The two
    times are offset-aware ISO 8601 strings, and `departure_time` is later
    than `arrival_time`.
  - **Input `validated_context_information`** (I-03, `{lot_id,
    walking_time_minutes}`): received, but not used in the decision.
  - **Input `data_quality_and_freshness_status`** (`{lot_id: "current" |
    "stale"}`): received, but not used in the decision. A stale area is not
    excluded here; freshness belongs to A1.3 and A4.
  - **Control `parking_policy_constraints`** (`ParkingPolicyConstraints`,
    E-12): `{"rules": [...]}`.
    - Required fields in each rule: `lot_id`, `eligibility_class`,
      `allowed` and `closure`.
    - Optional SPEC §4 fields: `zone`, `valid_from`, `valid_until`,
      `time_zone`, `days_of_week` (ISO, 1 = Monday), `start_local_time`
      and `end_local_time`. Ignore any other fields.
    - A field that is absent means "no restriction". With no `zone`, the
      rule covers the whole lot. With no date fields, it covers every date.
      With no `days_of_week`, it covers every day. With no
      `start_local_time` and `end_local_time`, it covers the whole day.
    - `"*"` in `zone` or `eligibility_class` matches every value.
    - Times are local wall-clock `HH:MM` in `time_zone` (default
      `America/New_York`). `end_local_time` `"24:00"` means the end of the
      day. An end earlier than the start means the window runs past
      midnight into the next day, and that next-day part still belongs to
      the window's start day for `days_of_week`.
    - `valid_from` and `valid_until` are inclusive dates. Apply them to the
      window's start day.
    - Use the actual UTC offset of each date, including daylight-saving
      changes (`zoneinfo`).
  - **Output** (`EligibleParkingAreas`, I-05): a list of `{"lot_id": ...}`.
    Use the candidate order, with no duplicates and no other fields.
  - **Mechanism.** C.1.4 Eligibility Filter Module.
  - **Decision rule.** Implement DO-04 exactly as follows. The trip interval
    is `[arrival_time, departure_time)`.
    1. The trip's required classes are `declared_eligibility`, plus
       `"accessible"` when `access_needs` is true.
    2. A rule applies to class C when its `eligibility_class` is C or `"*"`.
    3. A class C is satisfied at a lot when, for at least one zone of that
       lot, two things hold. A zone counts here if a rule for the lot names
       it, and a rule with no zone or `"*"` counts for every zone:
       - Every instant of the trip interval is covered by a rule with
         `allowed` true and `closure` false that applies to C in that zone.
       - No instant is covered by a rule with `allowed` false that applies
         to C in that zone.
       Coverage may come from several consecutive rules.
    4. A lot is excluded if any rule for that lot with `closure` true covers
       any instant of the trip interval, whatever its zone or class.
    5. A lot is included only if every required class is satisfied there and
       rule 4 does not exclude it.
    6. Rules for other lots, and rules for lots that are not candidates, are
       ignored.
  - **Error conditions.**
    - If `normalized_trip_requirements` is missing any of the six fields,
      or its times cannot be parsed as offset-aware ISO 8601, return `[]`.
      An incomplete request is not treated as complete.
    - A rule that lacks a required field, or has a value that cannot be
      parsed, resolves nothing. It is skipped, so it can never make an area
      eligible. If such a rule has `closure` true and names a candidate lot,
      that lot is excluded, because an unreadable closure must not be read
      as "open".
    - Raise no exceptions for these cases.

- **Constraints.**
  - Python 3.13, standard library only (`datetime`, `zoneinfo`).
  - Put the function in one new module:
    `prepare_eligible_parking_information/determine_eligible_parking_areas.py`.
  - Do not modify `contracts/`, the A1–A6 module files, `parking_data_access/`,
    `language_model/`, or the rule table.
  - Local execution only, with no network or file access. The function is
    pure: it reads only its arguments.
  - No performance limit is allocated. C.1 2.3.1 says the budget is "its
    allocated response-time budget", which has no number yet. Keep the
    function simple rather than optimized.

- **Success criteria.** Requirement-derived tests in
  `tests/test_eligibility_filter.py`.
  - All scenarios below must give exactly the expected eligible set
    (DO-04 MOP: 100% of scenarios, 0 violating areas).
  - Scenarios 1–8 use the draft rule table, loaded with
    `cornell_transportation_and_parking_services.get_rule_table()`. The
    candidates are LOT-1, LOT-2 and LOT-3.
  - Times are written in America/New_York, using offset `-05:00`, which
    applies after 2026-11-01. Each row's DO-04 case is in brackets.

  | # | DO-04 case | declared_eligibility | access_needs | Arrival → departure | Expected |
  |---|---|---|---|---|---|
  | 1 | Matching permit | permit_O | false | Mon 2026-11-02 10:00 → 12:00 | LOT-1, LOT-3 |
  | 2 | Non-matching permit; area with no applicable rule (LOT-2 has no permit_O rule) | permit_O | false | same | LOT-1, LOT-3 (LOT-2 left out) |
  | 3 | Visitor eligibility (LOT-3 disallows visitors in its permit zone and has no visitor zone) | visitor | false | same | LOT-1, LOT-2 |
  | 4 | Requested accessible space | permit_O | true | same | LOT-1, LOT-3 |
  | 5 | Requested accessible space, visitor | visitor | true | same | LOT-1, LOT-2 |
  | 6 | Closure overrides an allowance (R-12 closes LOT-3 on Wed 08:00–18:00) | permit_O | false | Wed 2026-11-04 10:00 → 12:00 | LOT-1 |
  | 7 | Rule window ends before departure (LOT-3's permit_O rule ends 17:00) | permit_O | false | Mon 2026-11-02 16:00 → 18:00 | LOT-1 (R-01 then R-05) |
  | 8 | Overnight window, chained rules | permit_O | false | Mon 2026-11-02 18:00 → Tue 2026-11-03 09:00 | LOT-1 |

  - Scenario 9 must also pass, with rules written in the contract's minimal
    shape and no zone or time fields. It mirrors
    `test_FR_1_4_1_prepares_eligible_parking_information`.
    - Rules:
      - LOT-1: permit_O, allowed, no closure.
      - LOT-2: permit_O, allowed, closure.
      - LOT-3: permit_O, allowed, no closure.
      - LOT-4: permit_O, not allowed.
    - Candidates: LOT-1 to LOT-4, with LOT-3 marked `stale`.
    - Trip: permit_O, no access need, 2026-10-02 11:20 → 13:00, offset
      `-04:00`.
    - Expected: LOT-1, LOT-3.
  - Scenario 10: a trip missing `access_needs` must return `[]`.

- **Output format.** Two Python files:
  - `prepare_eligible_parking_information/determine_eligible_parking_areas.py`
  - `tests/test_eligibility_filter.py`

  No prose outside code comments and docstrings.

- **Out of scope.**
  - Do not judge freshness (A1.3), forecast (A2), rank (A3) or present
    (A4). Do not use occupancy or walking times in the decision.
  - Do not wire the function into `prepare_eligible_parking_information()`
    or `smart_parking_service`. Integration is a separate step.
  - Do not add logging, caching, retries, configuration, CLI entry points
    or classes that no requirement asks for.
  - Do not refactor other modules, and do not add dependencies.
  - Do not validate the rule table's policy content.

## Decisions taken while filling this prompt (confirmed by Katherine Xing, 2026-11-01)

1. **Combining DO-04's two conditions.** When `access_needs` is true, the
   declared eligibility and the accessible class may be satisfied by
   different zones of the same lot. For example, an O-permit holder with a
   placard is eligible at LOT-1, because the permit zone allows permit_O
   and the accessible zone allows accessible. DO-04 does not say whether
   both must hold in the same zone.
2. **Stale areas stay eligible.** The A1.4 relationships include Data
   Quality and Freshness Status, but DO-04 does not mention freshness, and
   FR 1.4.1 expects a stale LOT-3 to remain eligible.
3. **Candidate areas come from Validated Parking Data.** A lot with no
   validated data is not considered.
4. **Contract shape.** `contracts/api-v1.yaml` E-12 requires only four rule
   fields. The optional §4 fields are read when present, so both the
   contract's minimal shape and the full §4 shape work.
