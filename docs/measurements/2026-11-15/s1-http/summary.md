# UC.1 Scenario 1: 50 runs through HTTP

Measured 2026-11-15T18:19:59+00:00 on Apple M4 (macOS-26.6.2-arm64-arm-64bit-Mach-O), commit 11c03c8.

Paths taken: form_fallback 20, model_confirmed 30

### All runs

| Stage | Participant | n | min ms | median ms | mean ms | p95 ms | max ms | std ms |
|---|---|---|---|---|---|---|---|---|
| UC1.interpret_request | X.C.1 -> C.0 | 50 | 1987.71 | 2094.07 | 2160.08 | 2662.86 | 3986.54 | 294.93 |
| C.1.1.model_call | C.1.1 -> Ollama qwen3:4b | 50 | 1987.62 | 2093.99 | 2160.00 | 2662.74 | 3986.42 | 294.93 |
| C.1.1.contract_check | C.1.1 | 50 | 0.03 | 0.05 | 0.05 | 0.07 | 0.10 | 0.01 |
| UC1.find_parking | X.C.1 -> C.0 | 50 | 18.38 | 19.25 | 19.46 | 20.20 | 26.01 | 1.08 |
| X.C.2.availability | C.0 -> X.C.2 (SQLite data store) | 50 | 15.63 | 16.74 | 17.00 | 17.82 | 23.21 | 1.08 |
| X.C.3.context | C.0 -> X.C.3 | 50 | 0.38 | 0.57 | 0.57 | 0.74 | 0.92 | 0.11 |
| X.C.4.rules | C.0 -> X.C.4 | 50 | 0.11 | 0.16 | 0.18 | 0.30 | 0.41 | 0.06 |
| C.1.prepare | C.1 | 50 | 1.27 | 1.55 | 1.54 | 1.68 | 1.85 | 0.10 |
| C.1.1.confirm | C.1.1 | 50 | 0.01 | 0.03 | 0.03 | 0.04 | 0.10 | 0.01 |
| C.1.2.requests | C.1.2 | 50 | 0.00 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 |
| C.1.3.validate | C.1.3 | 50 | 1.07 | 1.27 | 1.27 | 1.34 | 1.51 | 0.07 |
| C.1.4.eligibility | C.1.4 | 50 | 0.16 | 0.20 | 0.22 | 0.26 | 0.69 | 0.07 |
| C.3.rank | C.3 | 50 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 |
| C.0.assemble_result | C.0 (stands in for C.4) | 50 | 0.01 | 0.02 | 0.02 | 0.03 | 0.03 | 0.00 |
| HTTP.interpret_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 50 | 1988.38 | 2094.71 | 2160.75 | 2663.62 | 3987.37 | 294.96 |
| HTTP.confirm_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 50 | 19.51 | 20.12 | 20.38 | 21.08 | 27.14 | 1.10 |
| UC1.system_total | sum of the top-level stages | 50 | 2008.96 | 2114.52 | 2181.13 | 2683.74 | 4014.51 | 295.80 |

### Warm model only (excluding run 1)

| Stage | Participant | n | min ms | median ms | mean ms | p95 ms | max ms | std ms |
|---|---|---|---|---|---|---|---|---|
| UC1.interpret_request | X.C.1 -> C.0 | 49 | 1987.71 | 2093.37 | 2122.81 | 2279.85 | 2717.24 | 133.72 |
| C.1.1.model_call | C.1.1 -> Ollama qwen3:4b | 49 | 1987.62 | 2093.29 | 2122.72 | 2279.74 | 2717.15 | 133.71 |
| C.1.1.contract_check | C.1.1 | 49 | 0.03 | 0.05 | 0.05 | 0.07 | 0.10 | 0.01 |
| UC1.find_parking | X.C.1 -> C.0 | 49 | 18.38 | 19.25 | 19.33 | 20.16 | 21.50 | 0.53 |
| X.C.2.availability | C.0 -> X.C.2 (SQLite data store) | 49 | 15.63 | 16.73 | 16.87 | 17.73 | 19.24 | 0.62 |
| X.C.3.context | C.0 -> X.C.3 | 49 | 0.40 | 0.57 | 0.57 | 0.74 | 0.92 | 0.11 |
| X.C.4.rules | C.0 -> X.C.4 | 49 | 0.11 | 0.16 | 0.17 | 0.27 | 0.36 | 0.05 |
| C.1.prepare | C.1 | 49 | 1.27 | 1.54 | 1.54 | 1.68 | 1.79 | 0.09 |
| C.1.1.confirm | C.1.1 | 49 | 0.01 | 0.03 | 0.03 | 0.04 | 0.10 | 0.01 |
| C.1.2.requests | C.1.2 | 49 | 0.00 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 |
| C.1.3.validate | C.1.3 | 49 | 1.07 | 1.27 | 1.27 | 1.34 | 1.51 | 0.07 |
| C.1.4.eligibility | C.1.4 | 49 | 0.16 | 0.20 | 0.21 | 0.25 | 0.29 | 0.02 |
| C.3.rank | C.3 | 49 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 |
| C.0.assemble_result | C.0 (stands in for C.4) | 49 | 0.01 | 0.02 | 0.02 | 0.03 | 0.03 | 0.00 |
| HTTP.interpret_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 49 | 1988.38 | 2094.04 | 2123.48 | 2280.65 | 2717.89 | 133.73 |
| HTTP.confirm_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 49 | 19.51 | 20.11 | 20.24 | 21.07 | 22.46 | 0.52 |
| UC1.system_total | sum of the top-level stages | 49 | 2008.96 | 2113.62 | 2143.71 | 2300.70 | 2737.61 | 133.66 |

### Cold model only

| Stage | Participant | n | min ms | median ms | mean ms | p95 ms | max ms | std ms |
|---|---|---|---|---|---|---|---|---|
| UC1.interpret_request | X.C.1 -> C.0 | 1 | 3986.54 | 3986.54 | 3986.54 | 3986.54 | 3986.54 | 0.00 |
| C.1.1.model_call | C.1.1 -> Ollama qwen3:4b | 1 | 3986.42 | 3986.42 | 3986.42 | 3986.42 | 3986.42 | 0.00 |
| C.1.1.contract_check | C.1.1 | 1 | 0.07 | 0.07 | 0.07 | 0.07 | 0.07 | 0.00 |
| UC1.find_parking | X.C.1 -> C.0 | 1 | 26.01 | 26.01 | 26.01 | 26.01 | 26.01 | 0.00 |
| X.C.2.availability | C.0 -> X.C.2 (SQLite data store) | 1 | 23.21 | 23.21 | 23.21 | 23.21 | 23.21 | 0.00 |
| X.C.3.context | C.0 -> X.C.3 | 1 | 0.38 | 0.38 | 0.38 | 0.38 | 0.38 | 0.00 |
| X.C.4.rules | C.0 -> X.C.4 | 1 | 0.41 | 0.41 | 0.41 | 0.41 | 0.41 | 0.00 |
| C.1.prepare | C.1 | 1 | 1.85 | 1.85 | 1.85 | 1.85 | 1.85 | 0.00 |
| C.1.1.confirm | C.1.1 | 1 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.00 |
| C.1.2.requests | C.1.2 | 1 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C.1.3.validate | C.1.3 | 1 | 1.10 | 1.10 | 1.10 | 1.10 | 1.10 | 0.00 |
| C.1.4.eligibility | C.1.4 | 1 | 0.69 | 0.69 | 0.69 | 0.69 | 0.69 | 0.00 |
| C.3.rank | C.3 | 1 | 0.01 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 |
| C.0.assemble_result | C.0 (stands in for C.4) | 1 | 0.03 | 0.03 | 0.03 | 0.03 | 0.03 | 0.00 |
| HTTP.interpret_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 1 | 3987.37 | 3987.37 | 3987.37 | 3987.37 | 3987.37 | 0.00 |
| HTTP.confirm_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 1 | 27.14 | 27.14 | 27.14 | 27.14 | 27.14 | 0.00 |
| UC1.system_total | sum of the top-level stages | 1 | 4014.51 | 4014.51 | 4014.51 | 4014.51 | 4014.51 | 0.00 |
