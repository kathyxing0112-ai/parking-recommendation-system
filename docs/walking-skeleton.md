# Walking Skeleton — UC.1 Find Suitable Parking

This increment builds the walking skeleton for UC.1, the use case that delivers
the main value of the system-of-interest: a Cornell Driver obtaining ranked
parking recommendations for a planned trip and rechecking the selected option
before arrival.

The skeleton follows the **updated UC.1 sequence diagram** in Innoslate. It
replaces the Lab 2 call list, which was built from an earlier version of the
diagram.

## Sequence (from the model)

| UC.1 message | From → To | Implementation |
|---|---|---|
| UC.1.1 Submit Trip Request | Cornell Driver → SoI | `cornell_driver_interface.submit_trip_request()` |
| UC.1.2 Interpret and Confirm Trip Request | SoI → Cornell Driver | `smart_parking_service.interpret_trip_request()` → `language_model.interpret_trip_request()` |
| UC.1.3 Confirm Trip Requirements | Cornell Driver → SoI | `cornell_driver_interface.confirm_trip_requirements()` |
| UC.1.4 Request Parking Availability | SoI → X.C.2 | `parking_availability_data_sources.get_current_parking_availability()` |
| UC.1.6 Request Context Information | SoI → X.C.3 | `contextual_information_sources.get_contextual_information()` |
| UC.1.8 Request Parking Rules and Closures | SoI → X.C.4 | `cornell_transportation_and_parking_services.get_parking_rules_and_closures()` |
| UC.1.5 Provide Current Parking Availability | X.C.2 → SoI | return value of the X.C.2 call |
| UC.1.7 Provide Context Information | X.C.3 → SoI | return value of the X.C.3 call |
| UC.1.9 Provide Parking Rules and Closures | X.C.4 → SoI | return value of the X.C.4 call |
| UC.1.10–UC.1.13 (internal Actions) | within SoI | placeholder inside `smart_parking_service.find_suitable_parking()` |
| UC.1.14 Present Ranked Parking Recommendations | SoI → Cornell Driver | `ranked_options` returned by `find_suitable_parking()` |
| UC.1.16 Select Parking Option | Cornell Driver → SoI | `cornell_driver_interface.select_parking_option()` |
| UC.1.17 Present Selected Parking Information | SoI → Cornell Driver | `smart_parking_service.get_selected_parking_information()` |
| UC.1.18 Request Pre-Arrival Status Recheck | Cornell Driver → SoI | `cornell_driver_interface.request_pre_arrival_recheck()` |
| UC.1.19 Request Updated Parking Availability | SoI → X.C.2 | `parking_availability_data_sources.get_updated_parking_availability()` |
| UC.1.20 Provide Updated Parking Availability | X.C.2 → SoI | return value of the X.C.2 call |
| UC.1.21 Present Updated Parking Status | SoI → Cornell Driver | return value of `smart_parking_service.recheck_parking_status()` |

`app.py` plays the Cornell Driver and prints the result of each driver-facing
message, labeled with its UC.1 identifier.

## Participants

### External actors and systems

- Cornell Driver (X.C.1) — a person; the system's interface to this actor is
  `cornell_driver_interface/`, and `app.py` plays the driver
- Parking Availability Data Sources (X.C.2) — `parking_availability_data_sources/`
- Contextual Information Sources (X.C.3) — `contextual_information_sources/`
- Cornell Transportation and Parking Services (X.C.4) — `cornell_transportation_and_parking_services/`

Cloud and Network Infrastructure (X.C.5) is an enabling system. It supports
future hosting and network access but has no message in UC.1, so its
placeholder package is not invoked.

### Components internal to the system-of-interest

- Cornell Driver Interface — `cornell_driver_interface/`
- Smart Parking Service — `smart_parking_service/`
- Language Model — `language_model/` (formerly `recommendation_model/`)

The sequence diagram shows the system-of-interest as a single lifeline, so
these internal components have no lifeline of their own. Per ADR-0002, the
Language Model only interprets the driver's message into the six-field trip
request (UC.1.2); the Smart Parking Service derives recommendation
explanations from the factors it used (SR-15).

## Scope and Placeholders

- Every external participant and the Language Model return hard-coded,
  synthetic values of the right shape; outputs are labeled `synthetic`.
- UC.1.10–UC.1.13 (validate inputs, filter ineligible areas, estimate
  arrival-time availability, rank primary and backup options) are a single
  placeholder: the primary and backup options are hard-coded, not computed.
- The skeleton sends each external request and receives its response before
  the next request, whereas the diagram shows the three requests before the
  three responses; the participants and information exchanged are the same.
- UC.1.15 and the trip-completion Actions after UC.1.21 have no message in the
  sequence diagram and are not part of this skeleton.
