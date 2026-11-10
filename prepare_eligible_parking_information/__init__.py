"""A1 -- Prepare Eligible Parking Information.

Implements first-level IDEF0 function A1 of A0 Provide Parking Decision
Support. A1 is decomposed in the model into A1.1 Interpret and Confirm Parking
Requests, A1.2 Request Parking, Context, and Policy Information, A1.3 Validate
Parking and Context Information, and A1.4 Determine Eligible Parking Areas;
this module implements A1 at its boundary and calls one module per subfunction.

Mechanism: C.1 Parking Information Subsystem, with modules C.1.1 to C.1.4
performing A1.1 to A1.4 (docs/deployment.md). Requirement: 1.4.1.

Signature from the ICOMs. Conforms to contracts/api-v1.yaml
(prepareEligibleParkingInformation) since Chapter 7; see
docs/adr/0003-internal-interface-contract.md.
"""

from prepare_eligible_parking_information.determine_eligible_parking_areas import (
    determine_eligible_parking_areas,
)
from prepare_eligible_parking_information.interpret_and_confirm_parking_requests import (
    InvalidTripRequest,
    interpret_and_confirm_parking_requests,
)
from prepare_eligible_parking_information.request_parking_context_and_policy_information import (
    request_parking_context_and_policy_information,
)
from prepare_eligible_parking_information.validate_parking_and_context_information import (
    validate_parking_and_context_information,
)

__all__ = ["InvalidTripRequest", "prepare_eligible_parking_information"]


def prepare_eligible_parking_information(
    trip_information_and_parking_request: dict,
    confirmed_trip_requirements: dict,
    status_recheck_request: dict,
    parking_availability_data: list[dict],
    updated_parking_availability: dict,
    contextual_information: list[dict],
    personal_record_disposition_result: dict,
    *,
    trip_request_validation_rules: dict,
    information_acquisition_and_refresh_rules: dict,
    data_validation_and_freshness_rules: dict,
    parking_policy_constraints: dict,
    authorization_decision: dict,
) -> dict:
    """in: trip_information_and_parking_request (Cornell Driver),
    confirmed_trip_requirements (Cornell Driver),
    status_recheck_request (Cornell Driver),
    parking_availability_data (Parking Availability Data Sources),
    updated_parking_availability (Parking Availability Data Sources),
    contextual_information (Contextual Information Sources),
    personal_record_disposition_result (A6).
    control: trip_request_validation_rules,
    information_acquisition_and_refresh_rules,
    data_validation_and_freshness_rules, parking_policy_constraints,
    authorization_decision (A5).
    out: interpreted_trip_summary (Cornell Driver),
    availability_data_request (Parking Availability Data Sources),
    context_data_request (Contextual Information Sources),
    parking_policy_request (Cornell Transportation and Parking Services),
    updated_availability_request (Parking Availability Data Sources),
    normalized_trip_requirements (A2, A3, A4),
    validated_parking_data (A2, A4),
    validated_context_information (A2, A3, A4),
    data_quality_and_freshness_status (A2, A3, A4),
    eligible_parking_areas (A2, A3, A4),
    protected_data_operation_request (A5),
    personal_records_and_retention_metadata (A6).

    Before the driver confirms, only interpreted_trip_summary carries a result.
    The current build stores no trip record (docs/trip-record-data.md), so
    personal_records_and_retention_metadata is empty, no protected operation is
    requested, and authorization_decision and personal_record_disposition_result
    change nothing. Raises InvalidTripRequest for an invalid confirmed request
    (contract 422).
    """
    submitted_at = trip_information_and_parking_request.get("submitted_at")
    interpretation = interpret_and_confirm_parking_requests(  # A1.1
        trip_information_and_parking_request,
        confirmed_trip_requirements,
        trip_request_validation_rules=trip_request_validation_rules,
    )
    normalized = interpretation.get("normalized_trip_requirements")
    if normalized is None:
        return {
            "interpreted_trip_summary": interpretation["interpreted_trip_summary"],
            "normalized_trip_requirements": {},
            "validated_parking_data": [],
            "validated_context_information": [],
            "data_quality_and_freshness_status": {},
            "eligible_parking_areas": [],
            "personal_records_and_retention_metadata": [],
        }

    requests = request_parking_context_and_policy_information(  # A1.2
        normalized,
        status_recheck_request,
        information_acquisition_and_refresh_rules=information_acquisition_and_refresh_rules,
        requested_at=submitted_at,
    )
    validated = validate_parking_and_context_information(  # A1.3
        normalized,
        parking_availability_data,
        updated_parking_availability,
        contextual_information,
        data_validation_and_freshness_rules=data_validation_and_freshness_rules,
        parking_policy_constraints=parking_policy_constraints,
        decision_time=submitted_at,
    )
    eligible = determine_eligible_parking_areas(  # A1.4
        validated["validated_parking_data"],
        normalized,
        validated["validated_context_information"],
        validated["data_quality_and_freshness_status"],
        parking_policy_constraints=parking_policy_constraints,
    )
    return {
        **requests,
        "normalized_trip_requirements": normalized,
        **validated,
        "eligible_parking_areas": eligible,
        "personal_records_and_retention_metadata": [],
    }
