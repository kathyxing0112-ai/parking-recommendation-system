# Chapter 7 — Actual Verification Results

| Item | Value |
|---|---|
| Run date | 2026-10-24 |
| Branch | `lab6-lab7-architecture-definition` |
| Python | 3.13.9 |
| pytest | 8.4.2 |
| Command | `python -m pytest tests/test_functional_requirements.py -v` |
| Summary | `3 failed, 4 passed in 0.03s` |

## System functional requirements 1.4.1–1.4.6

| Requirement | Test | Result | Actual result |
|---|---|---|---|
| 1.4.1 Prepare Eligible Parking Information | `test_FR_1_4_1_prepares_eligible_parking_information` | FAILED | NotImplementedError — function body not yet implemented. The test now also covers an area whose confirmed rule does not allow the declared permit (LOT-4), which must be excluded (SR-10). |
| 1.4.2 Estimate Arrival Time Availability | `test_FR_1_4_2_estimates_arrival_time_availability` | FAILED | NotImplementedError — function body not yet implemented; the forecasting model is planned for Chapter 8. |
| 1.4.3 Rank Parking Options | `test_FR_1_4_3_ranks_parking_options` | PASSED | Scored order LOT-2, LOT-1 (scores 0.68, 0.56); walking-time fallback order LOT-1, LOT-2 when a forecast is unsupported; one eligible area returns one option; no eligible area returns an empty list (SR-13). |
| 1.4.3 Rank Parking Options | `test_FR_1_4_3_tie_breaks_follow_sr13` | PASSED | Equal scores of 0.5 are ordered by ascending walking time (LOT-B, LOT-A); equal scores and walking times are ordered by area ID (LOT-A, LOT-B) (SR-13). |
| 1.4.4 Present Parking Recommendations and Status | `test_FR_1_4_4_presents_parking_recommendations_and_status` | FAILED | NotImplementedError — function body not yet implemented. |
| 1.4.5 Authorize Protected Data Operations | `test_FR_1_4_5_authorizes_protected_data_operations` | PASSED | All 10 role, operation, and session-ownership cases return the expected decision: same-session access permitted; cross-session access, missing session information, unlisted operations, and unknown roles denied (SR-03). Identity establishment is not verified. |
| 1.4.6 Apply Personal Data Retention Rules | `test_FR_1_4_6_applies_personal_data_retention_rules` | PASSED | Records at 25 h and 24 h 1 min are authorized for deletion; records at 23 h 59 min and 1 h are not; nothing is authorized when the authorization decision is denied. Only deletion authorization is verified; physical deletion and cached-copy removal are planned for Chapter 8 (SR-04, NFR.9). |

## 1.1.x–1.3.x

The input/output and interface requirements 1.1.x–1.3.x are verified by
inspection of the function signatures: each ICOM of A1–A6 maps to a parameter
(input), a keyword-only parameter (control), or a return value (output), as
listed in `docs/traceability.md`. No separate tests exist for these
requirements in this increment.

Three of them are exercised indirectly by passing tests:

- 1.1.1 (accept the data-retention schedule) by `test_FR_1_4_6_applies_personal_data_retention_rules`
- 1.1.2 (accept the approved role-permission matrix) by `test_FR_1_4_5_authorizes_protected_data_operations`
- 1.1.11 (accept the ranking and fallback rules) by `test_FR_1_4_3_ranks_parking_options` and `test_FR_1_4_3_tie_breaks_follow_sr13`
