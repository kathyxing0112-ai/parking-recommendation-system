# Data and Model Adapters — Lab 8 Product Build

Context: SYSEN 5151 Team 26, Lab 8 Product Build (Lab Manual §8.5, p.148–149).
Branch: lab8-lab9-product-build. Task sheet items K1–K4 (Katherine Xing).

## Component Prompt Template — C.1.2 data access component

- **Context.** The Cornell Smart Parking Availability & Recommendation System
  recommends eligible pilot parking areas from simulated occupancy data. The
  data access component belongs to C.1.2 External Data Acquisition Module.
  It sits on A1's boundary with X.C.2 Parking Availability Data Sources.
- **Component.** C.1.2 External Data Acquisition Module (data access component).
- **Function performed.** A1.2 Request Parking, Context, and Policy
  Information. In this increment it covers only the parking-availability part.
- **Requirements.** SPEC.md Data Contract, "Common rules", section 1
  "Simulated parking-space sensor events" and section 3 "Pilot lot and space
  metadata", quoted verbatim from SPEC.md.
- **Interfaces.**
  - Input: Availability Data Request `{lot_ids, as_of}` and Updated
    Availability Request `{lot_id, as_of}`.
  - Output: Parking Availability Data, a list of `SensorEvent`, and Updated
    Parking Availability `{lot_id, observations}`, as defined in
    `contracts/api-v1.yaml`.
  - Error condition: an invalid event is rejected and recorded. It never
    becomes a vacant space.
- **Constraints.**
  - Python 3.13, standard library only (`sqlite3`).
  - Schema in `parking_data_access/schema.sql`.
  - Do not modify `contracts/` or the A1–A6 modules.
  - Local only.
- **Success criteria.** `tests/test_data_access.py` passes, and the existing
  suite results are unchanged.
- **Output format.** `schema.sql`, the package `__init__.py`, and the test
  file.
- **Out of scope.**
  - Do not judge freshness or staleness; that is A1.3.
  - Do not store the modeling table, the rule table, or trip records.
  - Add no dependencies and no caching or retries.

The simulated X.C.2 source was specified as follows:

- Three pilot lots, labeled `simulated_inventory`.
- Space-level events on a 30-second cadence.
- Occupancy redrawn every 15 minutes from an hourly weekday profile, with a
  fixed seed of 5151.
- The `LOT-1`–`LOT-3` ids already used by the walking skeleton.

The full weeks 1–15 generator and the train, validation and test split (K2)
are not part of this prompt.

## Component Prompt Template — C.1.1 language model adapter

- **Context.** As above. The adapter belongs to C.1.1 Trip Request
  Interpretation Module. It is the system's only call to the product's
  language model.
- **Component.** C.1.1 Trip Request Interpretation Module (model adapter).
- **Function performed.** A1.1 Interpret and Confirm Parking Requests.
- **Requirements.** These sources, quoted verbatim:
  - SPEC.md Model Response Contract, including its Fallback paragraph
  - SPEC.md Data Contract section 5
  - ADR-0002 Decision, first two bullets
  - SR-12
- **Interfaces.**
  - Input: `interpret_trip_request(message, *, submitted_at, supported_values, transport)`.
  - Output: the parsed contract object, or `{"status": "fallback", "reason"}`.
  - The prompt template, parameters, timeout, token limits, response schema
    and fallback reasons are exactly as in `docs/model-adapter.md`. That file
    was written and reviewed before generation.
- **Constraints.**
  - Python 3.13, standard library only (`urllib`, `json`).
  - Loopback Ollama endpoint only.
  - Raw messages and raw model output must not be logged or stored (SR-04).
  - Do not modify `contracts/` or the A1–A6 modules.
- **Success criteria.** `tests/test_model_adapter.py` passes without a
  running model. Every fallback reason is exercised.
- **Output format.** The adapter module and the test file.
- **Out of scope.**
  - No retries or repair prompts.
  - Do not extract fields from malformed output.
  - No explanation generation (ADR-0002).
  - No hosted API and no new dependencies.

## Wiring

`smart_parking_service` replaces the X.C.2 and language-model stubs one at a
time. The suite is run after each replacement, and the previous pass/fail
set must not change. `app.py` falls back to the six-field form when the
model is unavailable.
