"""Smart Parking Service — the orchestration layer of the SoI.

Internal to the system-of-interest. The context diagram shows the Cornell
Smart Parking system as a single element; this module coordinates the UC.1
messages inside it, in the order of the updated UC.1 sequence diagram
(see docs/walking-skeleton.md).

Internal Actions UC.1.10-UC.1.13 are placeholders: no validation, filtering,
forecasting, or scoring is computed in this increment.
"""

from contextual_information_sources import get_contextual_information
from cornell_transportation_and_parking_services import get_parking_rules_and_closures
from language_model import interpret_trip_request as model_interpret
from parking_availability_data_sources import (
    get_current_parking_availability,
    get_updated_parking_availability,
)

REQUIRED_FIELDS = (
    "destination",
    "arrival_time",
    "departure_time",
    "vehicle_category",
    "declared_eligibility",
    "access_needs",
)


def interpret_trip_request(message: str) -> dict:
    """UC.1.2 Interpret and Confirm Trip Request.

    The language model interprets the message (ADR-0002); the application
    checks that all six required fields are present before asking the driver
    to confirm them.
    """
    response = model_interpret(message)
    trip_request = response.get("trip_request", {})
    missing = [f for f in REQUIRED_FIELDS if f not in trip_request]
    return {"status": "incomplete" if missing else "complete",
            "trip_request": trip_request, "missing_fields": missing}


def find_suitable_parking(trip_request: dict) -> dict:
    """UC.1.4-UC.1.14: gather inputs, rank options, and return recommendations."""
    # UC.1.4-UC.1.9: request and receive data from the three external sources.
    availability = get_current_parking_availability(trip_request["destination"])
    context = get_contextual_information(trip_request["destination"])
    rules = get_parking_rules_and_closures(
        trip_request["declared_eligibility"], trip_request["access_needs"]
    )

    # UC.1.10-UC.1.13 placeholder: a hard-coded primary and backup option of
    # the shape SR-13 asks for. No ranking is computed from the inputs above.
    ranked_options = [
        {"rank": 1, "role": "primary", "lot_id": "LOT-1", "available_spaces": 10, "walking_time_minutes": 5},
        {"rank": 2, "role": "backup", "lot_id": "LOT-2", "available_spaces": 4, "walking_time_minutes": 9},
    ]

    # UC.1.14: the application, not the language model, derives each
    # explanation from the factors it used (ADR-0002, SR-15).
    for option in ranked_options:
        option["explanation"] = (
            f"{option['lot_id']} is eligible for {trip_request['declared_eligibility']}, "
            f"{option['walking_time_minutes']} min walk, "
            f"{option['available_spaces']} spaces observed (synthetic)."
        )

    # The confirmed request is echoed back so the driver can re-check it on the
    # results screen (A4 receives Normalized Trip Requirements, flow 9.13).
    trip_summary = {field: trip_request[field] for field in REQUIRED_FIELDS}

    return {
        "destination": trip_request["destination"],
        "ranked_options": ranked_options,
        "trip_summary": trip_summary,
        "data_mode": "synthetic",
    }


def get_selected_parking_information(recommendations: dict, lot_id: str) -> dict:
    """UC.1.17 Present Selected Parking Information."""
    for option in recommendations["ranked_options"]:
        if option["lot_id"] == lot_id:
            return option
    raise ValueError(f"{lot_id} was not among the returned options")


def recheck_parking_status(lot_id: str) -> dict:
    """UC.1.18-UC.1.21: pre-arrival recheck of the selected option."""
    updated = get_updated_parking_availability(lot_id)  # UC.1.19 / UC.1.20
    return {**updated, "data_mode": "synthetic"}      # UC.1.21
