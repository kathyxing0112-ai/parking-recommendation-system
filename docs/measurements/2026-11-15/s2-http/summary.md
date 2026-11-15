# UC.1 Scenario 2: 50 runs through HTTP

Measured 2026-11-15T18:21:49+00:00 on Apple M4 (macOS-26.6.2-arm64-arm-64bit-Mach-O), commit 11c03c8.

Paths taken: form 50

### All runs

| Stage | Participant | n | min ms | median ms | mean ms | p95 ms | max ms | std ms |
|---|---|---|---|---|---|---|---|---|
| UC1.find_parking | X.C.1 -> C.0 | 50 | 8.67 | 8.85 | 8.93 | 9.16 | 12.49 | 0.52 |
| X.C.2.availability | C.0 -> X.C.2 (SQLite data store) | 50 | 7.97 | 8.12 | 8.19 | 8.45 | 10.83 | 0.40 |
| X.C.3.context | C.0 -> X.C.3 | 50 | 0.12 | 0.12 | 0.13 | 0.14 | 0.15 | 0.01 |
| X.C.4.rules | C.0 -> X.C.4 | 50 | 0.04 | 0.04 | 0.04 | 0.05 | 0.05 | 0.00 |
| C.1.prepare | C.1 | 50 | 0.51 | 0.52 | 0.54 | 0.56 | 1.38 | 0.12 |
| C.1.1.confirm | C.1.1 | 50 | 0.00 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 |
| C.1.2.requests | C.1.2 | 50 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C.1.3.validate | C.1.3 | 50 | 0.44 | 0.45 | 0.45 | 0.47 | 0.50 | 0.01 |
| C.1.4.eligibility | C.1.4 | 50 | 0.06 | 0.07 | 0.08 | 0.08 | 0.90 | 0.12 |
| C.3.rank | C.3 | 50 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| C.0.assemble_result | C.0 (stands in for C.4) | 50 | 0.00 | 0.01 | 0.00 | 0.01 | 0.01 | 0.00 |
| HTTP.confirm_round_trip | X.C.1 browser -> web_app (loopback HTTP) | 50 | 8.95 | 9.15 | 9.57 | 9.45 | 29.92 | 2.94 |
| UC1.system_total | sum of the top-level stages | 50 | 8.95 | 9.15 | 9.57 | 9.45 | 29.92 | 2.94 |
