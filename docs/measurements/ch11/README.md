# Ch11 trade study: forecast spike results (validation weeks 11–12)

Input for the C.2 forecast trade study (DEC.2). These are measurements, not the decision.
The swing weights, value functions and the choice belong to the team's trade study (X1/X2/X4).

All numbers come from **simulated data** (`data/simulated/occupancy_15min.csv`, seed 5151).
They describe how each alternative does on the simulator, not on Cornell lots.

Produced by `python scripts/spike_forecast.py` at commit 63a5daa on branch `ch11-forecast-spike`
(no uncommitted changes; the data file's SHA-256 is in `run.json`). Run on 2026-11-21.
The LightGBM and Chronos forecasts are identical to the run at 632a7e4; this run adds the
usage-weighted scores and calibrates without the event window.

| File | Contents |
|---|---|
| `by_band.csv` | MAE, bias, pinball loss, coverage and width by lead-time band; all-day, daytime, and all-day without the event window |
| `per_lead.csv` | The same for each of the 43 lead times (all-day and daytime) |
| `event_window.csv` | The 2026-11-07 event window only |
| `cutoff_short_model_vs_baseline.csv` | The per-lead MAE pairs that set T_c, with and without the event window |
| `calibration_check_week12.csv` | Forecasts made in week 12: every method, plus the calibrated LightGBM options |
| `usage_weighted.csv` | Each metric by request band (0–1, 1–3, 3–6, 6–24, 24–72 h) and weighted by the request shares below; five scopes including the event window |
| `usage_weighted_week12_calibrated.csv` | The same on forecasts made in week 12, with the calibrated options |
| `run.json` | T_c, request shares, calibration widening, leakage checks that held, cost, environment |

## Decisions recorded on 2026-11-21

| Decision | Choice | By |
|---|---|---|
| Share of requests by how long before arrival | 0–1 h 50%, 1–3 h 25%, 3–6 h 10%, 6–24 h 10%, 24–72 h 5% (an assumption; there is no usage data) | Team |
| How to read the T_c rule | Without the event window: **T_c = 3 h** | Katherine; to confirm in X4 |
| Main selection score | Usage-weighted MAE without the event window, all-day and daytime | Katherine; to confirm in X4 |
| Event window | Not deleted: reported on its own as a separate line (n = 1) | Katherine; weight set in X4 |
| Interval calibration | Week 11 without the event window | Katherine |
| Retrain on weeks 1–12 before the holdout | No: the holdout is run once with the weeks 1–10 models | Katherine |

Reasons. One game in two validation weeks is not an ordinary period, and T_c describes ordinary
days. Most requests are expected close to arrival, and a driver who plans days ahead is expected
to check again within T_c before leaving, so long-lead forecasts are a reference only. The holdout
(week 13) has a home game on 11-21 from the event list, so the event weakness is shown here rather
than first seen in the holdout.

## Set-up

| Item | Value |
|---|---|
| Training data | Weeks 1–10 (2026-08-24 to 11-01). Forecast time and target time both in weeks 1–10 |
| Validation data | Weeks 11–12 (11-02 to 11-15). Forecast time and target time both in weeks 11–12 |
| Holdout | Weeks 13–15 are **not read**: they are dropped when the file is loaded, and a check stops the run if any remain |
| Forecast times scored | Every whole hour of weeks 11–12: 336 times × 3 lots |
| Lead times | 43: 15–60 min by 15 min, 2–24 h hourly, 27–72 h every 3 h. 40,068 scored forecasts |
| Inputs allowed | Occupancy at or before the forecast time; calendar, event list and weather forecast for the target day (known in advance) |
| Scopes | All-day; daytime (target time 07:00–18:59 local); all-day without the event window (2026-11-07 10:00–17:59, LOT-1 and LOT-2, 688 of 40,068 forecasts) |

**Leakage checks.** The script stops if any of these fail. All held in this run:
no holdout row is kept; the forecast time and target time are in the same split; lag, last-week and
profile inputs are at or before the forecast time; every label is after its forecast time; labels
are not features; the baseline table uses weeks 1–10 only; Chronos history ends at the forecast
time; Chronos future covariates are calendar, event and weather-forecast values only.

## Metrics

| Metric | Meaning |
|---|---|
| MAE | Mean absolute error of the median forecast, in spaces. SR-14 selects the model or the baseline by this |
| Bias | Mean of (median forecast − observed). Below 0 means occupancy is under-forecast, so a lot looks emptier than it is, which is the riskier direction for drivers |
| Pinball loss | Quantile loss averaged over the 10/50/90% forecasts, in spaces. It rewards an accurate median and an interval that is neither too narrow nor too wide |
| Coverage | Share of observations inside the 80% interval (10%–90%). Target 75%–85% (SR-14) |
| Width | Mean width of the 80% interval, in spaces |

## Alternatives as run

| Label | What it is |
|---|---|
| baseline | Historical time-slot baseline: median and 10%/90% quantiles of occupied spaces per lot × day of week × 15-min time of day, weeks 1–10 |
| ALT-F1 | One LightGBM quantile model (10/50/90%) for all lead times 15 min–72 h. It predicts the departure from the lot's mean at the same weekday and time in earlier weeks (the "profile"). Features: lot, lead time, current rate, lags 15/30/60 min, 1-h mean, same time last week, profiles at the forecast and target times and the current departure from them, and the target-day calendar, event flag and weather forecast. Lead-time bands carry equal weight in training |
| ALT-F2 | Hybrid: a LightGBM with the same features, trained only on lead times ≤ 6 h, is used below T_c; the baseline is used from T_c on |
| ALT-F3 | Chronos-2 (`amazon/chronos-2`, 120M parameters), zero-shot. Input: 21 days of occupancy history plus known future covariates (class day, break, weekend, event flag, precipitation chance, temperature) |
| ALT-F3b | Chronos-Bolt-Small (`amazon/chronos-bolt-small`, 48M parameters), zero-shot, occupancy history only. Reference run |

### T_c (set from data, not traded)

Rule: T_c is the shortest lead time at which the ALT-F2 LightGBM's validation MAE is higher than the
baseline's. If that never happens within the model's 6-hour range, T_c is the next grid point.

| Read on | Model vs. baseline MAE | T_c |
|---|---|---|
| All validation forecasts | The model is better at every lead up to 6 h (5.68 vs. 6.09 at 6 h) | **7 h** (next grid point) |
| Without the event window | The model is better up to 2 h (4.88 vs. 5.12) and worse from 3 h (5.22 vs. 5.12) | **3 h** |

The rule gives a different answer depending on whether the one event is included. Both versions of
ALT-F2 are reported, as "ALT-F2 (T_c 7 h)" and "ALT-F2 (T_c 3 h)". **The team needs to decide which
reading of the rule to use.** Decided 2026-11-21: the reading without the event window, T_c = 3 h.

## Selection score: usage-weighted MAE

Each request band is weighted by its share of requests (team assumption above). Two other share
sets check whether the ranking depends on the assumption. Without the event window. MAE in spaces.

**All-day**

| Band (share) | baseline | ALT-F1 | ALT-F2 (T_c 7 h) | ALT-F2 (T_c 3 h) | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|---|
| 0–1 h (50%) | 5.12 | 3.98 | **3.53** | **3.53** | 3.94 | 4.69 |
| 1–3 h (25%) | 5.12 | 5.13 | 5.05 | **5.00** | 6.84 | 8.12 |
| 3–6 h (10%) | **5.13** | 5.42 | 5.51 | **5.13** | 8.17 | 9.41 |
| 6–24 h (10%) | **5.02** | 5.37 | **5.02** | **5.02** | 9.27 | 9.22 |
| 24–72 h (5%) | **4.97** | 5.42 | **4.97** | **4.97** | 10.83 | 9.45 |
| **Weighted, team shares 50/25/10/10/5** | 5.10 | 4.62 | 4.33 | **4.28** | 5.96 | 6.71 |
| Weighted, more near 70/15/5/5/5 | 5.11 | 4.36 | 4.01 | **3.98** | 5.19 | 5.90 |
| Weighted, more far 30/20/15/20/15 | 5.08 | 4.92 | 4.65 | **4.58** | 7.25 | 7.70 |

**Daytime (07:00–18:59)**

| | baseline | ALT-F1 | ALT-F2 (T_c 7 h) | ALT-F2 (T_c 3 h) | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|---|
| **Weighted, team shares** | 7.09 | 6.51 | 6.17 | **6.04** | 8.23 | 9.21 |
| Weighted, more near | 7.08 | 6.13 | 5.69 | **5.62** | 7.00 | 7.93 |
| Weighted, more far | 7.06 | 6.92 | 6.59 | **6.44** | 10.18 | 10.87 |

ALT-F2 (T_c 3 h) has the lowest weighted MAE under all three share sets, all-day and daytime,
so the ranking does not depend on the exact shares.

**Bias, team shares, without the event window (spaces):** baseline −1.06 (daytime −1.23),
ALT-F1 −0.32 (−0.11), ALT-F2 (T_c 7 h) −0.41 (−0.35), ALT-F2 (T_c 3 h) −0.54 (−0.52),
ALT-F3 +0.62 (+0.25). Weighted this way, ALT-F2's under-forecast is about half a space, because
most requests fall before T_c, where the model is used.

**Event window, MAE by request band (n = 1, reference)**

| | 0–1 h | 1–3 h | 3–6 h | 6–24 h | 24–72 h | Weighted, team shares |
|---|---|---|---|---|---|---|
| baseline | 64.1 | 64.0 | 64.0 | 64.0 | 64.0 | 64.0 |
| ALT-F1 | 11.4 | 11.1 | 12.7 | 13.1 | 13.1 | 11.7 |
| ALT-F2 (T_c 7 h) | 11.3 | 11.2 | 10.6 | 64.0 | 64.0 | 19.1 |
| ALT-F2 (T_c 3 h) | 11.3 | 37.4 | 64.0 | 64.0 | 64.0 | 31.0 |
| ALT-F3 Chronos-2 | **7.3** | 11.9 | 13.3 | 12.3 | 12.1 | **9.8** |

ALT-F2 (T_c 3 h) uses the baseline from 3 h on, so it misses the game by about 64 spaces there.
The 1–3 h value (37) is the mean of 2 h (model, accurate) and 3 h (baseline).

## Accuracy: MAE by lead-time band

MAE in spaces; lower is better. The best value in each row is in bold.

**All-day**

| Band | baseline | ALT-F1 | ALT-F2 (T_c 7 h) | ALT-F2 (T_c 3 h) | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|---|
| 0–1 h | 6.06 | 4.09 | **3.66** | **3.66** | 3.99 | 4.86 |
| 1–6 h | 6.07 | **5.41** | **5.41** | 5.85 | 7.71 | 9.75 |
| 6–24 h | 6.00 | **5.50** | 6.00 | 6.00 | 9.32 | 10.25 |
| 24–48 h | 6.02 | **5.51** | 6.02 | 6.02 | 10.87 | 10.61 |
| 48–72 h | 6.12 | **5.62** | 6.12 | 6.12 | 10.83 | 10.61 |
| 0–72 h | 6.04 | **5.37** | 5.72 | 5.77 | 9.11 | 9.77 |

**All-day, without the event window (98% of forecasts)**

| Band | baseline | ALT-F1 | ALT-F2 (T_c 7 h) | ALT-F2 (T_c 3 h) | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|---|
| 0–1 h | 5.12 | 3.98 | **3.53** | **3.53** | 3.94 | 4.69 |
| 1–6 h | 5.13 | 5.30 | 5.32 | **5.08** | 7.63 | 8.89 |
| 6–24 h | **5.02** | 5.37 | **5.02** | **5.02** | 9.27 | 9.22 |
| 24–48 h | **4.97** | 5.37 | **4.97** | **4.97** | 10.85 | 9.50 |
| 48–72 h | **4.98** | 5.47 | **4.98** | **4.98** | 10.81 | 9.40 |
| 0–72 h | 5.03 | 5.24 | 4.89 | **4.86** | 9.06 | 8.80 |

**Daytime (07:00–18:59, event window included)**

| Band | baseline | ALT-F1 | ALT-F2 (T_c 7 h) | ALT-F2 (T_c 3 h) | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|---|
| 0–1 h | 8.88 | 5.76 | 5.18 | 5.18 | **5.11** | 6.28 |
| 1–6 h | 8.96 | **7.63** | 7.79 | 8.63 | 10.94 | 14.20 |
| 6–24 h | 8.90 | **7.73** | 8.90 | 8.90 | 13.38 | 15.47 |
| 24–48 h | 8.92 | **7.69** | 8.92 | 8.92 | 15.35 | 15.96 |
| 48–72 h | 9.09 | **7.86** | 9.09 | 9.09 | 14.85 | 16.02 |
| 0–72 h | 8.94 | **7.53** | 8.42 | 8.53 | 12.84 | 14.57 |

**Week 12 only (no event; forecasts made in week 12), 0–72 h:** baseline 5.19, ALT-F1 5.67,
ALT-F2 (T_c 7 h) 5.08, ALT-F2 (T_c 3 h) **5.01**, ALT-F3 7.18, ALT-F3b 7.93.

**Reading.** ALT-F1's lead at 6–72 h comes from the single event day. On 11-07 its long-lead
error over the whole day is 7.0 spaces against the baseline's 16.7. On ordinary times the
baseline beats ALT-F1 in every band from 6 h on (by about 0.35–0.5 spaces). The short-term signal helps for the first
2–3 hours. After that, the historical median is at least as good as the model on ordinary days.

## Event window (2026-11-07 football game, 10:00–17:59, LOT-1 and LOT-2)

One event only, so these numbers are for reference and are not a selection criterion on their own. MAE in spaces.

| Band | baseline | ALT-F1 | ALT-F2 (T_c 7 h) | ALT-F2 (T_c 3 h) | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|---|
| 0–1 h | 64.1 | 11.4 | 11.3 | 11.3 | **7.3** | 15.4 |
| 1–6 h | 64.0 | 12.1 | **10.8** | 53.3 | 12.7 | 62.4 |
| 6–24 h | 64.0 | 13.1 | 64.0 | 64.0 | **12.3** | 71.0 |
| 48–72 h | 64.0 | 13.0 | 64.0 | 64.0 | **11.9** | 71.8 |

Methods that use the event list (ALT-F1, ALT-F3, and the ALT-F2 LightGBM part) stay at 7–13
spaces. Wherever the baseline is used, the forecast misses the game by about 64 spaces.

## Bias, pinball loss and interval coverage (0–72 h, before calibration)

| | baseline | ALT-F1 | ALT-F2 (T_c 7 h) | ALT-F2 (T_c 3 h) | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|---|
| Bias, all-day | −1.98 | **+0.08** | −1.56 | −1.73 | +2.74 | −0.64 |
| Bias, daytime | −3.13 | **+0.67** | −2.39 | −2.70 | +3.28 | −1.58 |
| Pinball, all-day | 1.95 | **1.79** | 1.84 | 1.86 | 2.96 | 3.44 |
| Pinball, no event window | 1.75 | 1.76 | 1.67 | **1.67** | 2.95 | 2.99 |
| Coverage (target 0.75–0.85) | **0.75** | 0.56 | 0.72 | 0.74 | **0.77** | 0.65 |
| Width, spaces | 19.2 | 10.1 | 16.9 | 17.8 | 31.5 | 18.0 |

The baseline and ALT-F2 under-forecast daytime occupancy by 2–3 spaces on average, and part of
that is the event day. ALT-F1 is nearly unbiased.

## Interval calibration (split conformal)

The LightGBM intervals were widened by one amount per lead-time band. The amount was set on
forecasts whose target time is in week 11, without the event window, so that about 80% of week-11 observations fall inside.
The result was checked on forecasts made in week 12. The median forecast, and therefore the MAE, does not change.

Widening (spaces added to each side): ALT-F1 1.95–2.18 depending on the band; ALT-F2 LightGBM part 1.24 (0–1 h) and 1.86 (1–6 h).
Including the event window in week 11 would change coverage by less than one percentage point.

**Check on week 12, 0–72 h**

| | Coverage all-day | Coverage daytime | Width | Pinball |
|---|---|---|---|---|
| baseline (not calibrated) | 0.76 | 0.74 | 18.4 | 1.82 |
| ALT-F1, before → after | 0.53 → **0.73** | 0.52 → **0.65** | 9.8 → 13.8 | 1.92 → 1.81 |
| ALT-F2 (T_c 7 h), before → after | 0.72 → **0.76** | 0.70 → **0.73** | 15.8 → 16.6 | 1.74 → 1.72 |
| ALT-F2 (T_c 3 h), before → after | 0.74 → **0.76** | 0.72 → **0.74** | 16.8 → 17.2 | 1.74 → 1.73 |
| ALT-F3 Chronos-2 (not calibrated) | 0.77 | 0.84 | 26.5 | 2.34 |

Calibration brings ALT-F2 into the 75%–85% target all-day. ALT-F1 improves, but it stays below
the target (0.73 all-day, 0.65 daytime). Its errors in week 12 were larger than
in week 11, and one calibration week did not capture that.

**Weighted by the team's request shares (week 12):**

| | Coverage all-day | Coverage daytime | Width all-day |
|---|---|---|---|
| baseline | 0.76 | 0.76 | 19.8 |
| ALT-F1, calibrated | 0.75 | 0.69 | 13.1 |
| ALT-F2 (T_c 7 h), calibrated | 0.78 | 0.72 | 13.0 |
| ALT-F2 (T_c 3 h), calibrated | **0.78** | **0.74** | 14.3 |
| ALT-F3 Chronos-2 | 0.77 | 0.82 | 16.6 |

ALT-F2 (T_c 3 h) meets the 75%–85% target all-day and is one point short in daytime.

## Cost

Apple M4, 16 GB, macOS 26.6, Python 3.13.9, CPU only. LightGBM 4.7.0, torch 2.11.0,
chronos-forecasting 2.3.2. Latency is for one request (all three lots, all 43 lead times), 30 runs
after one warm-up. Memory is measured in a new Python process: the libraries are imported first,
then the model is loaded and answers one request.

| | baseline | ALT-F1 | ALT-F2 | ALT-F3 Chronos-2 | ALT-F3b Bolt |
|---|---|---|---|---|---|
| Training time | < 0.01 s | 109 s | 10 s | none | none |
| Latency, median (p95) | 0.2 ms (0.2) | 2.3 ms (2.5) | 1.7 ms (1.9) | 658 ms (662) | 878 ms (885) |
| Model size | 59 KB table | 8.2 MB (3 models) | 7.1 MB incl. table | 120M parameters | 48M parameters |
| Memory for model + one request | 1 MB | 29 MB | 27 MB | 312 MB | 367 MB |
| Extra dependencies | none | lightgbm | lightgbm | torch, chronos-forecasting, model download | same as ALT-F3 |

Chronos latency was 684–868 ms on 2026-11-20, 832–1,244 ms in the earlier run on 2026-11-21 and
658–878 ms in this run. It varies with machine load, but the conclusion is the same: it is several
hundred times slower than LightGBM (about 290–520 times in this run).

Licences, checked by Katherine on 2026-11-21: `amazon/chronos-2` and `amazon/chronos-bolt-small`
(Hugging Face model pages) and `amazon-science/chronos-forecasting` (GitHub) are Apache-2.0.

## What the numbers show

These are observations only, not a recommendation.

0. **With the team's request shares and without the event window, ALT-F2 (T_c 3 h) has the
   lowest MAE** (4.28 all-day, 6.04 daytime; ALT-F1 4.62 and 6.51), under all three share sets.
1. **Unweighted, the overall winner depends on how much the event day counts.** With the event day,
   ALT-F1 has the lowest MAE (5.37). Without it, which covers 98% of forecasts and all of week 12,
   ALT-F2 is lowest (4.86–4.89) and ALT-F1 is worse than the baseline from 6 h on.
2. **The ALT-F2 premise holds on ordinary days.** The model helps for about the first 2–3 hours,
   then the historical median is as good or better. The 2026-11-20 summary said that ALT-F1's
   long-lead gain came from calendar and weather inputs. That was wrong: it came from the event day.
3. **Events are ALT-F2's weak point.** Beyond T_c, ALT-F2 uses the baseline, which has no event
   input and misses the game by about 64 spaces.
4. **Intervals.** After calibration, ALT-F2 meets the 75%–85% coverage target on week 12; ALT-F1
   does not (0.73 all-day, 0.66 daytime).
5. **Bias.** ALT-F1 is nearly unbiased. The baseline and ALT-F2 under-forecast occupancy, mostly in daytime.
6. **Zero-shot Chronos.** It is competitive only in the first hour and on the event day. It is
   much worse beyond 1 h on ordinary days, and it is several hundred times slower, with about
   10 times the memory of LightGBM.

## Backtest and predictions for the holdout (written 2026-11-22, before the holdout run)

The holdout (weeks 13–15) is harder than validation: week 13 has the 2026-11-21 home game and
week 14 is Thanksgiving break (2026-11-25 to 11-29). Validation has one event and no break
weekdays. To see how the options behave on such days without reading the holdout, the training
weeks were split again: train on weeks 1–6, forecast weeks 7–10, which contain fall break
(10/12–13 weekdays), the homecoming game (10/17) and an evening concert (10/28).

Settings are the frozen ones, ALT-F2 uses T_c = 3 h, its short model is calibrated on week 7
(no event window) and checked on forecasts made in weeks 8–10. Scores use the team's request
shares. Script: `scripts/backtest_forecast.py`. Six training weeks instead of ten, so the
numbers are conservative.

| Weeks 8–10, usage-weighted | n | Baseline MAE | ALT-F1 MAE | ALT-F2 MAE | ALT-F2 coverage | ALT-F2 bias |
|---|---|---|---|---|---|---|
| All day, without event windows | 60,364 | 7.84 | 5.61 | **5.55** | 0.745 | +2.08 |
| Daytime, without event windows | 29,554 | 11.98 | 8.25 | **8.23** | 0.698 | +3.74 |
| Break weekdays 10/12–13 | 3,240 | 33.6 | **5.21** | 15.75 | 0.475 | +13.82 |
| Event windows | 1,505 | 71.9 | **12.13** | 34.75 | 0.268 | −30.84 |

Positive bias means the forecast says the lot is fuller than it is (the safe direction for a
driver); negative means emptier. Beyond T_c ALT-F2 uses the baseline, which has no break or
event input: it over-forecasts on break days and under-forecasts during events.

**Predictions for the SR-14 holdout checks**, recorded before the run, for ALT-F2 with T_c = 3 h:

| SR-14 check | Prediction | Reason |
|---|---|---|
| MAE not above the baseline | Likely met | ALT-F2 equals the baseline beyond T_c and beat it within T_c in validation and in the backtest (5.55 vs 7.84) |
| Primary option has a free space on arrival, ≥ 85 of 100 trips | Likely met | On break days ALT-F2 over-forecasts occupancy (safe direction). The risk is trips to LOT-1/LOT-2 during the 11/21 game requested more than 3 h ahead |
| 80% interval coverage 75%–85% | At risk | Backtest 0.745 all day, 0.698 daytime, 0.475 on break days; validation daytime 0.74 |

Whatever the holdout shows, the model, settings and T_c stay as they are; a missed check is
reported with its cause and recorded as a risk.

## Limitations to state in the report

- **Simulated data.** All factors (weekend ×0.4, break ×0.5, rain ×1.06, snow ×1.10, events,
  drift) are simulator assumptions. The weather forecast is the same at every lead time, which
  flatters long-lead forecasts.
- **Choices made on the validation weeks.** The LightGBM settings were frozen on 2026-11-21 after
  these trials on weeks 11–12. MAE is for the median model only:

  | # | Set-up | MAE at 15 min | MAE 0–72 h |
  |---|---|---|---|
  | 1 | Basic features, predicts the rate directly | 5.42 | 5.49 |
  | 2 | Same, with L1 or L2 loss | 5.55–5.59 | 5.60–5.66 |
  | 3 | + departure from last week | 5.13 | 5.44 |
  | 4 | Same, 1,500 trees | 5.41 | 5.63 |
  | 5 | + profile features | 4.93 | 5.53 |
  | 6 | + predicts the departure from the profile | 4.54 | 5.58 |
  | 7 | Equal weight per lead-time band, basic features | 5.28 | 5.67 |
  | 8 | Equal weight + profile features, predicts the rate | 4.19 | 5.36 |
  | 9 | Equal weight + profile features, predicts the departure (kept for ALT-F1) | 3.79 | 5.42 |
  | 10 | Larger model (255 leaves, 1,000 trees) | 4.07 | worse at long leads |
  | 11 | Trained on leads ≤ 6 h only, basic features | 3.75 | — |
  | 12 | Trained on leads ≤ 6 h only, profile features, predicts the departure (kept for ALT-F2) | 3.16 | — |

  T_c, the calibration, the request shares and the reading without the event were also set on
  these weeks, after the results were seen; both readings are kept in the tables. All of this favours the LightGBM options
  slightly. The single holdout run after selection is the unbiased check.
- **One event and no break weekdays in validation.** The event result rests on one game, and it
  decides whether ALT-F1 or ALT-F2 has the lower overall MAE. Break days are seen only
  in the backtest on training weeks (fall break) and in the holdout (Thanksgiving, week 14).
- **Request shares are an assumption.** There is no usage data (no trip records are stored). The
  sensitivity check shows the ranking holds for shares tilted toward nearer or farther requests.
- **Calibration uses one week.** It is checked on one more week; coverage on the holdout may differ.
- **Chronos settings.** The context is 21 days of history. Chronos-Bolt forecasts past 64 steps
  by feeding its own forecasts back in, so its long-lead result reflects the model as used here.
