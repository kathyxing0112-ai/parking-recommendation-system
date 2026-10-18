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
| A1 | Prepare Eligible Parking Information | `prepare_eligible_parking_information/` | 1.4.1 | SR-08, SR-09, SR-10, SR-12, SR-14 | SN-05, SN-06, SN-07, SN-08 | `test_FR_1_4_1_prepares_eligible_parking_information` | pending |
| A2 | Estimate Arrival Time Availability | `estimate_arrival_time_availability/` | 1.4.2 | SR-14 | SN-08 | `test_FR_1_4_2_estimates_arrival_time_availability` | pending |
| A3 | Rank Parking Options | `rank_parking_options/` | 1.4.3 | SR-13, SR-15 | SN-07, SN-08 | `test_FR_1_4_3_ranks_parking_options` | implemented; test passes |
| A4 | Present Parking Recommendations and Status | `present_parking_recommendations_and_status/` | 1.4.4 | SR-08, SR-09, SR-11, SR-13, SR-15 | SN-05, SN-07, SN-08 | `test_FR_1_4_4_presents_parking_recommendations_and_status` | pending |
| A5 | Authorize Protected Data Operations | `authorize_protected_data_operations/` | 1.4.5 | SR-03 | SN-02 | `test_FR_1_4_5_authorizes_protected_data_operations` | implemented; test passes |
| A6 | Apply Personal Data Retention Rules | `apply_personal_data_retention_rules/` | 1.4.6 | SR-04 | SN-02 | `test_FR_1_4_6_applies_personal_data_retention_rules` | implemented; test passes |

## Notes

- A1 is decomposed in the model into A1.1 Interpret and Confirm Parking
  Requests, A1.2 Request Parking, Context, and Policy Information, A1.3
  Validate Parking and Context Information, and A1.4 Determine Eligible
  Parking Areas. These child functions are implemented inside
  `prepare_eligible_parking_information/` and have no module of their own.
- The mechanism of every function is C.0, the system itself, so no
  signature has an injected dependency.
- The following modules are not functions on the IDEF0 and have no row:
  `smart_parking_service/` (orchestrates the UC.1 messages),
  `cornell_driver_interface/` (the system's interface to X.C.1),
  `language_model/` (the local language model used for trip-request
  interpretation, per ADR-0002), and the external-participant stubs
  `parking_availability_data_sources/` (X.C.2),
  `contextual_information_sources/` (X.C.3),
  `cornell_transportation_and_parking_services/` (X.C.4), and
  `cloud_and_network_infrastructure/` (X.C.5).
- 1.4 Provide Parking Decision Support (A0) is the parent requirement. It is
  verified through 1.4.1–1.4.6 and the end-to-end acceptance suite
  `tests/test_spec_acceptance.py`, and has no test of its own.
- A1, A2, and A4 bodies are not yet implemented, so their tests fail with
  `NotImplementedError`. A2 waits for the forecasting model and simulated
  data (Chapter 8).
