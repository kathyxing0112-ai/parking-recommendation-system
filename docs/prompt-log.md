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