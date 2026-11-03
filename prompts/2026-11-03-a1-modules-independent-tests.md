# A1.1 to A1.3 independent test prompt

Purpose: Lab Manual p.21, "Never let one generation write both the code and its
test". The A1.1, A1.2 and A1.3 modules were written by Claude Code. This prompt produces its
requirement-based tests in a **new, separate AI session**.

How to use it:

1. Open a new conversation in a tool with no access to this repository.
2. Paste everything below the line that says PASTE BELOW THIS LINE.
3. Do **not** paste any module from `prepare_eligible_parking_information/`, or any existing test.
4. Save the reply as `tests/test_a1_modules_independent.py`.
5. Run `python -m pytest tests/test_a1_modules_independent.py -v`.

---- PASTE BELOW THIS LINE ----

You are writing requirement-based tests for three Python functions you have NOT seen.
Use only the requirements and interfaces below.

## Requirements for A1.3 (verbatim)

- **C.1 Spec 1.4.3 Validate Parking and Context Information**: "The Parking Information Subsystem shall validate parking availability and contextual information against approved data validation and freshness rules."
- **DO-03 Observation Validation Status**: "The Data Validation Module shall mark a parking area as current in Data Quality and Freshness Status only when its latest valid observation is no more than 120 seconds old at decision time, and as stale otherwise, and shall leave out of Validated Parking Data any observation with a missing or invalid timestamp, a timestamp more than 5 seconds ahead of the application clock, or an occupied count outside 0 to capacity."
  - MOP: "Freshness boundary cases labeled correctly: 100% of cases. Invalid observations passed into Validated Parking Data: 0 observations."
  - Verification (Test): "Pass when observations aged 119 s and 120 s are marked current, one aged 121 s is marked stale, an observation without a timestamp is marked stale and left out, and an observation timestamped 6 s in the future or with occupied equal to capacity plus 1 is left out."
- **SPEC Data Contract §1**: `status` is `occupied`, `vacant` or `unknown`. "`unknown` is not counted as an available space." For each space, the latest valid event determines its observed state. Late arrivals must not replace a newer observation. Stale observations are not silently converted to vacant spaces.
- **Validated Context Information**: "Missing or invalid context must not be presented as confirmed information." Each record carries `lot_id` and `walking_time_minutes` (a number that is at least 0).

## Interface of A1.3 (do not implement it)

```python
# module: prepare_eligible_parking_information.validate_parking_and_context_information
def validate_parking_and_context_information(
    normalized_trip_requirements: dict,
    parking_availability_data: list[dict],
    updated_parking_availability: dict,
    contextual_information: list[dict],
    *,
    data_validation_and_freshness_rules: dict,
    parking_policy_constraints: dict,
    decision_time: str,
) -> dict:
```

- `normalized_trip_requirements`: received, not used in the checks. Pass `{}`.
- `parking_availability_data`: a list of space-level sensor events `{space_id, lot_id, zone, status, timestamp}`. A timestamp is an offset-aware ISO 8601 string.
- `updated_parking_availability`: `{}`, or `{"lot_id": ..., "observations": [sensor events]}` during a status recheck. Its observations are validated together with `parking_availability_data`.
- `contextual_information`: a list of `{lot_id, walking_time_minutes}`.
- `data_validation_and_freshness_rules`: `{"stale_after_seconds": 120}`.
- `parking_policy_constraints`: received, not used here. Pass `{"rules": []}`.
- `decision_time`: offset-aware ISO 8601 string. It is both the freshness reference and the application clock.

It returns a dict with exactly these keys:

- `validated_parking_data`: a list with one record per lot that has at least one valid event: `{lot_id, occupied, capacity, observed_at}`.
  - `capacity` is the number of distinct spaces in that lot with a valid event.
  - `occupied` counts those spaces whose latest valid status is `occupied` or `unknown`.
  - `observed_at` is the newest valid observation time in the lot, as an ISO 8601 string.
- `validated_context_information`: the valid `{lot_id, walking_time_minutes}` records.
- `data_quality_and_freshness_status`: `{lot_id: "current" | "stale"}`, with an entry for every lot named by any event, including a lot with no valid event (which is `"stale"`).

A valid event has all five fields as non-empty strings, a `status` from the three allowed values, and a timestamp that parses, has a UTC offset, and is no more than 5 seconds ahead of `decision_time`. A timestamp exactly 5 seconds ahead is valid. Any other event is left out and raises nothing.

A stale lot **stays** in `validated_parking_data`; it is only marked `"stale"`.

**Known limit, do not test it:** `capacity` is derived from the events themselves, so `occupied` cannot exceed `capacity` for this input. DO-03's "occupied equal to capacity plus 1" case cannot be built through this interface.

## Requirements for A1.1 (verbatim)

- **DO-01 Confirmed Trip Request Output**: "The Trip Request Interpretation Module shall output Normalized Trip Requirements only after the driver confirms all six fields (destination, arrival time, departure time, vehicle category, declared eligibility and access needs) and their values pass the Trip Request Validation Rules."
- **SPEC Data Contract §5**: `arrival_time` is an "offset-aware ISO 8601 timestamp; must be no earlier than the request time and no more than 60 minutes after it." `departure_time` "must be later than `arrival_time`." `access_needs` is a required boolean.

## Interface of A1.1 (do not implement it)

```python
# module: prepare_eligible_parking_information.interpret_and_confirm_parking_requests
class InvalidTripRequest(ValueError): ...

def interpret_and_confirm_parking_requests(
    trip_information_and_parking_request: dict,
    confirmed_trip_requirements: dict,
    *,
    trip_request_validation_rules: dict,
) -> dict:
```

- `trip_information_and_parking_request`: `{"message": str, "submitted_at": offset-aware ISO 8601 str}`.
- `confirmed_trip_requirements`: the six fields. Test only this path, so always pass a non-empty dict. An empty dict calls a language model, which is not available in tests.
- `trip_request_validation_rules`: `{"arrival_window_minutes": 60}`, and optionally `"supported_values": {"destinations": [...], "vehicle_categories": [...], "eligibility_values": [...]}`. When present, the three matching fields must be on those lists.
- It returns `{"normalized_trip_requirements": {...the six fields only...}}`. Extra fields in the input are not copied.
- It raises `InvalidTripRequest` for a missing field, an empty or non-string destination, vehicle category or eligibility, a value not on a supplied list, a non-boolean `access_needs`, a time that cannot be parsed or has no UTC offset, an arrival outside the window, or a departure not later than the arrival.
- `submitted_at` is compared at minute precision: its seconds are dropped first. So with `submitted_at` 10:30:40, an arrival at 10:30:00 is accepted, and 11:30:00 is the latest accepted arrival.

## Requirements for A1.2 (verbatim)

- **DO-02 Information Request Issuance**: "The External Data Acquisition Module shall send one Availability Data Request, one Context Data Request and one Parking Policy Request for each confirmed trip request, and one Updated Availability Request for the selected parking area for each Status Recheck Request, with no more than 60 seconds between consecutive availability requests during pilot operation."

## Interface of A1.2 (do not implement it)

```python
# module: prepare_eligible_parking_information.request_parking_context_and_policy_information
def request_parking_context_and_policy_information(
    normalized_trip_requirements: dict,
    status_recheck_request: dict,
    *,
    information_acquisition_and_refresh_rules: dict,
    requested_at: str,
) -> dict:
```

- `status_recheck_request`: `{}`, or `{"lot_id": ...}` during a recheck.
- `information_acquisition_and_refresh_rules`: `{"refresh_interval_seconds": 60, "lot_ids": [...]}`.
- With no recheck, it returns exactly these three keys:
  - `availability_data_request`: `{"lot_ids", "as_of", "refresh_interval_seconds"}`
  - `context_data_request`: `{"destination"}`
  - `parking_policy_request`: `{"declared_eligibility", "access_needs"}`
- During a recheck, it returns exactly one key: `updated_availability_request`: `{"lot_id", "as_of"}`.
- `as_of` equals `requested_at`. The other values are copied from the inputs.
- The 60-second polling interval in DO-02 is not observable in this one call. Do not test it beyond `refresh_interval_seconds`.

## What to write

Write one pytest file, `tests/test_a1_modules_independent.py`. For A1.1, cover each rejection listed above, the window boundaries, and that a valid request returns exactly the six fields. For A1.2, cover the two return shapes. For A1.3, cover:

- the 119 s, 120 s and 121 s freshness boundaries;
- an event with no timestamp, an unparseable timestamp, and a timestamp with no UTC offset;
- timestamps 5 s and 6 s ahead of `decision_time`;
- a missing field and an invalid status;
- `unknown` counted as not available;
- two events for one space, where the newer one wins, in either order in the list;
- a lot whose events are all invalid;
- a stale lot staying in `validated_parking_data`;
- recheck observations being validated together with the other events;
- invalid context records (missing `lot_id`, negative, non-numeric).

For every test, write a one-line comment naming the requirement it comes from.

Output only the Python file.
