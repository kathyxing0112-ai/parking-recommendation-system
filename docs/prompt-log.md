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
