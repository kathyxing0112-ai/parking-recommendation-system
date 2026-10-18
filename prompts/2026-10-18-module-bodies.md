# Component Prompts — Chapter 5 Module Bodies

Use each prompt in a new assistant session that has not seen the tests being
written. Generate one module per prompt. The tests must not be modified.

## A5 — Authorize Protected Data Operations

- **Context:** Cornell Smart Parking Availability & Recommendation System (C.0), an advisory parking decision-support service for three pilot areas using simulated data. A5 is a first-level function of A0 Provide Parking Decision Support; it has had a signature since Chapter 4, and this increment gives it a body.
- **Component:** `authorize_protected_data_operations.authorize_protected_data_operations`
- **Function performed:** A5 — Authorize Protected Data Operations
- **Requirements:** 1.4.5 — "The Cornell Smart Parking Availability & Recommendation System shall Authorize Protected Data Operations." Traced stakeholder requirement SR-03 (`SPEC.md`): "Under the approved three-role matrix, a driver may submit a trip, view results, and save, read, or update the trip record of the driver's own session; a maintainer may do the same and may also change parking rules, simulator settings, and model versions; the internal Retention Service may only delete trip records past their 24-hour expiry (SR-04). Any other operation, and any operation by an unrecognized role, is denied."
- **Interfaces:** Signature fixed in Chapter 4: `(protected_data_operation_request: dict, *, approved_role_permission_matrix: dict) -> dict`. The request has `role`, `operation`, and `record_id`. The matrix maps each role to a list of permitted operation names. Return `{"permitted": bool}`.
- **Constraints:** Python 3.13, standard library only, local execution, no changes to any other file.
- **Success criteria:** `tests/test_functional_requirements.py::test_FR_1_4_5_authorizes_protected_data_operations` passes without modification.
- **Output format:** The complete `authorize_protected_data_operations/__init__.py`, keeping the existing docstrings and signature.
- **Out of scope:** Identity establishment, session-ownership checks, logging, caching, retries, and error handling no requirement asked for. Do not refactor other modules or add dependencies.

## A6 — Apply Personal Data Retention Rules

- **Context:** As for A5. A6 is a first-level function of A0; this increment gives it a body.
- **Component:** `apply_personal_data_retention_rules.apply_personal_data_retention_rules`
- **Function performed:** A6 — Apply Personal Data Retention Rules
- **Requirements:** 1.4.6 — "The Cornell Smart Parking Availability & Recommendation System shall Apply Personal Data Retention Rules." Traced stakeholder requirement SR-04 (`SPEC.md`): retain trip records "for **no more than 24 hours after request submission**"; "A scheduled deletion removes each retained trip record by its 24-hour expiry." Per the A6 description in the model, record expiry is judged against the C.0 system clock.
- **Interfaces:** Signature fixed in Chapter 4: `(personal_records_and_retention_metadata: list[dict], *, authorization_decision: dict, approved_data_retention_schedule: dict) -> dict`. Each record has `record_id` and `submitted_at` (offset-aware ISO 8601). The schedule has `retention_hours`. The authorization decision has `permitted`. Return `{"protected_data_operation_request": dict, "personal_record_disposition_result": {"deleted": [record_id, ...]}}`; when `permitted` is false, nothing is deleted.
- **Constraints:** Python 3.13, standard library only, local execution, no changes to any other file.
- **Success criteria:** `tests/test_functional_requirements.py::test_FR_1_4_6_applies_personal_data_retention_rules` passes without modification.
- **Output format:** The complete `apply_personal_data_retention_rules/__init__.py`, keeping the existing docstrings and signature.
- **Out of scope:** Real storage, cache, log, or backup deletion; scheduling; logging; retries. Do not refactor other modules or add dependencies.

## A3 — Rank Parking Options

- **Context:** As for A5. A3 is a first-level function of A0; this increment gives it a body.
- **Component:** `rank_parking_options.rank_parking_options`
- **Function performed:** A3 — Rank Parking Options
- **Requirements:** 1.4.3 — "The Cornell Smart Parking Availability & Recommendation System shall Rank Parking Options." Traced stakeholder requirement SR-13 (`SPEC.md`), quoted: "When valid forecasts exist for all candidates, score each area as S = 0.40W + 0.40A + 0.20Q, where W = (w_max − w)/(w_max − w_min) for walking time w (W = 1 when all walking times are equal), A = F/C for forecast available spaces F and capacity C, and Q = 1 − (U − L)/C for the 80% prediction interval [L, U]. Inputs must satisfy C > 0, 0 ≤ F ≤ C, and 0 ≤ L ≤ U ≤ C. Round scores half-up to six decimals and rank by descending S, then ascending walking time, then area ID. If any forecast or interval is invalid, use the labeled fallback ordered by ascending walking time, then area ID." Return at most the first two options (primary and backup).
- **Interfaces:** Signature fixed in Chapter 4: `(normalized_trip_requirements: dict, validated_context_information: list[dict], eligible_parking_areas: list[dict], data_quality_and_freshness_status: dict, arrival_time_availability_estimates: list[dict], forecast_validity_status: dict, *, ranking_and_fallback_rules: dict) -> list[dict]`. Walking time comes from `validated_context_information` (`lot_id`, `walking_time_minutes`). Each estimate has `lot_id`, `capacity`, `available_spaces`, `interval_lower`, `interval_upper`. `forecast_validity_status` maps `lot_id` to "supported" or "unsupported". `ranking_and_fallback_rules["weights"]` holds `walking_time`, `availability`, and `uncertainty`. Each returned option includes `lot_id`.
- **Constraints:** Python 3.13, standard library only, local execution, no changes to any other file.
- **Success criteria:** `tests/test_functional_requirements.py::test_FR_1_4_3_ranks_parking_options` passes without modification.
- **Output format:** The complete `rank_parking_options/__init__.py`, keeping the existing docstrings and signature.
- **Out of scope:** Explanation text (A4), forecasting (A2), eligibility filtering (A1), logging, caching. Do not refactor other modules or add dependencies.

## A3 — Fix for zero eligible areas

- **Context:** As for A5. A3 already has a body; the 1.4.3 test was extended with the one- and zero-eligible-area cases from SR-13, and the zero-area case now fails.
- **Component:** `rank_parking_options.rank_parking_options`
- **Function performed:** A3 — Rank Parking Options
- **Requirements:** 1.4.3 — "The Cornell Smart Parking Availability & Recommendation System shall Rank Parking Options." Traced stakeholder requirement SR-13 (`SPEC.md`): "With one eligible area, show one option; with none, state that no confirmed eligible option is available." A3 returns an empty list when there are no eligible areas; A4 presents the message.
- **Interfaces:** Unchanged from the current signature and return shape.
- **Constraints:** Python 3.13, standard library only, local execution, no changes to any other file. Change only what is needed for the failing case.
- **Success criteria:** `tests/test_functional_requirements.py::test_FR_1_4_3_ranks_parking_options` passes without modification. The current failure is `ValueError: min() iterable argument is empty` when `eligible_parking_areas` is empty.
- **Output format:** A minimal diff to `rank_parking_options/__init__.py`.
- **Out of scope:** Any other change to the ranking logic, return fields, or other modules.

## A5 — Fix for session ownership

- **Context:** As for A5 above. A5 has a body, but SR-03's own-session rule was out of scope in the first prompt. The 1.4.5 test now covers it and fails.
- **Component:** `authorize_protected_data_operations.authorize_protected_data_operations`
- **Function performed:** A5 — Authorize Protected Data Operations
- **Requirements:** 1.4.5 — "The Cornell Smart Parking Availability & Recommendation System shall Authorize Protected Data Operations." SR-03 (`SPEC.md`): "a driver may submit a trip, view results, and save, read, or update the trip record of the driver's own session; a maintainer may do the same and may also change parking rules, simulator settings, and model versions; the internal Retention Service may only delete trip records past their 24-hour expiry (SR-04). Any other operation, and any operation by an unrecognized role, is denied."
- **Interfaces:** Signature unchanged. The matrix now maps each role to a dict of `{operation: scope}`, where scope is `"own_session"` or `"any"`. The request has `role` and `operation`, and for trip-record operations `caller_session_id` and `record_session_id`. Permit only when the role lists the operation and, for `"own_session"` scope, both session IDs are present and equal. Return `{"permitted": bool}`.
- **Constraints:** Python 3.13, standard library only, local execution, no changes to any other file.
- **Success criteria:** `tests/test_functional_requirements.py::test_FR_1_4_5_authorizes_protected_data_operations` passes without modification. It currently fails because a driver may read another session's record.
- **Output format:** A minimal diff to `authorize_protected_data_operations/__init__.py`.
- **Out of scope:** Identity establishment or authentication, logging, caching, other modules.

## A6 — Fix for disposition field

- **Context:** As for A6 above. A6 returned its expired record IDs as `deleted`, but no storage is deleted in this increment, so the field overstated the result. The 1.4.6 test now expects `authorized_for_deletion` and fails.
- **Component:** `apply_personal_data_retention_rules.apply_personal_data_retention_rules`
- **Function performed:** A6 — Apply Personal Data Retention Rules
- **Requirements:** 1.4.6 — "The Cornell Smart Parking Availability & Recommendation System shall Apply Personal Data Retention Rules." SR-04 (`SPEC.md`): trip records are retained "for **no more than 24 hours after request submission**." Physical deletion from storage arrives with the storage adapter in Chapter 8.
- **Interfaces:** Signature unchanged. Return `personal_record_disposition_result` as `{"authorized_for_deletion": [record_id, ...]}`, listing expired records only when the authorization decision permits; do not return a `deleted` field.
- **Constraints:** Python 3.13, standard library only, local execution, no changes to any other file.
- **Success criteria:** `tests/test_functional_requirements.py::test_FR_1_4_6_applies_personal_data_retention_rules` passes without modification. It currently fails with `KeyError: 'authorized_for_deletion'`.
- **Output format:** A minimal diff to `apply_personal_data_retention_rules/__init__.py`.
- **Out of scope:** Storage, cache, or backup deletion; any other change to the expiry logic; other modules.
