# Traceability

Function-to-module map for the first-level IDEF0 decomposition of A0 Provide
Parking Decision Support (Innoslate model v3). Each module implements exactly
one function, and its signature follows the function's ICOMs: inputs are
parameters, controls are keyword-only parameters, and outputs are return
values.

Each first-level function is satisfied by one system functional requirement
(1.4.1–1.4.6, children of 1.4 Provide Parking Decision Support). The
stakeholder requirements and needs come from the function's source
allocation (report Table 2) and `SPEC.md`. Tests are in
`tests/test_functional_requirements.py`.

| Function ID | Function Name | Module | Requirement | Stakeholder requirements | Needs | Test | Implementation |
|---|---|---|---|---|---|---|---|
| A1 | Prepare Eligible Parking Information | `prepare_eligible_parking_information/` | 1.4.1 | SR-08, SR-09, SR-10, SR-12, SR-14 | SN-05, SN-06, SN-07, SN-08 | `test_FR_1_4_1_prepares_eligible_parking_information` | implemented; test passes |
| A2 | Estimate Arrival Time Availability | `estimate_arrival_time_availability/` | 1.4.2 | SR-14 | SN-08 | `test_FR_1_4_2_estimates_arrival_time_availability` | pending |
| A3 | Rank Parking Options | `rank_parking_options/` | 1.4.3 | SR-13, SR-15 | SN-07, SN-08 | `test_FR_1_4_3_ranks_parking_options` | implemented; test passes |
| A4 | Present Parking Recommendations and Status | `present_parking_recommendations_and_status/` | 1.4.4 | SR-08, SR-09, SR-11, SR-13, SR-15 | SN-05, SN-07, SN-08 | `test_FR_1_4_4_presents_parking_recommendations_and_status` | pending |
| A5 | Authorize Protected Data Operations | `authorize_protected_data_operations/` | 1.4.5 | SR-03 | SN-02 | `test_FR_1_4_5_authorizes_protected_data_operations` | implemented; test passes |
| A6 | Apply Personal Data Retention Rules | `apply_personal_data_retention_rules/` | 1.4.6 | SR-04 | SN-02 | `test_FR_1_4_6_applies_personal_data_retention_rules` | implemented (deletion authorized, not yet physical); test passes |

## A1 second level

A1 is decomposed into A1.1 to A1.4, performed by C.1.1 to C.1.4. Requirement IDs
are from the C.1 Component Specification (report Section 3.2) and the Design
Output Requirements (report Section 3.3).

| Function ID | Function Name | Asset | Module | Requirements | Tests |
|---|---|---|---|---|---|
| A1.1 | Interpret and Confirm Parking Requests | C.1.1 | `prepare_eligible_parking_information/interpret_and_confirm_parking_requests.py`, `language_model/` | C.1 Spec 1.4.1, DO-01 | `tests/test_a1_modules_independent.py`, `tests/test_model_adapter.py` |
| A1.2 | Request Parking, Context, and Policy Information | C.1.2 | `prepare_eligible_parking_information/request_parking_context_and_policy_information.py`, `parking_data_access/` | C.1 Spec 1.4.2, C.1 Spec 2.3.2, DO-02 | `tests/test_a1_modules_independent.py`, `tests/test_data_access.py` |
| A1.3 | Validate Parking and Context Information | C.1.3 | `prepare_eligible_parking_information/validate_parking_and_context_information.py` | C.1 Spec 1.4.3, C.1 Spec 2.1.1, DO-03 | `tests/test_a1_modules_independent.py` |
| A1.4 | Determine Eligible Parking Areas | C.1.4 | `prepare_eligible_parking_information/determine_eligible_parking_areas.py` | C.1 Spec 1.4.4, C.1 Spec 2.1.2, DO-04 | `tests/test_eligibility_filter_independent.py`, `tests/test_eligibility_filter.py` |

## Notes

- The mechanism of every function was C.0 through Chapter 7. From Chapter 8
  each first-level function has its own subsystem C.1–C.6, and A1.1–A1.4 have
  C.1.1–C.1.4 (`docs/deployment.md`). No signature gained an injected
  dependency.
- Chapter 8 adds the C.1.2 data access component (`parking_data_access/`,
  `tests/test_data_access.py`) and the C.1.1 model adapter
  (`language_model/`, `docs/model-adapter.md`, `tests/test_model_adapter.py`).
  They implement A1's boundary exchanges with X.C.2 and the local model.
- The following modules are not functions on the IDEF0 and have no row:
  `smart_parking_service/` (orchestrates the UC.1 messages),
  `cornell_driver_interface/` (the system's interface to X.C.1),
  `language_model/` (the C.1.1 adapter to the local language model, per
  ADR-0002), `parking_data_access/` (the C.1.2 data access component), the
  simulated X.C.2 feed `parking_availability_data_sources/`, and the
  external-participant stubs
  `contextual_information_sources/` (X.C.3),
  `cornell_transportation_and_parking_services/` (X.C.4), and
  `cloud_and_network_infrastructure/` (X.C.5).
- 1.4 Provide Parking Decision Support (A0) is the parent requirement and
  has no test of its own. It is planned to be verified through the 1.4.1–1.4.6
  tests and a future end-to-end test; the acceptance suite
  `tests/test_spec_acceptance.py` does not yet call the system. Verification
  of 1.4 is not complete.
- A2 and A4 bodies are not yet implemented, so their tests fail with
  `NotImplementedError`. A2 waits for the forecasting model and simulated
  data. `.github/workflows/tests.yml` covers implemented behavior and must stay
  green; `.github/workflows/requirement-status.yml` runs the full suite and
  stays red until the remaining requirements are met.
- A6 identifies expired records and authorizes their deletion. Physical
  deletion from storage arrives with the storage adapter in Chapter 8, so
  SR-04 is only partly satisfied in this increment.
- Since Chapter 7 the internal flows between A1–A6 are defined by
  `contracts/api-v1.yaml`, and `tests/test_interface_contract.py` checks each
  module's signature against its generated stub (ADR-0003).
- A5 checks role, operation, and session ownership. Identity establishment
  is an open decision in the report and is not implemented.
