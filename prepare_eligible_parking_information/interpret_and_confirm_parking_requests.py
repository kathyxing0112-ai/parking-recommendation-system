"""C.1.1 Trip Request Interpretation Module -- A1.1 Interpret and Confirm Parking Requests.

Requirements: C.1 Spec 1.4.1; DO-01; SR-12; SPEC Data Contract section 5. The
language model only proposes values through language_model (ADR-0002). Only
values the driver confirmed, and that pass the Trip Request Validation Rules,
leave this module as Normalized Trip Requirements.
"""

from datetime import datetime, timedelta

from language_model import interpret_trip_request

REQUIRED_FIELDS = (
    "destination",
    "arrival_time",
    "departure_time",
    "vehicle_category",
    "declared_eligibility",
    "access_needs",
)
# supported_values key for each field checked against an approved list.
LISTED_FIELDS = {
    "destination": "destinations",
    "vehicle_category": "vehicle_categories",
    "declared_eligibility": "eligibility_values",
}


class InvalidTripRequest(ValueError):
    """A required trip field is missing or invalid (contract 422, SR-12)."""


def _offset_aware(value, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise InvalidTripRequest(f"{field} is not an ISO 8601 time") from None
    if parsed.tzinfo is None:
        raise InvalidTripRequest(f"{field} has no UTC offset")
    return parsed


def _normalize(confirmed: dict, submitted_at: str, rules: dict) -> dict:
    missing = [field for field in REQUIRED_FIELDS if field not in confirmed]
    if missing:
        raise InvalidTripRequest(f"missing fields: {', '.join(missing)}")
    for field, list_key in LISTED_FIELDS.items():
        allowed = rules.get("supported_values", {}).get(list_key)
        if allowed is not None and confirmed[field] not in allowed:
            raise InvalidTripRequest(f"{field} is not a supported value")
        if not isinstance(confirmed[field], str) or not confirmed[field]:
            raise InvalidTripRequest(f"{field} is empty")
    if not isinstance(confirmed["access_needs"], bool):
        raise InvalidTripRequest("access_needs is not true or false")

    submitted = _offset_aware(submitted_at, "submitted_at").replace(second=0, microsecond=0)
    arrival = _offset_aware(confirmed["arrival_time"], "arrival_time")
    departure = _offset_aware(confirmed["departure_time"], "departure_time")
    window = timedelta(minutes=rules["arrival_window_minutes"])
    if not submitted <= arrival <= submitted + window:
        raise InvalidTripRequest("arrival_time is outside the arrival window")
    if departure <= arrival:
        raise InvalidTripRequest("departure_time is not later than arrival_time")
    return {field: confirmed[field] for field in REQUIRED_FIELDS}


def interpret_and_confirm_parking_requests(
    trip_information_and_parking_request: dict,
    confirmed_trip_requirements: dict,
    *,
    trip_request_validation_rules: dict,
) -> dict:
    """A1.1: interpret a message, or normalize the request the driver confirmed.

    in: trip_information_and_parking_request ({"message", "submitted_at"}),
    confirmed_trip_requirements (the six fields; empty until the driver confirms).
    control: trip_request_validation_rules ({"arrival_window_minutes"}, optional
    {"supported_values"}).
    out: {"interpreted_trip_summary"} before confirmation, or
    {"normalized_trip_requirements"} after it. Raises InvalidTripRequest when a
    confirmed request fails the rules.
    """
    submitted_at = trip_information_and_parking_request.get("submitted_at")
    if confirmed_trip_requirements:
        return {
            "normalized_trip_requirements": _normalize(
                confirmed_trip_requirements, submitted_at, trip_request_validation_rules)
        }
    supported_values = trip_request_validation_rules.get("supported_values")
    if supported_values is None:
        return {"interpreted_trip_summary": {"status": "fallback", "reason": "no_supported_values"}}
    return {
        "interpreted_trip_summary": interpret_trip_request(
            trip_information_and_parking_request.get("message", ""),
            submitted_at=submitted_at,
            supported_values=supported_values,
        )
    }
