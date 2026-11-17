# UC.1 Scenario 1: 50 runs through HTTP

Measured 2026-11-15T19:57:52+00:00 on Apple M4 (macOS-26.6.2-arm64-arm-64bit-Mach-O), commit 7ffb193.

Paths taken: form_fallback 13, model_confirmed 37

### All runs

| Stage | Participant | n | min ms | median ms | mean ms | p95 ms | max ms | std ms |
|---|---|---|---|---|---|---|---|---|
| UC1.interpret_request | X.C.1 -> C.0 | 50 | 1996.60 | 2118.80 | 2165.76 | 2318.86 | 2982.97 | 174.31 |
| C.1.1.model_call | C.1.1 -> Ollama qwen3:4b | 50 | 1996.51 | 2118.73 | 2165.67 | 2318.74 | 2982.84 | 174.30 |
| C.1.1.contract_check | C.1.1 | 50 | 0.04 | 0.05 | 0.05 | 0.08 | 0.10 | 0.01 |
| UC1.find_parking | X.C.1 -> C.0 | 50 | 18.45 | 20.18 | 20.21 | 21.36 | 25.02 | 0.96 |
| X.C.2.availability | C.0 -> X.C.2 (SQLite data store) | 50 | 16.12 | 17.77 | 17.82 | 19.18 | 22.51 | 0.96 |
| X.C.3.context | C.0 -> X.C.3 | 50 | 0.38 | 0.52 | 0.55 | 0.74 | 0.98 | 0.13 |
| X.C.4.rules | C.0 -> X.C.4 | 50 | 0.12 | 0.16 | 0.16 | 0.22 | 0.25 | 0.03 |
| C.1.prepare | C.1 | 50 | 1.38 | 1.49 | 1.50 | 1.64 | 1.72 | 0.07 |
| C.1.1.confirm | C.1.1 | 50 | 0.02 | 0.03 | 0.03 | 0.07 | 0.08 | 0.01 |
| C.1.2.requests | C.1.2 | 50 | 0.00 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 |
| C.1.3.validate | C.1.3 | 50 | 1.11 | 1.23 | 1.24 | 1.32 | 1.44 | 0.05 |
| C.1.4.eligibility | C.1.4 | 50 | 0.17 | 0.20 | 0.21 | 0.24 | 0.53 | 0.05 |
| C.3.rank | C.3 | 50 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 |
| C.0.assemble_result | C.0 (stands in for C.4) | 50 | 0.01 | 0.02 | 0.02 | 0.03 | 0.04 | 0.00 |
| HTTP.interpret_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 50 | 1997.23 | 2119.38 | 2166.44 | 2319.61 | 2983.76 | 174.32 |
| HTTP.confirm_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 50 | 19.28 | 21.18 | 21.12 | 22.22 | 26.02 | 1.00 |
| UC1.system_total | sum of the top-level stages | 50 | 2017.66 | 2141.22 | 2187.56 | 2340.78 | 3005.05 | 174.40 |

### Warm model only (excluding run 1)

| Stage | Participant | n | min ms | median ms | mean ms | p95 ms | max ms | std ms |
|---|---|---|---|---|---|---|---|---|
| UC1.interpret_request | X.C.1 -> C.0 | 49 | 1996.60 | 2118.86 | 2166.80 | 2318.86 | 2982.97 | 175.95 |
| C.1.1.model_call | C.1.1 -> Ollama qwen3:4b | 49 | 1996.51 | 2118.79 | 2166.71 | 2318.74 | 2982.84 | 175.95 |
| C.1.1.contract_check | C.1.1 | 49 | 0.04 | 0.05 | 0.05 | 0.08 | 0.10 | 0.01 |
| UC1.find_parking | X.C.1 -> C.0 | 49 | 18.45 | 20.18 | 20.11 | 21.18 | 21.61 | 0.67 |
| X.C.2.availability | C.0 -> X.C.2 (SQLite data store) | 49 | 16.12 | 17.76 | 17.73 | 18.76 | 19.28 | 0.69 |
| X.C.3.context | C.0 -> X.C.3 | 49 | 0.38 | 0.52 | 0.55 | 0.74 | 0.98 | 0.13 |
| X.C.4.rules | C.0 -> X.C.4 | 49 | 0.12 | 0.16 | 0.16 | 0.22 | 0.25 | 0.03 |
| C.1.prepare | C.1 | 49 | 1.38 | 1.49 | 1.50 | 1.64 | 1.72 | 0.07 |
| C.1.1.confirm | C.1.1 | 49 | 0.02 | 0.03 | 0.03 | 0.07 | 0.08 | 0.01 |
| C.1.2.requests | C.1.2 | 49 | 0.00 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 |
| C.1.3.validate | C.1.3 | 49 | 1.14 | 1.23 | 1.24 | 1.32 | 1.44 | 0.05 |
| C.1.4.eligibility | C.1.4 | 49 | 0.17 | 0.20 | 0.20 | 0.24 | 0.33 | 0.02 |
| C.3.rank | C.3 | 49 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 |
| C.0.assemble_result | C.0 (stands in for C.4) | 49 | 0.01 | 0.02 | 0.02 | 0.03 | 0.04 | 0.00 |
| HTTP.interpret_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 49 | 1997.23 | 2119.48 | 2167.48 | 2319.61 | 2983.76 | 175.97 |
| HTTP.confirm_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 49 | 19.28 | 21.16 | 21.02 | 22.00 | 22.58 | 0.71 |
| UC1.system_total | sum of the top-level stages | 49 | 2017.66 | 2140.93 | 2188.50 | 2340.78 | 3005.05 | 176.07 |
