# Product Risk Register (Ch 12, §12.3)

**Status: draft.** The B3 likelihood and impact values below are copied from the team's B3 sheet (`风险表.xlsx`, sheet "B3 风险评分"), which is still marked "Draft initial values — pending team review". The six AI risks have no ratings yet. The team rates them on the same scales; AI does not score risks.

## Scales and Calculation (B3 量表)

- **Likelihood (L)** and **Cost, Schedule and Technical impact** are rated 1–5 using the definitions in the B3 量表 sheet.
- **Overall Impact (I)** is the mean of the three impacts, rounded. Each impact has weight 1/3 because the team has no approved dimension weights.
- **Risk = L × I.** Low is 1–5, Medium is 6–12 and High is 13–25. These thresholds are proposed and await team confirmation.
- In the matrix, likelihood increases up the vertical axis and Overall Impact increases to the right.
- Source: SYSEN 5151 Lab Manual v3.0, pp. 176–177 and 179–180.

## System-Level Risks (B1 Shortlist, B3 Ratings)

| ID | Risk | Type | L | C / S / T → I | Risk | Handling in the product | Innoslate | Code / tests |
|---|---|---|---|---|---|---|---|---|
| R-01 | Incorrect LLM interpretation becomes a confirmed request | LLM interpretation, accessibility | 3 | 3 / 2 / 4 → 3 | 9 Medium | Mitigate. The adapter accepts only listed values and arrival times within 72 h. Anything else is treated as missing, not substituted. The driver confirms all six fields before any search. | 319085 · I/O 308674 (s1.3 → s1.4) | `language_model/`, `tests/test_model_adapter.py` |
| R-02 | Stale or invalid occupancy appears current | Data freshness, integrity | 2 | 2 / 2 / 3 → 2 | 4 Low | Mitigate. A1.3 rejects invalid records and labels observations older than 120 s as stale (SR-09). A2 gives no forecast from a stale observation. | 319086 · I/O 308678 | `prepare_eligible_parking_information/`, `tests/test_a1_modules_independent.py` |
| R-03 | Recommendations violate eligibility or closure rules | Policy compliance, accessibility | 2 | 2 / 2 / 5 → 3 | 6 Medium | Mitigate. C.1.4 leaves out any area with no applicable confirmed rule, and the rule table is under team control. | 319087 · I/O 308680 | `prepare_eligible_parking_information/`, `tests/test_eligibility_filter*.py` |
| **R-04** | **Unsupported availability estimates drive ranking or display** | Forecast validity | 3 | 4 / 4 / 4 → 4 | **12 Medium (highest)** | **Guardrail (added 2026-11-22), see below.** It sits on top of A2's own "unsupported" status and A3's walking-time fallback. | 319088 · I/O 264259 (A2 → A3, A4) | `smart_parking_service.guard_forecasts`, `tests/test_r04_forecast_guard.py` |
| R-05 | Complete recommendations miss the driver-visible deadline | Response timeliness | 2 | 3 / 3 / 3 → 3 | 6 Medium | Monitor. Stage timing is recorded (`stage_timing`). The A2 model loads at start-up, so a request costs about 1 ms after warm-up. | 319089 · I/O 222138 | `stage_timing/`, `tests/test_measure_uc1.py` |

The matrix in the B3 矩阵 sheet places each risk in the right cell: R-01 at (3, 3), R-04 at (3, 4), R-02 at (2, 2), and R-03 and R-05 at (2, 3).

## AI-Specific Risks (Lab Manual §12.3.2)

| ID | Risk named by the Manual | Where it sits in the model | L | I | Risk | Handling in the product | Code / tests |
|---|---|---|---|---|---|---|---|
| AI-1 | Model output has the right format but wrong content | C.1.1.1 Qwen3 → C.1.1 adapter, s1.3 → s1.4 (I/O 308674). This is the AI side of R-01. | team | team | — | Value checks against the supported lists and the 72 h window. An unusable value is listed as missing, not guessed, and the driver confirms the trip. | `tests/test_model_adapter.py` (`test_unusable_value_is_listed_as_missing_not_substituted`, `test_access_needs_of_wrong_type_is_missing_not_false`) |
| AI-2 | Model unavailable or slow | C.1.1 → C.1.1.1, s1.2 → s1.3 (I/O 308673, candidate B1-25) | team | team | — | Fallback. A connection error or the 60 s timeout leads to `model_unavailable` and the six-field form. Truncated output falls back too. The model is warmed up at start-up. | `test_unreachable_or_slow_model_falls_back`, `test_truncated_output_falls_back`, `test_warm_up_failure_does_not_stop_the_product` |
| AI-3 | Untrusted input from a data source enters the prompt | X.C.1 driver message → C.1.1 prompt | team | team | — | Only the driver's message and the application's own supported-value lists enter the prompt. No occupancy, rule or context data does. Messages over 2,000 characters are not sent. Whatever the message says, the reply must pass the six-field contract and driver confirmation. | `test_overlong_message_is_not_sent_to_model`, `test_request_follows_adapter_specification` |
| AI-4 | Response schema drifts between model versions | C.1.1.1 → C.1.1 (Model Response Contract) | team | team | — | A reply that is not a JSON object with exactly the six fields is discarded (`wrong_fields` / `malformed_json`) and the form is shown. The model is named as `qwen3:4b` in `language_model/`. | `test_reply_without_the_six_fields_falls_back`, `test_unexpected_ollama_envelope_falls_back` |
| AI-5 | A dependency is deprecated | Ollama runtime (C.1.1.1 mechanism), `lightgbm` (C.2) | team | team | — | Python packages are pinned in `requirements.txt` (`lightgbm==4.7.0`). The forecast model files are versioned with a manifest and data hash, and `scripts/train_forecast.py` rebuilds them. The Ollama and Qwen3 versions are recorded in `docs/environment.md`. | `tests/test_a2_forecast.py::test_model_files_record_the_team_decisions` |
| AI-6 | Data leaves the machine by an unintended path | C.1.1 → C.1.1.1 endpoint; X.C.2/X.C.3 are local simulated sources | team | team | — | The model endpoint is the loopback address only. Raw messages and raw model output are never logged or stored (SR-04). No trip records are stored. Forecast features come from local simulated data. | `test_model_endpoint_is_local`, `test_fallback_presents_six_field_form_without_raw_output` |

## Top Risk R-04: Guardrail

The B3 ratings rank R-04 highest. **Type: guardrail.** It stops the failure from
reaching the driver rather than recovering after it.

The product already had two controls. A2 marks a forecast "unsupported", and A3
falls back to walking time when any eligible area lacks a supported, bounded
forecast (SR-13). Neither checked whether a "supported" estimate actually belongs
to this lot, this trip and a still-current observation. Those are the B1-20 and
B1-21 failure modes.

The new guardrail `guard_forecasts` (stage `C.0.forecast_guard`, between A2 and
A3) keeps an estimate only if all of these hold:

- A2 marked the lot supported, the lot is eligible, and A2 returned exactly one estimate for it.
- The counts are whole numbers with 0 ≤ lower ≤ estimate ≤ upper ≤ capacity, the capacity matches the observed one, and the interval level is 80%.
- The estimate is for this trip's arrival time, it was made from this lot's observation, and the lead time is 0–72 h.
- The observation is still "current" and is at most 120 s old when rechecked just before display (SR-14).

Any estimate that fails is withheld. The lot becomes "unsupported", A3 ranks by
walking time, and the page shows no forecast for it. The reason is returned in
`withheld` and is never shown to the driver.

`tests/test_r04_forecast_guard.py` has 22 failure-path tests (including missing fields and observation ages of 119, 120 and 121 s). Each feeds one
kind of bad A2 output, including through the whole UC.1 flow with A2 corrupted,
and asserts that nothing reaches ranking or display.

**Monitoring:** the `C.0.forecast_guard` stage time is recorded with the other
stages. After the holdout run, SR-14 coverage and MAE are reported in
`docs/measurements/ch11/`.

## Open Items for the Team

1. Confirm the B3 ratings and the Low/Medium/High thresholds. All five risks are still "draft".
2. Rate AI-1 to AI-6 on the B3 scales.
3. Update the R-04 evidence in B3 (column K). It says "SR-14 on main specifies 60 minutes". The 72 h window is on branch `ch11-forecast-trade` and reaches main with the A2 PR, so this line in this file and in Innoslate changes after the merge.
4. Confirm that the R-04 handling here matches the B5 mitigation plan.
