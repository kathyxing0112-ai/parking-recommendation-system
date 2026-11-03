"""C.1.2 External Data Acquisition Module -- A1.2 Request Parking, Context, and Policy Information.

Requirements: C.1 Spec 1.4.2 and 2.3.2; DO-02. One availability, one context
and one policy request for each confirmed trip, and one updated availability
request for each status recheck. parking_data_access answers the availability
requests.
"""


def request_parking_context_and_policy_information(
    normalized_trip_requirements: dict,
    status_recheck_request: dict,
    *,
    information_acquisition_and_refresh_rules: dict,
    requested_at: str,
) -> dict:
    """A1.2: the requests for one confirmed trip, or for one status recheck.

    in: normalized_trip_requirements (A1.1), status_recheck_request ({"lot_id"};
    empty when no recheck is in progress).
    control: information_acquisition_and_refresh_rules
    ({"refresh_interval_seconds"}, optional {"lot_ids"}).
    requested_at: offset-aware ISO 8601 time the requests are made.
    out: availability_data_request, context_data_request, parking_policy_request,
    or updated_availability_request.
    """
    if status_recheck_request:
        return {
            "updated_availability_request": {
                "lot_id": status_recheck_request["lot_id"],
                "as_of": requested_at,
            }
        }
    return {
        "availability_data_request": {
            "lot_ids": information_acquisition_and_refresh_rules.get("lot_ids", []),
            "as_of": requested_at,
            "refresh_interval_seconds": information_acquisition_and_refresh_rules["refresh_interval_seconds"],
        },
        "context_data_request": {"destination": normalized_trip_requirements["destination"]},
        "parking_policy_request": {
            "declared_eligibility": normalized_trip_requirements["declared_eligibility"],
            "access_needs": normalized_trip_requirements["access_needs"],
        },
    }
