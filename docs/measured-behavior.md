# Measured Behavior (Lab Manual §10.4)

This file records how the product is instrumented and how the measurement runs
are made. The comparison with the Innoslate simulation, the explanation of the
divergence, and the decision come later (K3, K4).

## Instrumentation

`stage_timing/` records entry and exit (`time.perf_counter_ns`) at each
participant boundary on the UC.1 path. It is off unless a caller starts it,
so the product and CI behave as before. It records stage names and times only,
never a message, trip field or model output (SR-04).
Tests: `tests/test_stage_timing.py`.

| Stage | Participant | Covers | Innoslate action (S1 #308650 / S2 #308686, frozen V1) |
|---|---|---|---|
| `UC1.interpret_request` | X.C.1 → C.0 | Message submitted until the interpreted request returns (UC.1.1–UC.1.2) | Window C (s1.2–s1.4); s1.2 is this stage minus the next two |
| `C.1.1.model_call` | C.1.1 → Ollama `qwen3:4b` | One chat request to the local model | s1.3 Execute Language Model Inference (C.1.1.1) |
| `C.1.1.contract_check` | C.1.1 | Reply checked against the Model Response Contract | s1.4 Generate Structured Parking Criteria |
| `UC1.find_parking` | X.C.1 → C.0 | Confirmed request until ranked options return (UC.1.3–UC.1.14) | Server part of window D |
| `X.C.2.availability` | C.0 → X.C.2 (SQLite) | Simulated availability through the data access component | s1.6 + s1.7 / s2.2 + s2.3 (one call in the code) |
| `X.C.3.context` | C.0 → X.C.3 | Contextual information (walking times) | Not modeled |
| `X.C.4.rules` | C.0 → X.C.4 | Parking rules and closures | s1.9 / s2.5 Provide Applicable Parking Rules |
| `C.1.prepare` | C.1 | A1, all four modules | Holds s1.8 and s1.10 (with the two unmodeled checks) |
| `C.1.1.confirm` | C.1.1 | A1.1 checks the confirmed request | Not modeled |
| `C.1.2.requests` | C.1.2 | A1.2 builds the data requests | Not modeled (request objects only; the read is s1.6/s1.7) |
| `C.1.3.validate` | C.1.3 | A1.3 validates parking and context data | s1.8 / s2.4 Validate Parking Records |
| `C.1.4.eligibility` | C.1.4 | A1.4 determines eligible areas | s1.10 / s2.6 Filter Eligible Parking Options |
| `C.3.rank` | C.3 | A3 ranks the options | s1.11 / s2.7 Rank Parking Recommendations |
| `C.0.assemble_result` | C.0 (stands in for C.4) | Driver-facing result; A4 has no body yet | s1.12 / s2.8 Deliver, together with the HTTP reply |
| `HTTP.interpret_round_trip` | Browser → `web_app` | POST /api/interpret, client side (`--http`) | Window C seen by the client |
| `HTTP.confirm_round_trip` | Browser → `web_app` | POST /api/confirm, client side (`--http`) | Window D (SR-13 window up to the reply; rendering not included) |

Two things about these boundaries:
- In the code, `smart_parking_service` reads the three external sources before
  A1 runs, and A1.2 only builds the request objects. So the external reads
  are their own stages (`X.C.*`), and `C.1.2.requests` is close to zero.
- C.2 has no body yet, so there is no C.2 stage. A3 uses its walking-time
  fallback.

The time a driver spends reading and confirming is not measured. Only system
time is.

## Measurement runs

Request set: `measurements/uc1_requests.json`, 40 synthetic requests made by
`python scripts/make_uc1_requests.py` (seed 5151). Each has a message
template for Scenario 1 and the same six fields for the form.

```
python scripts/measure_uc1.py --scenario 1 --runs 50 --cold-first
python scripts/measure_uc1.py --scenario 2 --runs 50
```

Raw output goes to `measurements/runs/`, which git ignores. Per the team rule,
measured numbers stay local until the simulation parameters (X2) are
committed. Then the chosen runs are copied into the repository.

On 2026-11-10 an evening trial sent 24 of 30 Scenario 1 runs to the form:
the model writes clock times only, and the adapter listed any time past
midnight as missing. The adapter now reads such a time as the next day
(docs/model-adapter.md, 2026-11-11), so runs can be made at any hour. Runs
made before that change are not used.

## Formal runs, 2026-11-15

Apple M4, `qwen3:4b` through Ollama, both scenarios through `web_app`'s POST
endpoints (`--http`), 50 runs each, Scenario 1 with the model unloaded first.
The simulation parameters (X2 V0.3) were frozen and the Innoslate runs made on
2026-11-14, before these runs.

| Run | Commit | Product | Use |
|---|---|---|---|
| `s2-http/` | `11c03c8` | Scenario 2 (no model) | Comparison |
| `s1-http/` | `11c03c8` | Scenario 1 before the warm-up change: run 1 was a cold start (3,986 ms inference) | Evidence for the decision below |
| `s1-http-warm/` | `7ffb193` | Scenario 1 after the warm-up change (model loaded at start, `keep_alive` 30 min): run 1 was 2,141 ms in total | Comparison (current product) |

- Raw runs: `docs/measurements/2026-11-15/`
- Simulation results: `docs/measurements/simulation/HW6_B4_Simulation_Results.xlsx` (B4)
- Comparison: `docs/measurements/2026-11-15/comparison.md`, `comparison.csv`,
  `fig_stage_comparison.png`, `fig_windows.png`, made by
  `python scripts/compare_sim_measured.py` (command in its docstring)

The explanation of the divergence and the decision are written by the team
(report §4.4), not generated.

## Decision (Lab Manual §10.4.2), 2026-11-15

Recorded from report §4.4. **Simulation parameters: unchanged (X2 V0.3).
Architecture: the product keeps the language model warm.**

| Divergence | What was checked | Decision |
|---|---|---|
| Downstream stages: X2 overestimates window D about 12–25× (244 ms simulated; 21.1 ms S1 and 9.6 ms S2 measured) | Every implemented downstream stage against its X2 value (`comparison.md`). X2 Table 1 marks these inputs as preliminary estimates | Keep the X2 downstream values. They make the simulation conservative for SR-13: the measured `POST /api/confirm` round trip was at most 26.0 ms (S1) and 29.9 ms (S2) against 5 s, with two options in every run. The simulated 244 ms describes the model only and is not the system's response time |
| Inference: mean close (2.17 s measured, 2.4 s assumed), spread under a third of the assumed one, right-skewed; first request after an unload took 3.99 s | First request with no warm-up (3.99 s), with a bare model load (about 3.5 s), and with one full warm-up request (2.11 s) | Change the implementation, not the simulation: one full warm-up request when `web_app` starts and `keep_alive` of 30 minutes (commits `436c65f`, `7ffb193`; `docs/model-adapter.md`). Cost: about 2.5 GB of memory held for up to 30 minutes after the last request. S1 was measured again after the change (`s1-http-warm`). The X2 inference distribution is kept: its mean is within about 10%, inference is outside the SR-13 window, and the scenario comparison does not change |
| S1 downstream 2–4× slower than S2 (X.C.2 read 17.8 ms against 8.2 ms) with the same code | Three experiments on one build (`request-spacing/`): alternating conditions; back-to-back requests with the model loaded and unloaded; idle gaps of 0–2 s with the model unloaded | Request spacing alone reproduces the slowdown (back-to-back 8.5–9.2 ms; after a 0.1–2.0 s gap 21.1–21.9 ms, with no model involved). One set of downstream parameters stays for both scenarios. The S2 figure reflects back-to-back test runs; real requests are spaced like S1's. The machine-level cause was not verified |

Request-spacing experiments (medians of `POST /api/confirm`, ms):

| Experiment | Condition | Round trip | X.C.2 read | Validation |
|---|---|---|---|---|
| `idle_experiment.py`, 30 rounds alternating | confirm right after the previous round | 18.9 | 16.8 | 0.77 |
| | 2.1 s idle sleep, then confirm (no model) | 22.4 | 18.5 | 1.15 |
| | one Qwen3 call, then confirm (as in S1) | 20.9 | 17.5 | 1.22 |
| `loaded_experiment.py`, 30 back-to-back each | model unloaded | 8.5 | 7.5 | 0.44 |
| | model loaded | 9.2 | 8.2 | 0.45 |
| | model unloaded again | 9.2 | 8.2 | 0.45 |
| `gap_experiment.py`, model unloaded, 20 each, alternating | 0 s (after the previous round's 2 s gap) | 18.1 | 16.0 | 0.72 |
| | 0.1 s | 21.1 | 18.1 | 0.89 |
| | 0.5 s | 21.9 | 18.3 | 1.06 |
| | 2.0 s | 21.9 | 18.2 | 1.22 |

Each script runs from the repository root, for example
`python docs/measurements/2026-11-15/request-spacing/gap_experiment.py 20`.
Only `idle_experiment.py` writes a CSV (`idle_experiment.csv`); the other two
print their medians, recorded above. They ran on 2026-11-15 at commit `512ce9e`,
before the warm-up change, which does not touch the downstream path.
