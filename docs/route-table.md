# Route Table — Endpoint-to-Use-Case Audit

Lab 6 audit (Lab Manual §6.4). This table lists every user-triggered entry point in
the application and the use case it serves.

- **Source of the entry-point list:** the read-only enumeration recorded in
  `prompts/2026-10-24-entry-point-enumeration.md`.
- **Source of the use-case mapping:** the team's own trace work, not the assistant:
  - `B2_Trace_Mapping.xlsx` (sheets 01 B2 Mapping and 02 I-O Coverage)
  - report Table 1 (*First-level functions and UC.1 coverage*)
- **Model baseline:** Innoslate V2 (`Team26_V2_Model.xml`).
- **Sequence numbers:** "Seq #" means the 1–16 numbers on the UC.1 sequence
  diagram (`Team26_Ch6_Trace.pptx`).

## Use cases in the model

The UC-ROOT Support Parking Selection branch contains one use case:

- **UC.1 Find Suitable Parking.** It has 23 actions and 16 numbered sequence
  interactions. The Cornell Driver (X.C.1) starts four of those interactions:
  Seq #1, #3, #11 and #13.

The model also has two standalone system actions. Neither belongs to UC-ROOT
or CTX.0. Both are performed by C.0:

- **SYS.1** Authorize Protected Data Operations: satisfies SR-03, and
  1.4.5 is traced to it.
- **SYS.2** Delete Expired Personal Records: satisfies SR-04.

The first-level functions A5 and A6 take their source from SYS.1 and SYS.2
respectively.

## Entry points

| # | Entry point | Triggered by | Use case | Sequence interactions (Seq #) | First-level functions (B2) |
|---|---|---|---|---|---|
| E1 | `python app.py` → `app.main()` | Cornell Driver (played by `app.py`) | UC.1 Find Suitable Parking | Runs E2–E5 in order: #1–#16 | A1–A4 |
| E2 | `cornell_driver_interface.submit_trip_request(message)` | Cornell Driver | UC.1 | #1 UC.1.1 Submit Trip Request → #2 UC.1.2 Interpret and Confirm Trip Request | A1 (A1.1) |
| E3 | `cornell_driver_interface.confirm_trip_requirements(trip_request)` | Cornell Driver | UC.1 | #3 UC.1.3 Confirm Trip Requirements → #4–#9 (UC.1.4–UC.1.9) → UC.1.10–UC.1.13 → #10 UC.1.14 Present Ranked Parking Recommendations | A1 → A2 → A3 → A4 |
| E4 | `cornell_driver_interface.select_parking_option(recommendations, lot_id)` | Cornell Driver | UC.1 | #11 UC.1.16 Select Parking Option → #12 UC.1.17 Present Selected Parking Information | A4 |
| E5 | `cornell_driver_interface.request_pre_arrival_recheck(lot_id)` | Cornell Driver | UC.1 | #13 UC.1.18 Request Pre-Arrival Status Recheck → #14 UC.1.19, #15 UC.1.20 → #16 UC.1.21 Present Updated Parking Status | A1 → A4 (P1/P3 refresh path) |

`app.show()` is a print helper that only `app.main()` calls, so it is not an
entry point. Nothing outside `app.py` and `cornell_driver_interface/` is called
directly by an actor. The following modules are reached only through E2–E5:

- `smart_parking_service`
- `language_model`
- the X.C.2–X.C.4 stubs: `parking_availability_data_sources`,
  `contextual_information_sources` and
  `cornell_transportation_and_parking_services`

## Not product entry points

| Command or function | Called by | Classification |
|---|---|---|
| `python -m pytest tests/ -v` | Developer, or CI (`.github/workflows/tests.yml`) | Verification harness. It is not a use-case entry point. It is the documented test command in SR-06 handoff task 4.  |
| A1–A6 module functions (`prepare_eligible_parking_information`, `estimate_arrival_time_availability`, `rank_parking_options`, `present_parking_recommendations_and_status`, `authorize_protected_data_operations`, `apply_personal_data_retention_rules`) | `tests/test_functional_requirements.py` and `tests/test_interface_contract.py` only | Internal first-level functions. No actor calls them, and no entry point reaches them yet. Integration behind the Chapter 7 contract is planned. |

## Orphans found and their disposition

No orphan entry points were found. Each of E1–E5 traces to UC.1.

The audit did find one orphan **payload**. Ranked Parking Recommendations (Seq
#10) carried data that traces to no output in the model:

| Finding | Origin | Disposition |
|---|---|---|
| `find_suitable_parking()` returned an `"inputs"` field containing the raw X.C.2, X.C.3 and X.C.4 responses (`availability`, `context`, `rules`) to the Cornell Driver | Commit `a38e516` (2026-10-18, *Align walking skeleton with updated UC.1 sequence diagram*). No prompt or requirement asked for it. | **Removed.** Raw source data is internal to the system and is not part of Ranked Parking Recommendations. |
| `"data_mode": "synthetic"` on recommendations and recheck results | Commit `47a1a1c` (Lab 2 walking skeleton) | **Kept.** SPEC requires simulated data to be labeled as simulated. |
| `"trip_summary"` (new) | Team decision in this audit | **Added** in place of `"inputs"`. See the note below. |

`trip_summary` holds the six confirmed trip fields from SR-12, so the driver can
re-check their own request on the results screen. It traces to Normalized Trip
Requirements, which A4 receives as flow 9.13, so presenting it inside Ranked
Parking Recommendations is consistent with the model.

- It is to be added to the Ranked Parking Recommendations schema in
  `contracts/api-v1.yaml` and recorded in the Chapter 7 ADR.
- Display note for the future UI, not this increment: show it in a small,
  collapsed area of the results page, not as a main element.

## Model actions with no entry point

| Model entity | Status | Note |
|---|---|---|
| SYS.2 Delete Expired Personal Records (A6) | **Planned — Chapter 8** | A scheduled deletion has no actor-triggered entry point. A6 already identifies expired records and authorizes their deletion. The scheduler and physical deletion arrive with the Chapter 8 storage adapter (see `docs/traceability.md`). |
| SYS.1 Authorize Protected Data Operations (A5) | **Planned — Chapter 8** | No actor triggers SYS.1 directly. It is reached only through protected operations from A1, A4 or A6, and none of those exists yet. Outside the selected UC.1 trace (P2 decision b): storing the confirmed trip record at UC.1.3 is a protected operation that the trace does not show as a separate interaction. |
| UC.1.15 Review Parking Recommendations; UC.1.22 Proceed to Selected Parking Area; UC.1.23 Park and Complete Trip | Not applicable | The Driver performs these actions without sending any message to the system. They have no sequence interaction, so they need no entry point. |

## Count reconciliation

| Item | Model (V2) | Repository |
|---|---|---|
| Use cases | 1 (UC.1) | 1 served (UC.1) |
| Driver-initiated interactions in UC.1 | 4 (Seq #1, #3, #11, #13) | 4 driver-interface entry points (E2–E5), plus the `app.py` command (E1) that runs them |
| Entry-point-to-use-case traces | — | 5, all to UC.1 (E1–E5) |
| Numbered UC.1 interactions | 16 | 16 messages implemented in the walking skeleton (`docs/walking-skeleton.md`) |
| System-performed UC.1 actions | 12 (report Table 1) | 12. UC.1.10–UC.1.13 are still a single placeholder inside `find_suitable_parking()`. |
| System actions outside UC.1 | 2 (SYS.1, SYS.2) | 0 entry points; both planned for Chapter 8 |
| Orphan entry points | 0 allowed | 0 |
