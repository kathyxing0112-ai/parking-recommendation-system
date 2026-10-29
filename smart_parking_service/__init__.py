"""Smart Parking Service — the orchestration layer of the SoI.

Internal to the system-of-interest. The context diagram shows the Cornell
Smart Parking system as a single element; this module coordinates the UC.1
messages inside it, in the order of the updated UC.1 sequence diagram
(see docs/walking-skeleton.md).

Since Chapter 8, parking availability comes from the simulated X.C.2 feed
through the data access component, and trip interpretation goes through the
local language model adapter (docs/deployment.md). Internal Actions
UC.1.10-UC.1.13 are still placeholders: no validation, filtering,
forecasting, or scoring is computed in this increment.
"""

from datetime import datetime

from contextual_information_sources import get_contextual_information
from cornell_transportation_and_parking_services import get_parking_rules_and_closures
from language_model import interpret_trip_request as model_interpret
from parking_data_access import ParkingDataStore

REQUIRED_FIELDS = (
    "destination",
    "arrival_time",
    "departure_time",
    "vehicle_category",
    "declared_eligibility",
    "access_needs",
)

PILOT_LOT_IDS = ["LOT-1", "LOT-2", "LOT-3"]

# Provisional values the application gives the model (Model Response Contract).
# The approved lists are still open (prompt-log 2026-10-04, deferred item 3).
PROVISIONAL_SUPPORTED_VALUES = {
    "destinations": ["Duffield Hall", "Upson Hall", "Gates Hall"],
    "vehicle_categories": ["sedan", "suv", "van"],
    "eligibility_values": ["permit_O", "visitor"],
}

_data_store = None


def _store() -> ParkingDataStore:
    global _data_store
    if _data_store is None:
        _data_store = ParkingDataStore()
    return _data_store


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def interpret_trip_request(message: str) -> dict:
    """UC.1.2 Interpret and Confirm Trip Request.

    The language model interprets the message through the adapter (ADR-0002),
    which has already checked the output against the Model Response Contract.
    A "fallback" result means the model output was discarded: the driver is
    shown the six-field form instead, with no raw output or internal error.
    """
    response = model_interpret(message, submitted_at=_now(),
                               supported_values=PROVISIONAL_SUPPORTED_VALUES)
    if response["status"] == "complete":
        return {"status": "complete", "trip_request": response["trip_request"], "missing_fields": []}
    if response["status"] == "incomplete":
        return {"status": "incomplete", "trip_request": {}, "missing_fields": response["missing_fields"]}
    return {"status": "form_required", "trip_request": {}, "missing_fields": list(REQUIRED_FIELDS)}


def find_suitable_parking(trip_request: dict) -> dict:
    """UC.1.4-UC.1.14: gather inputs, rank options, and return recommendations."""
    # UC.1.4-UC.1.9: request and receive data from the three external sources.
    availability = _store().request_parking_availability(
        {"lot_ids": PILOT_LOT_IDS, "as_of": _now()}
    )
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
    updated = _store().request_updated_parking_availability(  # UC.1.19 / UC.1.20
        {"lot_id": lot_id, "as_of": _now()}
    )
    return {**updated, "data_mode": "simulated"}  # UC.1.21
