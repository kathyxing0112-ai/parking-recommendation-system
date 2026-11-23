# ADR-0004: Arrival-Time Forecast Architecture (DEC.2, ALT-F2 Hybrid)

## Status

Accepted on Weeks 11–12 validation evidence (Ch 11 trade study, X4, 2026-11-22).
Implemented in [PR #16](https://github.com/kathyxing0112-ai/parking-recommendation-system/pull/16) at merge commit `9bc07c3`.
The criteria below record the weights and maintainability ratings used in the
integrated report. The report’s life-cycle cost analysis records the local-pilot
affordability comparison. The selection was frozen before holdout verification.

## Context

A2 / C.2 has to forecast free spaces at the driver's arrival time, 0–72 h ahead
(SR-12, SR-14; the 72 h window was agreed on 2026-11-17). ADR-0002 named LightGBM
only as a candidate. The architecture was an open decision because no single
approach was best on every criterion. A model trained on recent occupancy is most
accurate at short lead times. A historical time-slot baseline is cheap and stable
at long lead times. A pretrained zero-shot model needs no training but is heavy
to run. The Ch 11 trade study (issue #10, Innoslate DEC.2) compared three options:

| Option | Architecture |
|---|---|
| ALT-F1 | One LightGBM quantile model for all lead times |
| ALT-F2 | Hybrid: LightGBM below a cutoff T_c, the lot × day-of-week × 15-min time-slot baseline from T_c to 72 h |
| ALT-F3 | Zero-shot Chronos-2 (no local training) |

All data is simulated (seed 5151, 15 weeks). Every option was trained on weeks
1–10 and compared on validation weeks 11–12. The holdout weeks 13–15 were not read.

## Criteria

Five criteria differ between the options (X4 §3; the weights are proposed and await team approval):

| Criterion | Measure | Weight |
|---|---|---|
| Ordinary-day accuracy | Usage-weighted MAE in spaces, all-day, without the event window | 0.45 |
| Event-day performance | Weighted MAE in the 2026-11-07 event window (one event) | 0.15 |
| Interval reliability | Distance of the calibrated 80% interval coverage from 80% | 0.15 |
| Response latency | Median time per 3-lot, 43-lead request | 0.10 |
| Maintainability | Team judgment, 1–5 | 0.15 |

Usage shares by lead band are a team assumption, not a measurement (2026-11-21):
0–1 h 50%, 1–3 h 25%, 3–6 h 10%, 6–24 h 10%, 24–72 h 5%.

X4 excludes data-interruption robustness. SR-09, SR-13 and SR-14 require the same
fallback for every option (no forecast for an observation older than 120 s; rank
by walking time), so the swing is zero.

## Measures

The source for each measure is `docs/measurements/ch11/README.md` on branch
`ch11-forecast-spike` (commit b58f095 for the validation numbers, 92303d0 for
the backtest and the pre-holdout predictions). The script is
`scripts/spike_forecast.py`.

| Measure (validation weeks 11–12) | ALT-F1 | ALT-F2 (T_c 3 h) | ALT-F3 |
|---|---|---|---|
| Usage-weighted MAE, ordinary all-day (spaces) | 4.62 | **4.28** | 5.96 |
| Usage-weighted MAE, ordinary daytime | 6.51 | **6.04** | 8.23 |
| Weighted MAE, event window (n = 1 event) | 11.7 | 31.0 | **9.8** |
| Calibrated 80% coverage, all-day | 75% | **78%** | 77% (uncalibrated) |
| Calibrated 80% coverage, daytime | 69% | 74% | **82%** (uncalibrated) |
| Median latency per request | 2.3 ms | **1.7 ms** | 658 ms |
| Memory, model + one request | 29 MB | **27 MB** | 312 MB |
| Training time | 109 s | **10 s** | none |

T_c is the shortest grid lead at which the short model's validation MAE exceeds
the baseline's (SR-14). The team read it without the event window (180 min), so
one event in two weeks does not set the cutoff; with the event window included
it reads 7 h (team decision 2026-11-21).

## Decision

**ALT-F2 with T_c = 180 min.** X4 total value: F2 77.50, F1 74.54, F3 25.00.

Sensitivity (X4 §4):

- F1 overtakes F2 when the event weight exceeds about 17.66%, offset against ordinary-day accuracy.
- Comparing raw MAE, F1 overtakes F2 when events make up more than about 1.73% of requests. In validation, 1.7% of forecasts (688 of 40,068) fell in the event window.
- If coverage is scored on daytime rather than all-day, F2's coverage value falls from 100 to 55.6 and the totals become F1 74.54, F2 70.83. Coverage is scored all-day because SR-14's 75–85% target is not split by time of day and the MAE criterion is all-day.

The lead is small and depends on weights and scope, so the holdout run (below) is the independent check.

## Implementation

Branch `a2-forecast-f2`, issue #12.

- `scripts/train_forecast.py` reuses the spike code. It trains the short LightGBM 10/50/90% quantile models (leads up to 6 h) and the baseline on weeks 1–10, with the settings frozen on 2026-11-21. It recomputes T_c and stops if T_c is not 180 min, widens the intervals by split conformal calibration on week 11 without the event window, and writes `estimate_arrival_time_availability/model/` with a manifest that records the data hash.
- `estimate_arrival_time_availability/` works per eligible lot with a current observation:
  - It uses the model at leads of 0, 15, 30, 45, 60 and 120 min; 0 min is the observation itself.
  - It interpolates linearly between grid points.
  - From 120 to 180 min it interpolates toward the baseline at T_c (SPEC SR-14, team choice 2026-11-22).
  - From 180 min to 72 h it uses the baseline for the arrival's time slot, and the page marks the forecast "for reference only".
  - The forecast is unsupported if the observation is stale or invalid, or the arrival is more than 72 h away. Missing look-back history falls back to the baseline.
- A3 ranks by the forecast when it is supported (issue #13) and falls back to walking time otherwise.
- `tests/test_a2_forecast.py` covers the A3 input constraints, method by lead, interpolation, the 72 h limit, stale input and a future-data leak check. `test_FR_1_4_2` passes and is no longer deselected in CI.

**Deviation from the Chapter 4 ICOMs.** A2 reads the occupancy history through
`parking_data_access`, and the calendar, event and weather features through
`contextual_information_sources`, directly. It does not receive them through A1's
`validated_context_information`, because the model needs features for each grid
lead time, not only for the arrival. The A2 signature itself is unchanged.

## Consequences

- **Events.** After T_c the baseline under-forecasts occupied spaces by about 64 in the one event window. Long-range forecasts are labeled for reference only, and the page asks the driver to check again closer to arrival. That wording does not guarantee behavior. The team decided on 2026-11-22 not to build an event-aware baseline this round.
- **Breaks.** In the backtest (train weeks 1–6, test weeks 8–10), F2's weighted MAE on the fall-break days 10/12–13 was 15.75 spaces, against 5.21 for F1, because the baseline assumes a normal weekday. The holdout includes Thanksgiving week (week 14), so SR-14 coverage is predicted to be at risk (pre-registered in 92303d0).
- **Holdout.** The team froze the approach, T_c and settings before the one Weeks 13–15 run. The [protocol](https://github.com/kathyxing0112-ai/parking-recommendation-system/blob/d0dbe52/scripts/evaluate_sr14_holdout.py) was committed before the [results](https://github.com/kathyxing0112-ai/parking-recommendation-system/blob/dc69b21/docs/measurements/ch11/holdout/results.json). All three checks met the preregistered all-day, usage-weighted scope. Coverage was 77.6% in that scope, approximately 71.4% for unweighted all-day and weighted daytime. The SR-14 verification record should state the weighting convention. The holdout did not determine the choice.
- **Dependency.** `lightgbm==4.7.0` is added to `requirements.txt`. The model files take about 7 MB in the repository.

## What the Losing Options Would Need

- **ALT-F1:** train one model on all leads up to 72 h (about 109 s), and fix its interval calibration. Its daytime coverage was 69%, below the 75% floor, so it needs a wider per-band widening or band weights. The same A2 code path would serve every lead time.
- **ALT-F3:** PyTorch and the Chronos-2 weights (Apache-2.0, checked 2026-11-21), about 312 MB of memory and about 0.66 s per request. Its interval needs calibration before SR-14, and a model download has to be added to the clean-machine setup (#15).

## What Would Change This Decision

- An SR-14 failure on the holdout opens a new trade study cycle, not a swap after the fact.
- Evidence that event or break days account for a larger share of requests. The raw-MAE crossover of approximately 1.73% is a sensitivity threshold. The proportion of simulated forecasts falling into the validation event window does not estimate real demand.
- An event- or calendar-aware baseline, which would remove F2's main weakness (future work).
