# Personal Trip Record — Fields, Sample Data, and Current Storage Behavior

This file answers the review of ISS-RET-01 and ISS-RET-02 (SR-04, NFR.9,
DO-09, C.1 spec 2.3.5).

- **What it covers:** runtime data the product creates while a driver uses
  it. It does **not** cover model training data. Qwen3 is never trained or
  fine-tuned (ADR-0002). The parking occupancy data is non-identifying and
  falls outside SR-04 (SPEC.md, "Retention and evaluation boundary").
- **Sample records:** `docs/examples/simulated_trip_records.json`. All values
  in it are simulated.

## 1. Trip record fields

SPEC.md allows the pilot to keep three things: the "confirmed structured trip
fields, recommendation output, and submission time". The record below holds
only those, plus the two identifiers the interface contract already uses.

| Field | Type | Required | Source | Notes |
|---|---|---|---|---|
| `record_id` | string | yes | I-11 `PersonalRecordsAndRetentionMetadata` | Identifies the record for deletion (I-09 `record_ids`) |
| `session_id` | string | yes | I-09 `record_session_id` | Lets SR-03 apply the own-session rule |
| `submitted_at` | string, ISO 8601 with UTC offset | yes | I-11; E-01 `submitted_at` | The 24-hour retention period starts here |
| `trip_request.destination` | string, from the supported destination list | yes | SPEC Data Contract §5 | |
| `trip_request.arrival_time` | string, ISO 8601 with UTC offset | yes | §5 | No earlier than `submitted_at` and at most 60 minutes after it |
| `trip_request.departure_time` | string, ISO 8601 with UTC offset | yes | §5 | Later than `arrival_time` |
| `trip_request.vehicle_category` | string, from the approved list | yes | §5 | |
| `trip_request.declared_eligibility` | string, from the approved list | yes | §5 | |
| `trip_request.access_needs` | boolean | yes | §5 | |
| `recommendation_output` | array of 0–2 items | yes (may be empty) | I-08 `RankedParkingOptions` | Empty when no eligible area exists |
| `recommendation_output[].lot_id` | string | yes | I-08 | |
| `recommendation_output[].walking_time_minutes` | number ≥ 0, minutes | yes | I-08 | |
| `recommendation_output[].score` | number from 0 to 1, or null | yes | I-08 | null when the ranking uses the walking-time fallback |
| `recommendation_output[].ranking_basis` | `score` or `fallback_walking_time` | yes | I-08 | |

**Derived, not stored:** the expiry time, `submitted_at + 24 h`. A6
recalculates it each time from the approved retention schedule
(`retention_hours: 24`).

**Never retained (SR-04):**

- The raw chatbot message.
- The raw model output.
- Rejected or discarded model replies.

The value lists for destination, vehicle category and eligibility are still
provisional (prompt log 2026-10-04, deferred item 3).

## 2. Sample records

These are simulated. The inspection time is `2026-10-30T12:00:00-04:00`, and
the retention period is 24 hours.

| record_id | submitted_at | Expires at | Age at inspection | Expected disposition |
|---|---|---|---|---|
| TR-SIM-001 | 2026-10-29 11:59:00 −04:00 | 2026-10-30 11:59:00 | 24 h 01 min | Delete (past expiry) |
| TR-SIM-002 | 2026-10-29 12:01:00 −04:00 | 2026-10-30 12:01:00 | 23 h 59 min | Keep (just before expiry) |
| TR-SIM-003 | 2026-10-30 10:30:00 −04:00 | 2026-10-31 10:30:00 | 1 h 30 min | Keep. Has no eligible option, so `recommendation_output` is empty |

TR-SIM-001 and TR-SIM-002 are the SR-04 cases on either side of the expiry,
one just after and one just before. All three trip requests pass the
adapter's Data Contract §5 checks.

## 3. Where trip data actually is today (as of commit `d301e6b`)

| Location | Holds trip data? | Current behavior |
|---|---|---|
| Application database (`parking_data_access`, in-memory SQLite) | No | Holds only lot and space inventory and simulated sensor events. There is no trip-record table yet |
| Process memory (`smart_parking_service`) | Yes, while the request runs | The confirmed request and the recommendations exist only as function values. Nothing is kept after the run ends |
| Application logs | No | The application writes no log files. The model adapter does not log messages or replies |
| Terminal output from `python app.py` | Yes (demo only) | The demo prints the confirmed trip and the recommendations to the console. Nothing is written to disk |
| Local Ollama process (Qwen3 4B) | Gets the raw message while it interprets it | The call goes to `127.0.0.1` only. **Not verified:** whether Ollama's own server log keeps prompt text. Check this once Ollama is installed |
| Cache | No | The pilot has no cache |
| Backups | No | The pilot has no backups |

## 4. Deletion: what exists and what does not

- **A6 (`apply_personal_data_retention_rules`):**
  - Finds records where `now ≥ submitted_at + 24 h`, using the C.0 system
    clock.
  - Sends I-09 to A5 with role `retention_service` and operation
    `delete_expired_trip_record`.
  - Lists those records in I-12 `authorized_for_deletion`, but only if A5
    permits it.
- **Physical deletion:** **not implemented.** No component deletes a stored
  record yet, because no trip-record store exists.
- **Existing test evidence:** `test_FR_1_4_6_applies_personal_data_retention_rules`
  (`tests/test_functional_requirements.py`) covers the decision only.
  - Records aged 25 h and 24 h 01 min are authorized for deletion.
  - Records aged 23 h 59 min and 1 h are kept.
  - Nothing is authorized when A5 denies the operation.
  - The test asserts that no `deleted` result exists. There is **no**
    deletion test and **no** timing evidence for NFR.9's 60 seconds yet.

## 5. Open decisions for the team (not decided here)

1. Where trip records are stored, if they are stored at all: for example an
   application database table, or memory only. SR-04 requires the retained
   fields and storage locations to be listed before pilot requests are
   collected.
2. Which component physically deletes records. DO-09 now covers only
   building the disposition list.
3. The time budget from expiry to confirmed deletion, which must fit inside
   NFR.9's 60 seconds. This covers the expiry check, A5 authorization, the
   disposition list, the deletion itself, and the deletion check. It depends
   on how often A6 runs; the schedule is not set.
4. Whether the demo console output and the Ollama server log count as
   "logs" under SR-04's inspection scope.
