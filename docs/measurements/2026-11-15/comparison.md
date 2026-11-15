# Simulated vs measured UC.1 stage times

Simulation: Innoslate Monte Carlo, 100 runs per scenario, X2 V0.3 (HW6_B4_Simulation_Results.xlsx). Measurement: 50 runs per scenario through web_app POST endpoints (s1-http-warm, s2-http). All times in milliseconds.

| Scen. | Stage | Sim mean | Sim SD | Sim min-max | Meas. n | Meas. mean | Meas. SD | Meas. median | Meas. p95 | Meas. min-max | Sim / meas. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | s1.2 Initiate interpretation | 30.9 | 6.91 | 17.0-49.6 | 50 | 0.038 | 0.007 | 0.036 | 0.049 | 0.031-0.067 | 818.2x |
| S1 | s1.3 Language model inference | 2,341.6 | 580.4 | 650.9-4,010.9 | 50 | 2,165.7 | 174.3 | 2,118.7 | 2,318.7 | 1,996.5-2,982.8 | 1.1x |
| S1 | s1.4 Structure criteria | 41.8 | 9.66 | 16.2-64.5 | 50 | 0.052 | 0.011 | 0.049 | 0.080 | 0.043-0.10 | 807.7x |
| S1 | s1.6 + s1.7 Retrieve parking records | 48.1 | 9.35 | 27.3-71.9 | 50 | 17.8 | 0.96 | 17.8 | 19.2 | 16.1-22.5 | 2.7x |
| S1 | s1.8 Validate records | 20.4 | 4.91 | 7.87-31.7 | 50 | 1.24 | 0.050 | 1.23 | 1.32 | 1.11-1.44 | 16.5x |
| S1 | s1.9 Parking rules (X.C.4) | 9.70 | 2.14 | 4.18-16.7 | 50 | 0.16 | 0.032 | 0.16 | 0.22 | 0.12-0.25 | 59.3x |
| S1 | s1.10 Filter eligible options | 46.2 | 11.6 | 17.1-72.7 | 50 | 0.21 | 0.051 | 0.20 | 0.24 | 0.17-0.53 | 220.1x |
| S1 | s1.11 Rank recommendations | 70.6 | 18.4 | 30.6-112.5 | 50 | 0.009 | 0.001 | 0.009 | 0.011 | 0.007-0.013 | 7493.9x |
| S1 | s1.12 Deliver recommendations | 58.6 | 16.0 | 12.6-100.6 | 50 | 0.93 | 0.15 | 0.89 | 1.26 | 0.73-1.43 | 63.0x |
| S1 | Window C: interpretation (s1.2-s1.4) | 2,414.3 | 579.5 | 742.8-4,078.2 | 50 | 2,165.8 | 174.3 | 2,118.8 | 2,318.9 | 1,996.6-2,983.0 | 1.1x |
| S1 | Window D: confirmed request to delivery | 243.9 | 28.7 | 173.0-313.2 | 50 | 21.1 | 1.00 | 21.2 | 22.2 | 19.3-26.0 | 11.5x |
| S2 | s2.2 + s2.3 Retrieve parking records | 47.7 | 10.4 | 15.1-70.0 | 50 | 8.19 | 0.40 | 8.12 | 8.45 | 7.97-10.8 | 5.8x |
| S2 | s2.4 Validate records | 19.2 | 4.67 | 6.81-29.3 | 50 | 0.45 | 0.010 | 0.45 | 0.47 | 0.44-0.50 | 42.9x |
| S2 | s2.5 Parking rules (X.C.4) | 10.0 | 1.77 | 5.96-14.7 | 50 | 0.040 | 0.003 | 0.040 | 0.046 | 0.036-0.053 | 247.0x |
| S2 | s2.6 Filter eligible options | 46.1 | 12.3 | 18.0-70.7 | 50 | 0.082 | 0.12 | 0.065 | 0.077 | 0.061-0.90 | 560.6x |
| S2 | s2.7 Rank recommendations | 68.1 | 14.8 | 38.6-106.5 | 50 | 0.003 | 0.001 | 0.002 | 0.004 | 0.002-0.004 | 27230.1x |
| S2 | s2.8 Deliver recommendations | 59.4 | 14.5 | 32.2-101.2 | 50 | 0.65 | 2.42 | 0.30 | 0.41 | 0.25-17.4 | 92.0x |
| S2 | Window D: confirmed request to delivery | 240.4 | 25.6 | 177.8-304.9 | 50 | 9.57 | 2.94 | 9.15 | 9.45 | 8.95-29.9 | 25.1x |

S1 had no cold start: the product loads the model when it starts (warm-up), so run 1 was warm.

Measured stages with no modeled action:

| Scen. | Stage | n | mean ms | max ms |
|---|---|---|---|---|
| S1 | X.C.3.context | 50 | 0.55 | 0.98 |
| S1 | C.1.1.confirm | 50 | 0.032 | 0.078 |
| S1 | C.1.2.requests | 50 | 0.003 | 0.007 |
| S2 | X.C.3.context | 50 | 0.13 | 0.15 |
| S2 | C.1.1.confirm | 50 | 0.005 | 0.010 |
| S2 | C.1.2.requests | 50 | 0.001 | 0.002 |

SR-13 check (window D, 5 s limit, every run returned two options): S1 max 26.0 ms over 50 runs; S2 max 29.9 ms over 50 runs. Page rendering is not included.
