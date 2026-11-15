# Simulated vs measured UC.1 stage times

Simulation: Innoslate Monte Carlo, 100 runs per scenario, X2 V0.3 (HW6_B4_Simulation_Results.xlsx). Measurement: 50 runs per scenario through web_app POST endpoints (s1-http, s2-http). All times in milliseconds.

| Scen. | Stage | Sim mean | Sim SD | Sim min-max | Meas. n | Meas. mean | Meas. SD | Meas. median | Meas. p95 | Meas. min-max | Sim / meas. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | s1.2 Initiate interpretation | 30.9 | 6.91 | 17.0-49.6 | 50 | 0.039 | 0.008 | 0.037 | 0.055 | 0.030-0.065 | 791.8x |
| S1 | s1.3 Language model inference | 2,341.6 | 580.4 | 650.9-4,010.9 | 50 | 2,160.0 | 294.9 | 2,094.0 | 2,662.7 | 1,987.6-3,986.4 | 1.1x |
| S1 | s1.4 Structure criteria | 41.8 | 9.66 | 16.2-64.5 | 50 | 0.049 | 0.012 | 0.047 | 0.071 | 0.034-0.10 | 853.2x |
| S1 | s1.6 + s1.7 Retrieve parking records | 48.1 | 9.35 | 27.3-71.9 | 50 | 17.0 | 1.08 | 16.7 | 17.8 | 15.6-23.2 | 2.8x |
| S1 | s1.8 Validate records | 20.4 | 4.91 | 7.87-31.7 | 50 | 1.27 | 0.069 | 1.27 | 1.34 | 1.07-1.51 | 16.1x |
| S1 | s1.9 Parking rules (X.C.4) | 9.70 | 2.14 | 4.18-16.7 | 50 | 0.18 | 0.057 | 0.16 | 0.30 | 0.11-0.41 | 54.2x |
| S1 | s1.10 Filter eligible options | 46.2 | 11.6 | 17.1-72.7 | 50 | 0.22 | 0.072 | 0.20 | 0.26 | 0.16-0.69 | 212.5x |
| S1 | s1.11 Rank recommendations | 70.6 | 18.4 | 30.6-112.5 | 50 | 0.009 | 0.002 | 0.009 | 0.011 | 0.006-0.012 | 7574.3x |
| S1 | s1.12 Deliver recommendations | 58.6 | 16.0 | 12.6-100.6 | 50 | 0.93 | 0.16 | 0.92 | 1.25 | 0.67-1.45 | 62.8x |
| S1 | Window C: interpretation (s1.2-s1.4) | 2,414.3 | 579.5 | 742.8-4,078.2 | 50 | 2,160.1 | 294.9 | 2,094.1 | 2,662.9 | 1,987.7-3,986.5 | 1.1x |
| S1 | Window D: confirmed request to delivery | 243.9 | 28.7 | 173.0-313.2 | 50 | 20.4 | 1.10 | 20.1 | 21.1 | 19.5-27.1 | 12.0x |
| S1 | s1.3 inference, warm model only | 2,341.6 | 580.4 | 650.9-4,010.9 | 49 | 2,122.7 | 133.7 | 2,093.3 | 2,279.7 | 1,987.6-2,717.2 | 1.1x |
| S2 | s2.2 + s2.3 Retrieve parking records | 47.7 | 10.4 | 15.1-70.0 | 50 | 8.19 | 0.40 | 8.12 | 8.45 | 7.97-10.8 | 5.8x |
| S2 | s2.4 Validate records | 19.2 | 4.67 | 6.81-29.3 | 50 | 0.45 | 0.010 | 0.45 | 0.47 | 0.44-0.50 | 42.9x |
| S2 | s2.5 Parking rules (X.C.4) | 10.0 | 1.77 | 5.96-14.7 | 50 | 0.040 | 0.003 | 0.040 | 0.046 | 0.036-0.053 | 247.0x |
| S2 | s2.6 Filter eligible options | 46.1 | 12.3 | 18.0-70.7 | 50 | 0.082 | 0.12 | 0.065 | 0.077 | 0.061-0.90 | 560.6x |
| S2 | s2.7 Rank recommendations | 68.1 | 14.8 | 38.6-106.5 | 50 | 0.003 | 0.001 | 0.002 | 0.004 | 0.002-0.004 | 27230.1x |
| S2 | s2.8 Deliver recommendations | 59.4 | 14.5 | 32.2-101.2 | 50 | 0.65 | 2.42 | 0.30 | 0.41 | 0.25-17.4 | 92.0x |
| S2 | Window D: confirmed request to delivery | 240.4 | 25.6 | 177.8-304.9 | 50 | 9.57 | 2.94 | 9.15 | 9.45 | 8.95-29.9 | 25.1x |

S1 cold-start inference (run 1, model unloaded first): 3,986.4 ms.

Measured stages with no modeled action:

| Scen. | Stage | n | mean ms | max ms |
|---|---|---|---|---|
| S1 | X.C.3.context | 50 | 0.57 | 0.92 |
| S1 | C.1.1.confirm | 50 | 0.032 | 0.095 |
| S1 | C.1.2.requests | 50 | 0.003 | 0.007 |
| S2 | X.C.3.context | 50 | 0.13 | 0.15 |
| S2 | C.1.1.confirm | 50 | 0.005 | 0.010 |
| S2 | C.1.2.requests | 50 | 0.001 | 0.002 |

SR-13 check (window D, 5 s limit, every run returned two options): S1 max 27.1 ms over 50 runs; S2 max 29.9 ms over 50 runs. Page rendering is not included.
