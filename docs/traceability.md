# Traceability

Function-to-module map for the first-level IDEF0 decomposition of A0 Provide
Parking Decision Support (Innoslate model v3). Each module implements exactly
one function, and its signature follows the function's ICOMs: inputs are
parameters, controls are keyword-only parameters, and outputs are return
values. Requirement and test columns are added in Chapter 5.

| Function ID | Function Name | Module |
|---|---|---|
| A1 | Prepare Eligible Parking Information | `prepare_eligible_parking_information/` |
| A2 | Estimate Arrival Time Availability | `estimate_arrival_time_availability/` |
| A3 | Rank Parking Options | `rank_parking_options/` |
| A4 | Present Parking Recommendations and Status | `present_parking_recommendations_and_status/` |
| A5 | Authorize Protected Data Operations | `authorize_protected_data_operations/` |
| A6 | Apply Personal Data Retention Rules | `apply_personal_data_retention_rules/` |

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
