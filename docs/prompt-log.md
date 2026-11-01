# Prompt Log

## 2026-09-20 — Katherine Xing — Codex

- Built from: `SYSEN_5151_Innoslate_Lab_Manual_v3_0_23_5_5.pdf`, `Wk03_Business_Mission_Analysis_Behavior.pdf`, and the team Business or Mission Analysis document
- Prompt: Asked the assistant to identify the Chapter 1 repository scaffold requirements, explain the required files, and draft content for `README.md` and `docs/context.md`
- Reviewed by: Katherine Xing
- Accepted: Repository structure
- Rejected or removed: Any unrequested application functionality, API endpoint, sample parking data, or behavior beyond the repository scaffold
- Assistant assumptions: External interface protocols, data formats, authentication methods, and update frequencies have not yet been selected and were therefore documented as not yet specified

## 2026-09-20 — Katherine Xing — Codex

- Built from: Chapter 1 toolchain requirements, the current local development environment, and the project’s anticipated FastAPI and LLM needs
- Prompt: Asked the assistant to compare local and hosted LLM options, evaluate whether Docker was necessary, recommend an initial model runner and model, and draft `docs/adr/0001-initial-toolchain.md`
- Reviewed by: Katherine Xing
- Accepted: Python 3.13, a local Python virtual environment, PyCharm and Visual Studio Code, and evaluation of Ollama with Qwen3 4B as the initial candidate
- Rejected or removed: Immediate Docker configuration, paid hosted API integration, larger local models, and untested Python dependencies
- Assistant assumptions: The LLM will initially explain recommendations rather than perform the core parking ranking logic, and the initial prototype will be developed and demonstrated locally
## 2026-09-20 — Katherine Xing — Claude

- Built from: `docs/walking-skeleton.md` (UC.1 sequence, 10 calls); no requirements exist yet — the code traces to UC.1 and the sequence diagram, not to a requirement ID
- Prompt: Asked the assistant to implement each participant in the UC.1 call list as a stub returning a hard-coded value of the correct shape, and to wire them so one Cornell Driver action traverses every participant and returns
- Reviewed by: Katherine Xing
- Accepted: The six participant stubs, the `smart_parking_service` orchestration layer, the `recommendation_model` stand-in for the local language model, and the `app.py` entry point that runs one driver action end to end. During review the `ranked_options` value was changed from a pass-through of the availability list to a hard-coded value carrying a `rank` field, so the returned shape matches the message name in call 10 of the sequence diagram ("return ranked parking recommendations"); no ranking is computed
- Rejected or removed: An earlier assistant-generated version that added FastAPI, uvicorn, and pydantic as dependencies; pydantic field validation on the trip request; a real availability/vehicle-type/eligibility filtering chain; a ranking algorithm sorting on walking time and available spaces; and HTTP error handling returning 422. None of these is specified yet, all three dependencies are absent from `docs/environment.md`, and the data contract they assumed belongs to `SPEC.md` in Chapter 3. They were removed rather than kept so they do not surface as orphans in the Chapter 6 audit
- Assistant assumptions: Assumed the `Recommendation Model` participant belongs in the UC.1 call list because ADR-0001 commits to a local model for explaining recommendations. Because that decision runs the model locally, it is treated as a component internal to the system-of-interest rather than an external system, so it does not appear on the system context diagram, the Universe hierarchy, or the use case diagram, and needs no lifeline of its own in the sequence diagram, which shows interactions between actors rather than actions internal to one. During review the Chapter 1 package `cornell_driver/` was renamed to `cornell_driver_interface/`: X.C.1 is a person, so what the repository holds is the system's interface to that actor, following the naming pattern Chapter 1 uses for boundary elements. The call list was expanded from ten calls to twelve so that the human actor and that interface are separate participants. Assumed `Cloud and Network Infrastructure` (X.C.5) is an enabling system outside this call sequence and therefore needs no stub

## 2026-10-04 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: Draft `SPEC.md` (Needs and Acceptance Criteria for SN-01–SN-08 and SR-01–SR-15, Data Contract, and Model Response Contract); the team's Stakeholder Needs Analysis and Requirements Definition report (Table 3.1 and Table 4.1); Lab Manual §3.5; `docs/adr/0001-initial-toolchain.md`; `docs/walking-skeleton.md`; and the team-written red acceptance suite `tests/test_spec_acceptance.py` with `.github/workflows/tests.yml`
- Prompt: Asked the assistant to check `SPEC.md` against the report, identify conflicts between the Data Contract and the Model Response Contract, identify acceptance criteria that could not be evaluated objectively or were ambiguous about units or conditions, and check whether the failing tests and CI configuration met the Chapter 3 build steps. The assistant was asked to flag issues, not to write needs or criteria
- Reviewed by: Katherine Xing. All needs, requirements, acceptance criteria, and decisions remain the team's own. For some sentences, the assistant suggested English wording after the team had made the decision; the team edited that wording before adding it to `SPEC.md`. These sentences cover user editing before confirmation, the arrival-time window, the forecast-horizon rounding rule, the walking-time-only ranking fallback, the normalization TBD, and the `access_needs` missing-field rule
- Accepted: The team revised `SPEC.md` in response to these findings:
  (1) `declared_eligibility` cannot be unknown; a request with an unknown value is blocked until it is corrected. The SR-10 and Common rules statements now refer to "an option whose eligibility is not resolved by a confirmed rule."
  (2) The user-confirmed values, including any edits the user makes before confirming, enter the pipeline, and edited values are validated again. The fallback condition "content inconsistent with the user's confirmed input" was removed.
  (3) The language model only interprets chatbot input. This change is recorded in ADR-0002, and ADR-0001 is marked partially superseded.
  (4) "LightGBM" in the fallback was replaced with "the forecasting model."
  (5) "Raw assistant messages" was replaced with "raw chatbot messages," so that the product's chatbot is not confused with the development assistant.
  (6) The SR-04 inspection scope now lists the database, cache, logs, and backups, matching the report and the retention section.
  (7) `arrival_time` must be no earlier than the request time and no more than 60 minutes after it, and SR-14 uses the nearest 15-minute forecast horizon. The examples were updated to match, and the same window was added to the SR-12 validation criteria in the report.
  (8) When any eligible area lacks a supported forecast, SR-13 ranks all eligible areas by walking time alone, and the explanation states that forecasts are unavailable.
  (9) SR-11 now specifies exactly 10 participants and a median task completion time of no more than 60 seconds.
  (10) The sensor timestamp tolerance is 5 seconds ahead of the application clock.
  (11) The SR-05 MOE target is zero requirement-changing pull requests merged while a blocking ambiguity remains unresolved, and the SR-07 MOE target is zero.
  (12) The sentence referring to an unavailable screenshot was removed.
  The assistant also made two documentation edits directly, and Katherine Xing reviewed and accepted both: it removed a leftover comment from `requirements.txt`, and it added the Qwen3 4B role and the LightGBM forecasting candidate to `docs/environment.md`
- Rejected or removed: The suggestion to make `access_needs` default to `false` was rejected, because the team chose not to assume that a driver does not need accessible parking. The field remains required, and the model lists it as missing rather than assuming a value
- Deferred: (1) The method for normalizing walking time, availability, and uncertainty in SR-13 is recorded as TBD, to be agreed by the team before evaluation. (2) The walking-time data source is not yet in the Data Contract, because the team has not decided whether a map service is needed to obtain walking time or distance. (3) The accepted values for `vehicle_category` and `declared_eligibility` will be listed after the team collects them. (4) Walking-skeleton calls 9–10 ("request recommendation explanation") will be updated in the Innoslate model and in `docs/walking-skeleton.md` when the language model is implemented
- Assistant assumptions: None. This was a critique, not a generation, apart from the two documentation edits listed under Accepted
## 2026-10-07 — Katherine Xing — Claude (Opus 5.5)

- Built from: The updated UC.1 sequence diagram in Innoslate (messages UC.1.1–UC.1.21); `SPEC.md` (six-field trip request, Model Response Contract, SR-13, SR-14); `docs/adr/0002-model-responsibilities-and-forecast-candidate.md`; and the team's report (Table 3.1)
- Prompt: Asked the assistant to align the walking skeleton with the updated UC.1 sequence diagram and the six-field trip contract, keep every participant a stub, and synchronize `SPEC.md` SR-13 and SR-14 with the report
- Reviewed by: Katherine Xing
- Accepted: `app.py` now plays the Cornell Driver through UC.1.1–UC.1.21 and labels each printed step with its message identifier. `recommendation_model/` was renamed `language_model/` and now only interprets the driver's message (UC.1.2), per ADR-0002; explanations are derived in `smart_parking_service` from the factors it used (SR-15). The X.C.4 stub was renamed `get_parking_rules_and_closures()` to match UC.1.8, and X.C.2 gained `get_updated_parking_availability()` for UC.1.19/UC.1.20. Stubs now return two lots so a primary and a backup option exist. `docs/walking-skeleton.md` was rewritten as a message-to-code table replacing the Lab 2 call list; `README.md` and `docs/context.md` were updated for the six-field contract. `SPEC.md` now states the SR-13 scoring and tie-break rules and SR-14 interpolation from the report, and cites the SYSEN 5151 Team 26 report
- Rejected or removed: No real validation, filtering, forecasting, or scoring was added; UC.1.10–UC.1.13 remain one placeholder, so no unspecified behavior surfaces as an orphan in the Chapter 6 audit
- Deferred: Deferred item (4) from 2026-10-04 is closed by this entry. The skeleton issues each external request and receives its response before the next, whereas the diagram shows three requests before three responses
- Assistant assumptions: UC.1.15 and the trip-completion Actions after UC.1.21 have no message in the sequence diagram and are left out of the skeleton

## 2026-10-18 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: A0 Provide Parking Decision Support and its first-level functions A1–A6 (IDEF0, Innoslate model v3); the ICOM allocation in Table 4 of the team's Chapter 4–5 report section; Lab Manual §4.4
- Prompt: Asked the assistant to create one module per first-level function, named with the function's verb phrase, with a signature written from the function's ICOMs only (inputs as parameters, controls as keyword-only parameters, outputs as return values, mechanisms as injected dependencies), a docstring stating the function identifier, unimplemented bodies, and `docs/traceability.md` mapping each function to its module
- Reviewed by: Katherine Xing — checked the input, control, and output counts of each signature against Table 4 and accepted all six signatures and `docs/traceability.md`. Accepted two decisions the assistant proposed: (1) A1.1–A1.4 are implemented inside `prepare_eligible_parking_information/` rather than as separate modules, because the build step asks for one module per top-level function; (2) `smart_parking_service/`, `cornell_driver_interface/`, `language_model/`, and the external-participant stubs are not functions on the IDEF0, so they are unchanged and have no traceability row
- Rejected or removed: None
- Deferred: Two modeling findings from the signatures. (1) Every function's mechanism is C.0, so no signature has an injected dependency, although A1.1 will use the local language model and A2 the forecasting model; this will be revisited in the physical architecture. (2) A1 and A4 receive inputs that arrive at different times (for example, the trip request and the status recheck request), so the Chapter 5 bodies must handle inputs that are not yet present
- Assistant assumptions: Parameter types (`dict`, `list[dict]`, `str | dict`) are not specified by the model; they were chosen to match the shapes in `SPEC.md` and the walking skeleton and will be confirmed by the internal interface contract in Chapter 7

## 2026-10-18 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: System functional requirements 1.4.1–1.4.6 (children of 1.4 Provide Parking Decision Support, Innoslate model v3) and the first-level functions A1–A6 they correspond to; the stakeholder requirements each function traces to in Table 2 of the team's Chapter 4–5 report section, with their acceptance criteria in `SPEC.md`; the Chapter 4 signatures; Lab Manual §5.3
- Prompt: Asked the assistant to write one test per functional requirement, named with the requirement identifier and derived from the requirement text rather than from any code, to extend `docs/traceability.md` with requirement and test columns, and to leave every module body unimplemented. Implementations will be generated in a separate session
- Reviewed by: Katherine Xing — accepted all six tests in `tests/test_functional_requirements.py` and the extended `docs/traceability.md`. All six fail with `NotImplementedError`, so the build is red for the right reason. At Katherine Xing's instruction, the assistant also rewrote the SR-03 acceptance criterion in `SPEC.md` (see Accepted)
- Accepted: The tests check the following, taken from the traced stakeholder requirements: 1.4.1, that the confirmed six fields are preserved (SR-12), closed areas are excluded (SR-10), and an observation older than 120 seconds is marked stale (SR-09); 1.4.2, that no forecast is produced from stale data and that a supported estimate lies within its interval and the area capacity (SR-14); 1.4.3, the SR-13 score order and the walking-time fallback; 1.4.4, the stale label with the last-observed time, an explanation for every option, and no implied reservation or guarantee (SR-09, SR-15, SR-13); 1.4.5, that only operations in the role-permission matrix are permitted and unknown roles are denied (SR-03); 1.4.6, that records older than 24 hours are deleted only when authorized (SR-04). The assistant raised four findings, and the team resolved them as follows. (1) Requirements 1.4.1–1.4.6 state only the function name and have no verification criteria; the team assigned a member to add verification criteria in Innoslate and the report. (2) The IDEF0 has no current-time input; the team added to the A1.3 and A6 descriptions in Innoslate that data freshness is computed from the request submission time and record expiry from the C.0 system clock. (3) A3 needs area capacity for the SR-13 score, but its inputs carry none; the team added to the description of Arrival-Time Availability Estimates in Innoslate, and to the report, that each estimate carries its area capacity. (4) The record shapes inside inputs and controls were chosen by the assistant from the `SPEC.md` Data Contract; the team accepted them, to be confirmed in the Chapter 7 interface contract. The assistant also identified that `SPEC.md` SR-03 (driver and maintainer) and the report's A5 design (driver and Retention Service) described different role matrices. The team merged them into a three-role matrix (driver, maintainer, Retention Service), updated the report and the Approved Role-Permission Matrix entity in Innoslate, and updated the 1.4.5 test to match
- Rejected or removed: None
- Deferred: Verification criteria for 1.4.1–1.4.6 are in progress by a teammate. Maintainer configuration requests have no source function in the current IDEF0, because maintenance is outside UC.1; this is recorded in the report's Open Decisions
- Assistant assumptions: The record shapes and field names in the test inputs (for example `data_quality_and_freshness_status` values "current" and "stale", and `forecast_validity_status` values "supported" and "unsupported") were not specified by the model; the team accepted them as described in finding (4)

## 2026-10-18 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: A5 Authorize Protected Data Operations; requirement 1.4.5; SR-03 (`SPEC.md`, three-role matrix); the failing test `test_FR_1_4_5_authorizes_protected_data_operations`
- Prompt: see `prompts/2026-10-18-module-bodies.md` (A5), run in a new session separate from the one that wrote the tests
- Reviewed by: Katherine Xing, who also ran the generation; no other team member reviewed this module. Accepted as generated: the body looks up the operations permitted for the request's role and denies any role not in the matrix. The test passed on the first run, and no test file was modified
- Rejected or removed: None
- Assistant assumptions: None

## 2026-10-18 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: A6 Apply Personal Data Retention Rules; requirement 1.4.6; SR-04 (`SPEC.md`); the A6 model description (expiry judged against the C.0 system clock); the failing test `test_FR_1_4_6_applies_personal_data_retention_rules`
- Prompt: see `prompts/2026-10-18-module-bodies.md` (A6), run in a new session separate from the one that wrote the tests
- Reviewed by: Katherine Xing, who also ran the generation; no other team member reviewed this module. Accepted as generated: records whose submission time plus the scheduled retention period has passed are identified as expired and deleted only when the authorization decision permits it. The test passed on the first run, and no test file was modified
- Rejected or removed: None
- Assistant assumptions: The delete request sent to A5 uses the role `retention_service` and the operation `delete_expired_trip_record`, matching the three-role matrix in `SPEC.md` SR-03. Accepted

## 2026-10-18 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: A3 Rank Parking Options; requirement 1.4.3; SR-13 (`SPEC.md`, score, tie-break, and fallback rules); the failing test `test_FR_1_4_3_ranks_parking_options`
- Prompt: see `prompts/2026-10-18-module-bodies.md` (A3), run in a new session separate from the one that wrote the tests
- Reviewed by: Katherine Xing, who also ran the generation; no other team member reviewed this module. Accepted as generated; the test passed on the first run, and no test file was modified. During review, the test-writing session found that the body raised `ValueError` when there were no eligible areas, a case the test did not cover; see the next entry
- Rejected or removed: None
- Assistant assumptions: Each returned option also carries `score`, `walking_time_minutes`, and `ranking_basis` ("score" or "fallback_walking_time"), and `_is_valid_estimate` treats a malformed estimate as invalid. None of these was in the prompt. The team kept them: `ranking_basis` provides the labeled fallback that SR-13 requires, the score and walking time support the explanations in SR-15, and treating a malformed estimate as invalid follows the SR-13 fallback rule

## 2026-10-18 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: 1.4.3; SR-13 ("With one eligible area, show one option; with none, state that no confirmed eligible option is available"); the extended test `test_FR_1_4_3_ranks_parking_options`
- Prompt: In the test-writing session, the assistant added the one- and zero-eligible-area cases from SR-13 to the 1.4.3 test, which then failed with `ValueError: min() iterable argument is empty`. The fix was generated in a new session; see `prompts/2026-10-18-module-bodies.md` (A3 — Fix for zero eligible areas)
- Reviewed by: Katherine Xing, who also ran the generation. Accepted: a two-line change that returns an empty list when no area is eligible. The extended test passes, and the test was not modified by the fix session
- Rejected or removed: None
- Assistant assumptions: None. The gap was in the test coverage of SR-13, not in the requirement

## 2026-10-18 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: Review comments on PR #4; requirements 1.4.4, 1.4.5, 1.4.6; SR-03, SR-04, SR-13 (`SPEC.md`)
- Prompt: Asked the assistant, in the test-writing session, to assess the review comments and then to revise the tests, `docs/traceability.md`, and the component prompts for the comments the team accepted. The fixes were generated in two new sessions; see `prompts/2026-10-18-module-bodies.md` (A5 — Fix for session ownership; A6 — Fix for disposition field)
- Reviewed by: Katherine Xing, who also ran both fix generations. Both fixes are minimal diffs; the 1.4.3, 1.4.5, and 1.4.6 tests pass, and the fix sessions did not modify any test
- Accepted: (1) A5 did not enforce SR-03's own-session rule, because session-ownership checks had been placed out of scope in the first A5 prompt. The 1.4.5 test now covers same-session access, cross-session access, and missing session information, and the matrix records an `own_session` or `any` scope for each operation; A5 was fixed to match. (2) A6 returned its expired records as `deleted` although nothing is deleted from storage in this increment. The field is now `authorized_for_deletion`, the 1.4.6 test adds the 23 h 59 min and 24 h 1 min boundaries, and `docs/traceability.md` states that SR-04 is only partly satisfied until the storage adapter in Chapter 8. (3) The 1.4.4 test rejected any explanation containing "reserved" or "guaranteed", which would fail a compliant disclaimer such as "Spaces are not reserved or guaranteed." The test now requires an `advisory_notice` and rejects affirmative claims such as "is reserved" and "guaranteed space". This corrects the verification criterion; A4 is not yet implemented, so no implementation was accommodated. (4) `docs/traceability.md` claimed that 1.4 was verified through the acceptance suite, which does not yet call the system; it now states that verification of 1.4 is planned and not complete, and that A1.1–A1.4 are allocated to A1 with implementation pending
- Rejected or removed: Implementing an in-memory personal-record store so that A6 performs a physical deletion now, because the model has no storage mechanism yet and storage arrives with the Chapter 8 adapter. Identity establishment in A5, because it remains an open decision in the report
- Assistant assumptions: The `own_session` and `any` scope values in the role-permission matrix and the `caller_session_id` and `record_session_id` request fields were chosen by the assistant; they are to be confirmed in the Chapter 7 interface contract

## 2026-10-24 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: Requirements 1.4.1 and 1.4.3; SR-10 and SR-13 (`SPEC.md`); the existing `tests/test_functional_requirements.py`; Lab 6–7 verification work
- Prompt: Asked the assistant, without changing any module body, to create branch `lab6-lab7-architecture-definition`, add a permit-not-allowed case to the 1.4.1 test, add a new SR-13 tie-break test for 1.4.3, run the functional-requirement suite, record the actual results in `docs/verification/ch7-actual-results.md`, and commit and push
- Changed: (1) `test_FR_1_4_1_prepares_eligible_parking_information` adds LOT-4, whose confirmed rule does not allow the declared permit, using a local walking list so the shared `WALKING` constant is unchanged; the existing assertion that only LOT-1 and LOT-3 are eligible still applies, so LOT-4 must be excluded (SR-10). (2) New `test_FR_1_4_3_tie_breaks_follow_sr13`: equal scores of 0.5 are ordered by ascending walking time, and equal scores and walking times by area ID (SR-13). (3) New `docs/verification/ch7-actual-results.md` recording the run. No existing assertion and no module body was changed
- Verification run: `python -m pytest tests/test_functional_requirements.py -v` on 2026-10-24 with Python 3.13.9 and pytest 8.4.2 — 3 failed, 4 passed. 1.4.3 (both tests), 1.4.5, and 1.4.6 pass; 1.4.1, 1.4.2, and 1.4.4 fail with `NotImplementedError` because those bodies are not yet implemented
- Reviewed by: Katherine Xing
- Assistant assumptions: None. Test data and expected orders were specified in the prompt; the assistant checked by hand that both Case 1 areas score 0.5 under the SR-13 formula

## 2026-10-25 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: `docs/route-table.md` (this increment's audit); `B2_Trace_Mapping.xlsx` and report Table 1 for the use-case mapping; Innoslate V2 model (`Team26_V2_Model.xml`)
- Prompt: see `prompts/2026-10-24-entry-point-enumeration.md`. The assistant enumerated the entry points and their callers read-only. In a follow-up, it was asked to compare that list with the report and to transcribe the team's existing B2/Table 1 mapping into `docs/route-table.md`
- Reviewed by: Katherine Xing. Accepted the enumeration as read: five entry points (`app.main` and the four `cornell_driver_interface` functions), all tracing to UC.1; no orphan entry points
- Changed: The audit found one orphan payload. `find_suitable_parking()` returned an `"inputs"` field carrying the raw X.C.2–X.C.4 responses to the driver; it arrived in commit `a38e516` and traces to no model output. The team removed it and kept `"data_mode"` (SPEC requires simulated data to be labeled). In its place the team added `"trip_summary"` with the six confirmed fields, justified by flow 9.13 (Normalized Trip Requirements into A4). This is a team decision, not an assistant proposal
- Recorded: SYS.2 Delete Expired Personal Records and SYS.1 Authorize Protected Data Operations have no entry point and are planned for Chapter 8. UC.1.15, UC.1.22 and UC.1.23 are driver-only actions and need none. `python -m pytest` is classified as a verification harness rather than a product entry point; the team confirmed this classification
- P2 resolved by the team: the assistant flagged that the report's statement that UC.1 triggers no protected-data operation conflicted with SR-03/SR-04 trip-record retention. The team chose decision (b): storing the confirmed trip record at UC.1.3 is a protected operation, but it stays outside the selected UC.1 trace and is realized by SYS.1/SYS.2 in Chapter 8. Report §2.1.1 and the SYS.1 row of `docs/route-table.md` were updated to match
- Assistant assumptions: None in the mapping, which was transcribed from the team's B2 workbook

## 2026-10-25 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: Internal flows I-01–I-12 (`B2_Trace_Mapping.xlsx`, sheet 02 I-O Coverage; Innoslate V2); the `SPEC.md` Data Contract; `contracts/api-v1.yaml`
- Prompt: see `prompts/2026-10-25-interface-contract.md`
- Reviewed by: Katherine Xing. The team chose the contract structure (one operation per receiving function), the lot-level Validated Parking Data shape, the A5 session fields, `trip_summary`, and generated stubs with a conformance test, before the contract was written
- Changed:
  - New `contracts/api-v1.yaml`
  - New `contracts/generate_stubs.py` and `contracts/generated/`
  - New `tests/test_interface_contract.py`
  - `pyyaml` added to `requirements.txt`
  - New ADR-0003
- Divergences the stubs exposed:
  - (1) The A1 signature took `trip_information_and_parking_request: str | dict`. The contract defines an object, so the type was narrowed to `dict`.
  - (2) The 1.4.4 test passed Ranked Parking Options as `{lot_id}` only. That violates I-08, so the fixture now carries the four required fields. No assertion changed. Katherine Xing reviewed and approved this test change.
  - A2–A6 already matched their stubs.
- Not resolved, recorded in ADR-0003:
  - `smart_parking_service` is not yet behind the contract.
  - The X.C.2 stubs return lot-level data rather than SPEC sensor events (Chapter 8 adapters).
  - SR-15 eligibility basis has no field in I-05.
  - Eight of the twelve flow entities have empty descriptions in the V2 model.
- Verification run:
  - `python -m pytest tests/test_functional_requirements.py tests/test_interface_contract.py -q`: 3 failed, 19 passed. The three failures are the unchanged `NotImplementedError` cases for 1.4.1, 1.4.2 and 1.4.4.
  - `python app.py` runs.
- Assistant assumptions: The control shapes (for example `stale_after_seconds` and `weights`) were taken from the existing accepted test fixtures. They are recorded in the contract as v1 and should be checked against the model's control entities

## 2026-10-28 — Katherine Xing — Claude Code (Opus 5.5)

- Built from:
  - Lab Manual §8.5
  - `SPEC.md`: Data Contract sections 1, 3 and 5, and the Model Response Contract
  - `contracts/api-v1.yaml`: `SensorEvent`, `UpdatedParkingAvailability`
  - ADR-0002, ADR-0003
  - The team's asset naming for C.1–C.6 and C.1.1–C.1.4 (Ch8–9 task sheet)
- Prompt: see `prompts/2026-10-28-data-and-model-adapters.md`. The adapter
  specification `docs/model-adapter.md` was written before the adapter was
  generated.
- Changed:
  - New `docs/deployment.md` (K1).
  - `parking_availability_data_sources/` is now a seeded simulated X.C.2
    feed of space-level sensor events.
  - New `parking_data_access/`, with `schema.sql` and the data access
    component (K3).
  - `language_model/` is now the Qwen3 adapter with the schema-violation
    fallback (K4).
  - `smart_parking_service` replaces the two stubs, one at a time.
  - `app.py` falls back to the six-field form.
  - New `tests/test_data_access.py` and `tests/test_model_adapter.py`.
  - `docs/walking-skeleton.md`, `docs/traceability.md`, `README.md` and the
    ADR-0003 divergence note are updated.
  - Drafts prepared for K6, with no generation yet:
    `prompts/2026-10-31-c14-eligibility-filter.md` and
    `docs/deviation-log.md`.
- Verification run: `python -m pytest tests/ -q` on 2026-10-28 with Python
  3.13.9 and pytest 8.4.2 gave 22 failed and 65 passed.
  - The 22 failures are the same pre-existing red tests: 19 acceptance
    placeholders, plus 1.4.1, 1.4.2 and 1.4.4 with `NotImplementedError`.
  - All 46 new tests pass, and the 19 tests that passed before still pass.
  - `python app.py` runs end to end.
- Live model call, 2026-10-30: Ollama 0.40.13 with `qwen3:4b` (Q4_K_M,
  digest `359d7dd4…`), served on `127.0.0.1:11434`. Done-When item 2 is
  met: the model returned a response through the adapter, and the
  schema-violation path fired on real output.
  - Three simulated messages were sent with `submitted_at`
    2026-10-30T15:00-04:00. Each call took 3.6–8.2 s (the first call
    loads the model) and produced about 120 output tokens, with
    `done_reason` `stop`.
  - All three replies were rejected as `invalid_fields`, and the driver
    got the six-field form:
    - A full request ("3:30 pm … leaving at 6 pm") came back with
      `departure_time` `2026-10-30T1:00:00-04:00`, which is not a valid
      timestamp.
    - A request with only the destination ("parking near Gates Hall
      soon") came back as `complete`. The model invented the vehicle,
      eligibility and access values, and set departure equal to arrival.
      The adapter caught this only because departure was not after
      arrival.
    - A full request ("3:45pm and stay two hours") came back with the
      offset `-04:0:00`.
  - `python app.py` ran end to end through the form fallback in 4.1 s.
  - Not in the repository: a scratch trial (not committed) asked the model
    for nullable fields, enum-limited values and `HH:MM` times, with the
    adapter assembling the contract object. That trial got four of four
    messages right, including `null` for the unstated fields. This changes
    what the model itself returns, which SPEC.md's Model Response Contract
    fixes. It waits for a team decision and is not applied.
    A second scratch trial on four harder messages found that design's own
    problems:
    - The enum forced the unsupported "Statler Hall" onto "Gates Hall".
    - The enum forced a "faculty CU permit" onto `permit_O`.
    - "Arriving 3:20" became `03:20`.
    - An explicit "no accessibility needs" became `null`.
  - `scripts/live_model_check.py` was added, so the team can rerun these
    checks. Its first run, on 2026-10-30 with the current adapter, gave
    2 of 8 messages as expected. Two wrong values passed the adapter as
    `complete`:
    - An unstated `access_needs` became `false`, against the Model
      Response Contract.
    - A "faculty CU permit" became `permit_O`.
- Reviewed by: pending. Xichen Wang reviews against the §8.5 Done When list
  in the PR (K5).
- Assistant assumptions, to be confirmed by the team:
  - (1) Simulator values: lot capacities, coordinates, the hourly occupancy
    profile, the 1% unknown rate and seed 5151. All are labeled simulated.
  - (2) The provisional supported destinations, vehicle categories and
    eligibility values in `smart_parking_service.PROVISIONAL_SUPPORTED_VALUES`.
    Deferred item 3 is still open.
  - (3) The adapter parameters: 60 s timeout, 512 output tokens, 4096
    context and a 2000-character input limit.
  - (4) A model that cannot be reached is treated like a schema violation,
    so the driver falls back to the six-field form. SPEC's Fallback
    paragraph names only malformed, unsupported or invalid output.
  - (5) Extra keys in a model reply are a violation, because the contract
    says "exactly one of the following JSON objects".
  - (6) The adapter applies the Data Contract §5 arrival-window and
    departure checks to `complete` replies.
  - (7) The database is in memory and holds no rule table, modeling table
    or trip records yet.
  - (8) The orchestration still uses the hard-coded ranking placeholder.
    It fetches availability through the component but does not use it to
    rank. Ranking waits for the A1, A2 and A4 bodies (ADR-0003).

## 2026-11-01 — Katherine Xing — Claude Code (Opus 5.5)

- Built from:
  - The 2026-10-30 live run recorded in the 2026-10-28 entry.
  - The team's decisions on the Model Response Contract, already entered
    in `SPEC.md` by Katherine Xing:
    - The interpretation step, meaning the model and its adapter, returns
      the contract object.
    - An unstated `access_needs` is `false`.
    - Other unstated or unsupported values are listed in `missing_fields`.
    - The Fallback paragraph covers only replies without the six fields.
  - Katherine Xing's further decisions in this session:
    - The model writes `HH:MM` times, and the adapter adds the date and
      offset.
    - A time with no am/pm is read as 24-hour.
    - The reply schema has no enum.
    - The live check keeps four ordinary and two non-standard messages.
- Prompt: Asked the assistant to implement those decisions in the C.1.1
  adapter, its tests, `docs/model-adapter.md` and the live check.
- Output:
  - `language_model/__init__.py`: new system prompt, user prompt, nullable
    reply schema, and `assemble_contract`.
  - `tests/test_model_adapter.py` was rewritten.
  - `scripts/live_model_check.py` now has six cases.
  - `docs/model-adapter.md` and the adapter paragraph of
    `docs/deployment.md` were updated.
- Trials before the code change, run in a scratch script and not committed:
  - With supported eligibility meanings in parentheses, the model copied
    the parentheses, and still mapped "faculty CU permit" to `permit_O`.
  - Two changes fixed both: the meanings were moved to their own prompt
    line, and the prompt now says a permit counts only if the driver names
    that exact permit.
- Verification, on 2026-11-01:
  - `python -m pytest tests/ -q` gave 22 failed and 67 passed. The 22 are
    the same pre-existing red tests. All 34 adapter tests pass.
  - `python scripts/live_model_check.py`, with Ollama 0.40.13 and
    `qwen3:4b`, gave 6 of 6 as expected. Each call took 1.6–2.3 s.
    - Both full requests came back complete, with the right times.
    - "Gates Hall soon" listed the four unstated fields.
    - "Statler Hall" listed `destination` as missing.
    - "Faculty CU permit" listed `declared_eligibility` as missing.
- Not verified:
  - Messages outside these six cases. The team chose not to test harder
    phrasings.
  - The confirmation card that shows missing fields, which belongs to A4
    and is not built.
- Reviewed by: pending. Xichen Wang reviews in the K5 PR.
- Open:
  - The 60-minute arrival window is under team review.
  - An `incomplete` result carries only `missing_fields`, so the
    confirmation card cannot pre-fill the values the model did recognize.
    Pre-filling would need the SPEC example for `incomplete` to also carry
    the known values.

## 2026-11-01 — Katherine Xing — Claude Code (Opus 5.5)

- Built from:
  - Bochao Liang's review comments to Katherine Xing.
    - Mark the ingestion checks as defensive.
    - Define the fields of `UpdatedParkingAvailability`.
  - Katherine Xing's request for a draft §4 rule table, researched online,
    because the data-and-rules owner has left the team.
  - Public Cornell Transportation pages, retrieved 2026-11-01:
    - https://fcs.cornell.edu/node/2296: night and weekend open parking.
      The page is undated.
    - https://fcs.cornell.edu/sites/default/files/2026-08/ParkmobileMap26.pdf:
      the August 2026 hourly-parking map.
- Output:
  - `docs/deployment.md`: the ingestion checks are described as defensive.
    A1.3 still owns validity and freshness, and no ADR is needed.
  - `contracts/api-v1.yaml`: `UpdatedParkingAvailability` now has the
    `lot_id` and `observations` fields, matching the data access component.
    The generated stubs did not change.
  - New `cornell_transportation_and_parking_services/parking_rules_draft.json`
    with nine draft rules, R-01 to R-09, and a `get_rule_table()` loader.
  - New `tests/test_rule_table.py`, which checks structure only.
- What is sourced and what is assumed:
  - Sourced:
    - Weekday enforcement 07:30–17:00.
    - Hoy Road Garage is open parking on weekday evenings and weekends
      (R-03, R-04).
    - Accessible spaces are restricted at all times (R-07, R-08).
  - Assumed and labeled in each rule's `source`:
    - Which permit each zone accepts (R-01, R-05, R-06).
    - That LOT-1 is Hoy Road Garage.
    - The event-day closure (R-09).
  - Not found online: whether O permits are valid at Hoy Road Garage or
    Peterson Lot. A contractor page groups Hoy G with a "Mid" permit
    group, not O.
- Verification: `python -m pytest tests/ -q` on 2026-11-01 gave 22 failed
  and 78 passed. The 22 are the same pre-existing red tests.
- Reviewed by: pending. The rules need team confirmation before evaluation
  (SR-10). Responsibility for data and rules needs a new owner under SR-07.
- Open: the mapping from lot IDs to real lot names. "Sage Garage" in the
  October slides does not appear in Cornell's sources. Peterson Lot is
  listed as an hourly pay lot, which does not match the slides' O-permit
  use.

## 2026-11-01 — Katherine Xing — Claude Code (Opus 5.5)

- Built from:
  - Katherine Xing's approval of the lot mapping:
    - LOT-1 Hoy Road Garage: 150 O-permit / 40 visitor / 10 accessible.
    - LOT-2 Peterson Lot: 0 / 110 / 10.
    - LOT-3 Campus Road O Area: 140 / 0 / 10.
  - The Innoslate export `5151 Team Project- Nov1.xml`. Its contents:
    - The C.1 Component Specification.
    - DO-04.
    - The A1.4 ICOM relationships, NFR.4 and SR-10.
- Output:
  - The simulator inventory was renamed and resized, to 470 spaces.
  - The walking-time and rule stubs and the placeholder ranking now use
    LOT-3 instead of LOT-2 as the O-permit backup.
  - The draft rule table moved to version `draft-2026-11-01b`:
    - Lot wildcards were replaced with explicit lots, so an O-permit rule
      no longer reaches Peterson Lot, which has no O zone.
    - The rules that disallow placard holders were dropped.
    - The simulated closure moved to Wednesday 2026-11-04, LOT-3.
  - `prompts/2026-10-31-c14-eligibility-filter.md` is filled from the
    export and is ready for team review. It has not been sent or generated
    yet.
- Verification: `python -m pytest tests/ -q` on 2026-11-01 gave 22 failed
  and 81 passed. The 22 are the same pre-existing red tests.
- Inconsistencies found and left for the team's Innoslate review meeting:
  - "1.4.4" is used for two different requirements: C.1's "Determine
    Eligible Parking Areas" and the system-level "Present Parking
    Recommendations and Status".
  - Contract E-12 `ParkingPolicyConstraints` has only four rule fields,
    while SPEC §4 has the full set.
  - The C.1 specification has no number for its response-time budget
    (2.3.1).
- Reviewed by: pending.

## 2026-11-01 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: `prompts/2026-10-31-c14-eligibility-filter.md`, whose four
  decisions Katherine Xing confirmed on 2026-11-01.
  - Decision 1 matches her reading. A lot must accept the declared permit,
    and it must also have accessible spaces the trip may use.
- Prompt: the component prompt, sent once (Lab Manual §9.4, task K6).
- Output, generated once and not modified since:
  - `prepare_eligible_parking_information/determine_eligible_parking_areas.py`
  - `tests/test_eligibility_filter.py`
- Verification on 2026-11-01:
  - The ten DO-04 scenarios: 10 of 10 passed.
  - The full suite: 22 failed and 91 passed. The 22 are the same
    pre-existing red tests.
- Deviations: see `docs/deviation-log.md`. It lists six specification
  defects, all at the input boundary, and no assistant errors or
  unrequested additions. The most serious is row 2: a trip whose departure
  is not after its arrival returns every candidate.
- Reviewed by: pending. Xichen Wang reviews in the K5 PR. The reviewer must
  not be the person who ran the generation.
- Not done: A1 does not call the module yet. The deviation-log corrections
  wait for the team to promote the requirements.

## 2026-11-01 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: `docs/deviation-log.md` rows 1–6, with Katherine Xing's
  dispositions from 2026-11-01.
  - Rows 2, 3 and 5 are promoted to requirements and corrected in the code.
  - Rows 4 and 6 are accepted as they are.
  - Row 1 is replaced by a real non-matching-permit test.
  - Permit holders may also use pay/visitor areas, by Katherine Xing's
    decision.
- Output:
  - `determine_eligible_parking_areas.py` now returns `[]` in two cases:
    when departure is not after arrival, and when `access_needs` is not a
    boolean. A rule window that starts and ends at the same time is now
    unreadable.
  - `tests/test_eligibility_filter.py` was updated; it has 15 tests.
  - The rule table moved to `draft-2026-11-01c`. R-07 and R-08 now use
    `eligibility_class` `*`.
  - The `SPEC.md` §4 window definition was updated.
- Verification on 2026-11-01: `python -m pytest tests/ -q` gave 22 failed
  and 96 passed. The 22 are the same pre-existing red tests.
- Innoslate changes, made by Katherine Xing: the DO-04 sentence for rows 2
  and 3, and the Parking Policy Constraints sentence for row 5.
- Reviewed by: pending. Xichen Wang reviews in the K5 PR.

## 2026-11-01 — Katherine Xing — Claude Code (Opus 5.5)

- Built from: a team member's review of the K5 PR, five points. Katherine
  Xing asked the assistant to check them.
- Checked against the Lab Manual and the code:
  - **Point 1 is confirmed.** Lab Manual p.21 says "Never let one
    generation write both the code and its test". The K6 prompt asked for
    both. This is recorded as deviation-log row 7, a process deviation. It
    stays open until a member who did not run the generation writes
    independent tests.
  - **Point 2 is confirmed.** Lab Manual p.20 says the reviewer "must be a
    team member who did not run the generation". Katherine Xing ran it, so
    "Reviewed by" stays open for another member.
  - **Point 3 was confirmed as an adapter defect, introduced on
    2026-11-01.** `assemble_contract` turned any non-boolean `access_needs`
    into `false`, and a test asserted that behavior. It is fixed:
    - Only `null` defaults to `false`.
    - Any other value is listed as missing.
    - The test now asserts the new behavior, and `docs/model-adapter.md`
      is updated.
  - **Point 4 is valid.** The CI signal is mixed with the 22 intended red
    tests. The CI change is left to the testing/CI owner, Xichen Wang
    (SR-07).
  - **Point 5 is confirmed.** `docs/deviation-log.md` now has a single
    final status and a "Requirement back-fill" table listing each element,
    the text added, the date and the person. The post-edit Innoslate
    export is still to be attached.
- Verification on 2026-11-01: `python -m pytest tests/ -q` gave 22 failed
  and 99 passed. The 22 are the same pre-existing red tests.

## 2026-11-01 — Katherine Xing — ChatGPT web, separate session (model: GPT-6.1 Sol)

- Built from: `prompts/2026-11-01-c14-independent-tests.md`. Only the part
  below its paste marker was used: the requirements, interface, decisions
  and rule table. The C.1.4 code and its first tests were not given to the
  session.
- Prompt: write requirement-based pytest tests for
  `determine_eligible_parking_areas` without seeing it. This remediates the
  process deviation in deviation-log row 7 (Lab Manual p.21).
- Output: `tests/test_eligibility_filter_independent.py`, 16 test
  functions.
- Verification on 2026-11-01, run by Claude Code in Katherine Xing's
  session:
  - The independent tests: 73 passed and 0 failed against commit `db85650`
    plus this file.
  - The full suite: 22 failed and 172 passed. The 22 are the same
    pre-existing red tests.
- Reviewed by: pending. A team member who did not run either generation
  must review it.
