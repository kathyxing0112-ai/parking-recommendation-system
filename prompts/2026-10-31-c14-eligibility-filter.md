# C.1.4 Eligibility Filter Module — Lab 9 Product Build (DRAFT, not yet sent)

Context: SYSEN 5151 Team 26, Lab 9 Product Build (Lab Manual §9.4, p.160–161).
Task sheet item K6. **Do not send this prompt until every `TODO` is filled.**
The prompt is sent once and generated once, with no follow-up corrections.
After that, write `docs/deviation-log.md` before changing any code.

Waiting on:

- X1: the C.1 Component Specification. The C.1.4 requirements are due Friday
  at 14:00.
- B5: DO-04, the C.1.4 design output requirement. Due Friday at 18:00.
- B3/X0: the frozen A1 second-level IDEF0. A1.4's ICOMs come from it.

## Component Prompt Template

- **Context.** The Cornell Smart Parking Availability & Recommendation System
  recommends eligible parking areas for a Cornell driver's confirmed trip.
  It uses three pilot lots and simulated occupancy data, and it only supports
  decisions: it does not reserve spaces. This component is the last step of
  C.1 Parking Information Subsystem. It decides which pilot areas the trip
  may use, before forecasting (C.2) and ranking (C.3).
- **Component.** C.1.4 Eligibility Filter Module
- **Function performed.** A1.4 Determine Eligible Parking Areas
- **Requirements.** Quote each one verbatim with its identifier:
  - TODO: the C.1.4 functional requirement from the X1 C.1 spec
  - TODO: the C.1 interface and I/O requirements that touch A1.4's boundary
  - TODO: the flowed-down system-wide requirements that apply (X2)
  - TODO: DO-04 (B5), with its MOP and verification criteria
  - Parent stakeholder requirement SR-10 (SPEC.md), quoted verbatim from the
    SN-06 and SN-08 acceptance criteria
- **Interfaces.** Copy these from the frozen A1 second-level IDEF0. The rows
  below are provisional, taken from `contracts/api-v1.yaml`, and must be
  checked:
  - Input: the normalized six-field trip request (`TripRequest`, I-01).
    TODO: confirm whether validated parking data or the freshness status
    also enters A1.4.
  - Control: Parking Policy Constraints (`ParkingPolicyConstraints`, E-12,
    the rule table).
  - Output: Eligible Parking Areas (`EligibleParkingAreas`, I-05,
    `[{lot_id}]`).
  - Mechanism: C.1.4.
  - Error conditions: TODO.
- **Constraints.**
  - Python 3.13, standard library only.
  - One new module. Do not modify `contracts/`, the other A1–A6 modules,
    `parking_data_access/` or `language_model/`.
  - Local execution only. Performance limit: TODO, from DO-04's MOP.
- **Success criteria.** TODO: the requirement-derived tests and thresholds
  from DO-04's verification criteria. The component must also pass the SR-10
  part of `test_FR_1_4_1_prepares_eligible_parking_information`.
- **Output format.** A single Python file containing the function, plus one
  test file. No prose.
- **Out of scope.**
  - Do not add error handling, logging, caching or retries that no
    requirement asks for.
  - Do not refactor other modules.
  - Do not add dependencies.
  - Do not judge freshness (A1.3), forecast (A2) or rank (A3).
