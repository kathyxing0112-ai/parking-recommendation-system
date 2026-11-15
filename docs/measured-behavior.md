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

| Stage | Participant | Covers | Innoslate action (s1.x / s2.x) |
|---|---|---|---|
| `UC1.interpret_request` | X.C.1 → C.0 | Message submitted until the interpreted request returns (UC.1.1–UC.1.2) | _to fill from B3_ |
| `C.1.1.model_call` | C.1.1 → Ollama `qwen3:4b` | One chat request to the local model | _to fill_ |
| `C.1.1.contract_check` | C.1.1 | Reply checked against the Model Response Contract | _to fill_ |
| `UC1.find_parking` | X.C.1 → C.0 | Confirmed request until ranked options return (UC.1.3–UC.1.14) | _to fill_ |
| `X.C.2.availability` | C.0 → X.C.2 (SQLite) | Simulated availability through the data access component | _to fill_ |
| `X.C.3.context` | C.0 → X.C.3 | Contextual information (walking times) | _to fill_ |
| `X.C.4.rules` | C.0 → X.C.4 | Parking rules and closures | _to fill_ |
| `C.1.prepare` | C.1 | A1, all four modules | _to fill_ |
| `C.1.1.confirm` | C.1.1 | A1.1 checks the confirmed request | _to fill_ |
| `C.1.2.requests` | C.1.2 | A1.2 builds the data requests | _to fill_ |
| `C.1.3.validate` | C.1.3 | A1.3 validates parking and context data | _to fill_ |
| `C.1.4.eligibility` | C.1.4 | A1.4 determines eligible areas | _to fill_ |
| `C.3.rank` | C.3 | A3 ranks the options | _to fill_ |
| `C.0.assemble_result` | C.0 (stands in for C.4) | Driver-facing result; A4 has no body yet | _to fill_ |

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
