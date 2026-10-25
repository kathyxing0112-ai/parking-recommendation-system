# ADR-0003: Internal Interface Contract and the Changes It Forced

## Status

Accepted

## Context

`contracts/api-v1.yaml` is now the authority on what crosses a first-level
function boundary (Lab Manual §7.4).

- **Source of the contract:** the model's internal-flow list, not the code:
  - flows I-01 to I-12 (`B2_Trace_Mapping.xlsx`, sheet 02 I-O Coverage,
    Innoslate V2)
  - the `SPEC.md` Data Contract
- **Stubs:** `contracts/generate_stubs.py` generates the stubs in
  `contracts/generated/` from the contract.
- **Conformance:** `tests/test_interface_contract.py` checks that each A1–A6
  module has exactly its stub's signature.

The V2 model names the twelve internal flows but defines fields for only four
of them. I-02, I-04, I-05 and I-06 have descriptions; the other eight have
none. The record shapes used since Chapter 5 were chosen by the assistant
from the SPEC Data Contract and accepted by the team as provisional, to be
confirmed by this contract (`docs/prompt-log.md`, 2026-10-18).

## Decision

1. **Contract structure.** There is one operation per receiving first-level
   function, A1–A6, and the twelve flows are component schemas. Each schema is
   labeled with its flow ID and trace numbers. Request properties carry
   `x-icom: input` or `x-icom: control`, which keeps the Chapter 4 ICOM
   convention: inputs are positional parameters and controls are keyword-only.
2. **Record shapes.** The team's provisional shapes become contract v1 where
   they trace to `SPEC.md`:
   - I-02 Validated Parking Data is lot-level: `occupied`, `capacity` and
     `observed_at` (SPEC modeling table).
   - I-04 is keyed by lot. Its values are `current` or `stale`.
   - I-07 is keyed by lot. Its values are `supported` or `unsupported`.
   - I-06 carries `capacity` (model description) and the 80% interval.
   - I-08 has `lot_id`, `walking_time_minutes`, `score` and `ranking_basis`.
3. **Protected Data Operation Request (I-09).** The request carries `role`
   and `operation`. It also carries `caller_session_id` and
   `record_session_id`, which SR-03's own-session rule needs, and
   `record_ids`, which a retention deletion needs. The team confirms these
   assistant-chosen field names.
4. **Trip Information and Parking Request (E-01).** This input is an object
   with `message` and `submitted_at`. The A1 signature changes from
   `str | dict` to `dict`, because data freshness is computed from the request
   submission time (Chapter 5 finding 2), so a bare message string cannot
   carry what A1 needs.
5. **Ranked Parking Recommendations (E-21).** The Lab 6 audit removed the
   orphan `"inputs"` payload. The output now carries `trip_summary`, the six
   confirmed trip fields from I-01 (flow 9.13 into A4), so the driver can
   re-check their own request. It also carries `advisory_notice` (SR-13).
   For the future UI, `trip_summary` belongs in a small, collapsed area of
   the results page, not as a main element.
6. **A4 test fixture.** The 1.4.4 test passed Ranked Parking Options as
   `{lot_id}` only. That violates I-08, so the fixture now carries the four
   required fields. The values follow the fallback that the test's
   unsupported forecasts imply. No assertion changed.

## Code changed to conform

- `prepare_eligible_parking_information`: the type of
  `trip_information_and_parking_request` changes from `str | dict` to `dict`
  (Decision 4).
- `smart_parking_service.find_suitable_parking`: `"inputs"` is removed and
  `"trip_summary"` is added (Decision 5, Lab 6 audit).
- `tests/test_functional_requirements.py`: the A4 ranked-options fixture is
  updated (Decision 6).
- No other A1–A6 signature changed. A2–A6 already matched their generated
  stubs.

## Model entities affected

| Entity | Effect | Model update needed |
|---|---|---|
| A1, A1.1; E-01 Trip Information and Parking Request | Signature type narrowed to an object with `message` and `submitted_at` | Added an E-01 description naming the submission time (done in Innoslate, 2026-10-25) |
| A4; E-21 Ranked Parking Recommendations; I-01 Normalized Trip Requirements (9.13) | `trip_summary` added, raw source data removed | Added an E-21 description listing `trip_summary` and `advisory_notice` (done, 2026-10-25) |
| A1, A4, A5, A6; I-09 Protected Data Operation Request | Session and record fields fixed | Added an I-09 description; the Approved Role-Permission Matrix description and SR-03 Validation Criteria now define the three-role matrix (done, 2026-10-25) |
| I-01, I-03, I-07, I-08, I-10, I-11, I-12 | Shapes fixed by this contract | These descriptions were empty in V2. They were added to match the contract, and I-02, I-04, I-05 and I-06 were revised to state their fields (done, 2026-10-25) |

The SR-13 Validation Criteria in Innoslate were also synchronized with `SPEC.md`:
displayed results must not state or imply that a space is reserved or
guaranteed (done, 2026-10-25).

## Divergences recorded, not resolved in this increment

- **`smart_parking_service` is not behind the contract yet.** It still
  implements UC.1.10–UC.1.14 as the walking-skeleton placeholder and does not
  call A1–A4. Its recommendation items use `rank`, `role`, `available_spaces`
  and `walking_time_minutes`, not the contract's `ParkingRecommendation`.
  Integration follows once the A1, A2 and A4 bodies exist, because wiring them
  now would break `app.py` with `NotImplementedError`.
- **The X.C.2 stubs return lot-level `available_spaces`.** They do not return
  the space-level `SensorEvent` that SPEC Data Contract section 1 and the
  contract's A1 request define. These are A0 boundary inputs, not internal
  flows. Alignment belongs to the Chapter 8 data adapters (§8.5).
- **SR-15 eligibility basis has no field.** SR-15 asks each option to show its
  eligibility basis. I-05 Eligible Parking Areas carries only `lot_id`, and
  the model defines no basis field. The contract does not invent one; it is
  left as an open item for the model.
- **`x-icom` sits beside `$ref`.** OpenAPI 3.0 ignores sibling keys of a
  `$ref`. `x-icom` and `description` are read by `generate_stubs.py` only, so
  generic OpenAPI tools will not see them.

## What Would Change This Decision

Any change to a flow's fields starts in the model and then in
`contracts/api-v1.yaml`. After that, the stubs are regenerated and the module
is changed until `tests/test_interface_contract.py` passes. The contract is
never edited to match the code.
