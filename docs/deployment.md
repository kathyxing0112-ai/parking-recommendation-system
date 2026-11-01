# Component and Deployment View

Lab Manual §8.5.2. This view shows what runs where and what talks to what in
the pilot. Subsystem names and numbers follow the team's asset naming
(`Team26_Ch8-9` task sheet, sheet 资产命名), which B1 and B3 enter into
Innoslate. If the model renames an asset, this file changes to match.

## Deployment: one machine, one process, local model

The pilot runs on one developer machine. Nothing in the pilot is hosted.

| Node | What runs there | Talks to |
|---|---|---|
| Developer machine, Python 3.13 process (`python app.py`) | C.0 and all six subsystems C.1–C.6 as in-process Python packages; the simulated X.C.2 feed; the SQLite parking data store | Ollama over loopback HTTP |
| Same machine, Ollama server (`127.0.0.1:11434`) | Qwen3 4B (`qwen3:4b`) | Nothing. It only answers the Python process |
| GitHub Actions runner | `python -m pytest tests/` | Nothing. CI does not start Ollama; the adapter tests use a fake transport |

**No project data leaves the machine.** The model adapter's only endpoint is
`http://127.0.0.1:11434/api/chat`, a loopback address
(`tests/test_model_adapter.py::test_model_endpoint_is_local`). The data store
is a local SQLite database. The pilot calls no hosted API. Data stays local,
as the Lab Manual's data-security note asks, even though all pilot data is
simulated.

X.C.5 Cloud and Network Infrastructure has no part in the pilot. Hosting
is still the open decision recorded in ADR-0001.

## Components

C.0 Cornell Smart Parking Availability & Recommendation System is made up of
six first-level subsystems. Each one performs exactly one first-level function.

| Asset | Name | Performs | Code | State in this increment |
|---|---|---|---|---|
| C.1 | Parking Information Subsystem | A1 Prepare Eligible Parking Information | `prepare_eligible_parking_information/` | Signature only; body pending. Its data access component and model adapter are built (below) |
| C.2 | Availability Forecasting Subsystem | A2 Estimate Arrival Time Availability | `estimate_arrival_time_availability/` | Signature only; waits for the forecast model (ADR-0002) |
| C.3 | Recommendation Ranking Subsystem | A3 Rank Parking Options | `rank_parking_options/` | Implemented |
| C.4 | Driver Presentation Subsystem | A4 Present Parking Recommendations and Status | `present_parking_recommendations_and_status/` | Signature only; body pending |
| C.5 | Access Authorization Subsystem | A5 Authorize Protected Data Operations | `authorize_protected_data_operations/` | Implemented |
| C.6 | Data Retention Subsystem | A6 Apply Personal Data Retention Rules | `apply_personal_data_retention_rules/` | Implemented (deletion authorized, not yet physical) |

C.1 is decomposed to the second level:

| Asset | Name | Performs | Code |
|---|---|---|---|
| C.1.1 | Trip Request Interpretation Module | A1.1 Interpret and Confirm Parking Requests | **Model adapter** `language_model/` |
| C.1.2 | External Data Acquisition Module | A1.2 Request Parking, Context, and Policy Information | **Data access component** `parking_data_access/` |
| C.1.3 | Data Validation Module | A1.3 Validate Parking and Context Information | Not built yet |
| C.1.4 | Eligibility Filter Module | A1.4 Determine Eligible Parking Areas | `prepare_eligible_parking_information/determine_eligible_parking_areas.py`, generated once from the C.1 specification (Lab 9.4). Not yet called by A1; see `docs/deviation-log.md` |

Two more packages are part of C.0 but are not functions on the IDEF0
(`docs/traceability.md`): `smart_parking_service/` puts the UC.1 messages in
order, and `cornell_driver_interface/` is the system side of X.C.1. Until A1,
A2 and A4 have bodies, `smart_parking_service` calls the C.1.1 and C.1.2
components directly (ADR-0003, divergences).

## What talks to what

```
Cornell Driver (X.C.1)
   │ app.py plays the driver
   ▼
cornell_driver_interface ──► smart_parking_service
                                 │
          ┌──────────────────────┼──────────────────────────┐
          ▼                      ▼                          ▼
 C.1.1 model adapter     C.1.2 data access component   X.C.3 / X.C.4 stubs
 language_model/         parking_data_access/          (walking times, rules)
          │ HTTP, loopback        │ SQLite (schema.sql)
          ▼                      ▼
 Ollama + Qwen3 4B       X.C.2 simulated sensor feed
 (local process)         parking_availability_data_sources/
```

| From | To | What crosses | Interface definition |
|---|---|---|---|
| C.1.1 model adapter | Ollama / Qwen3 4B | One `/api/chat` request with the driver message, the current time and the supported values. The reply is a JSON object | `docs/model-adapter.md`; SPEC.md Model Response Contract |
| C.1.2 data access component | X.C.2 simulated feed | Availability Data Request and Updated Availability Request; the reply is space-level sensor events | `contracts/api-v1.yaml` `SensorEvent`, `UpdatedParkingAvailability`; SPEC Data Contract §1 |
| C.1.2 data access component | SQLite store | Lot and space inventory (§3), accepted and rejected sensor events (§1) | `parking_data_access/schema.sql` |
| `smart_parking_service` | X.C.3, X.C.4 | Walking times; parking rules and closures | Still Chapter 2 stubs. They are not data sources in Lab 8.5's sense. A draft §4 rule table (`get_rule_table()`) is ready for C.1.4; the stub is replaced when C.1.4 uses it |

## Data access component (C.1.2)

- **Interface.** `ParkingDataStore.request_parking_availability({"lot_ids", "as_of"})`
  returns Parking Availability Data as a list of `SensorEvent`. This is the
  A1 input type in the contract. `request_updated_parking_availability({"lot_id", "as_of"})`
  returns `{"lot_id", "observations"}`.
- **Source.** The source is the seeded simulator in
  `parking_availability_data_sources/` (seed 5151). It has three pilot lots
  and 470 spaces, and it reports every 30 seconds. The lots are named Hoy
  Road Garage (LOT-1), Peterson Lot (LOT-2) and Campus Road O Area (LOT-3). Lots, capacities and
  occupancy are all simulator assumptions, labeled `simulated_inventory`.
- **Checks at ingestion (SPEC Data Contract §1, §3):**
  - The space must exist, and its lot and zone must match the inventory.
  - The status must be `occupied`, `vacant` or `unknown`.
  - The timestamp must be offset-aware and no more than 5 s ahead of the
    application clock.
  - Duplicates are dropped.
  - Rejected events are recorded in `rejected_events`. They are never turned
    into vacant spaces.
  - Space counts must reconcile with `capacity_by_zone`.
  - These checks are defensive only. They keep malformed or impossible
    events out of the store. They do not replace A1.3 Validate Parking and
    Context Information (C.1.3), which still decides whether data is valid
    and fresh enough to use. No function moves between components, so no
    ADR is needed.
- **Query.** For each space, the latest event at or before the decision time
  wins, so a late event cannot replace a newer one. The component does not
  judge freshness. A1.3 marks an observation stale after 120 s (SR-09).
- **Not stored yet.** The data store does not yet hold:
  - Section 2, the 15-minute modeling table. It arrives with the weeks 1–15
    simulator and the forecast comparison (ADR-0002).
  - Section 4, the rule table. A draft now lives with X.C.4 in
    `cornell_transportation_and_parking_services/parking_rules_draft.json`
    and is read through `get_rule_table()`. It is labeled unconfirmed and
    stays out of the store until the team confirms it.
  - Trip records. These are personal data under SR-04 and wait for the A6
    storage adapter.
  - The database is in memory and is rebuilt on each run.

## Model adapter (C.1.1)

Specified in `docs/model-adapter.md`. The adapter makes one call to
`qwen3:4b` with temperature 0, a fixed seed, JSON-schema output, 512 output
tokens and a 60 s timeout. The model copies the six fields, with null for
anything not stated and times as `HH:MM`. The adapter checks each value and
assembles the Model Response Contract object. A value it cannot use is
listed as missing, never replaced. If the reply is not a JSON object with
exactly the six fields, or is truncated, or if the model cannot be reached,
the adapter returns `{"status": "fallback"}`. The driver then gets the
six-field form, and no raw output or internal error is shown. Raw messages
are not logged. `scripts/live_model_check.py` runs the real model by hand;
CI does not.
