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
