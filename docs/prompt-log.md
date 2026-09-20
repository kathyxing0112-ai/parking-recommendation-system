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
- Accepted: Python 3.12, a local Python virtual environment, PyCharm and Visual Studio Code, and evaluation of Ollama with Qwen3 4B as the initial candidate
- Rejected or removed: Immediate Docker configuration, paid hosted API integration, larger local models, and untested Python dependencies
- Assistant assumptions: The LLM will initially explain recommendations rather than perform the core parking ranking logic, and the initial prototype will be developed and demonstrated locally