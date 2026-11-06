"""Smart Parking Service — the orchestration layer of the SoI.

Internal to the system-of-interest. The context diagram shows the Cornell
Smart Parking system as a single element; this module coordinates the UC.1
messages inside it, in the order of the updated UC.1 sequence diagram
(see docs/walking-skeleton.md).

Since Chapter 8, parking availability comes from the simulated X.C.2 feed
through the data access component, and trip interpretation goes through the
local language model adapter (docs/deployment.md). UC.1.10 and UC.1.11 run
through A1, and UC.1.13 ranks through A3. A2 is not implemented, so no forecast
exists and A3 uses its walking-time fallback (SR-13). A4 is not implemented
either, so this module still builds the driver-facing result.
"""

from datetime import date, datetime, timedelta

from contextual_information_sources import get_contextual_information
from cornell_transportation_and_parking_services import get_parking_rules_and_closures, get_rule_table
from language_model import interpret_trip_request as model_interpret
from parking_availability_data_sources import get_lot_inventory
from parking_data_access import ParkingDataStore
from prepare_eligible_parking_information import InvalidTripRequest, prepare_eligible_parking_information
from rank_parking_options import rank_parking_options

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

TRIP_REQUEST_VALIDATION_RULES = {
    "arrival_window_minutes": 60,  # SPEC Data Contract section 5
    "supported_values": PROVISIONAL_SUPPORTED_VALUES,
}
INFORMATION_ACQUISITION_AND_REFRESH_RULES = {"refresh_interval_seconds": 60, "lot_ids": PILOT_LOT_IDS}  # C.1 Spec 2.3.2
DATA_VALIDATION_AND_FRESHNESS_RULES = {"stale_after_seconds": 120}  # SR-09
# SR-13. No forecast exists yet, so A3 uses its walking-time fallback.
RANKING_AND_FALLBACK_RULES = {"weights": {"walking_time": 0.4, "availability": 0.4, "uncertainty": 0.2}}

LIVE_ROUNDS = 36          # three hours of 5-minute rounds on the live status page
LIVE_ROUND_MINUTES = 5

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
        return {"status": "incomplete", "trip_request": response["trip_request"],
                "missing_fields": response["missing_fields"]}
    return {"status": "form_required", "trip_request": {}, "missing_fields": list(REQUIRED_FIELDS)}


def find_suitable_parking(trip_request: dict) -> dict:
    """UC.1.4-UC.1.14: gather inputs, run A1 and A3, and return recommendations."""
    submitted_at = _now()
    # UC.1.4-UC.1.9: request and receive data from the three external sources.
    availability = _store().request_parking_availability({"lot_ids": PILOT_LOT_IDS, "as_of": submitted_at})
    context = get_contextual_information(trip_request.get("destination"))
    rules = get_parking_rules_and_closures(
        trip_request.get("declared_eligibility"), trip_request.get("access_needs")
    )

    # UC.1.10-UC.1.11: A1 validates the data and filters the areas.
    try:
        prepared = prepare_eligible_parking_information(
            {"message": "", "submitted_at": submitted_at},
            trip_request,
            {},
            availability,
            {},
            context,
            {},
            trip_request_validation_rules=TRIP_REQUEST_VALIDATION_RULES,
            information_acquisition_and_refresh_rules=INFORMATION_ACQUISITION_AND_REFRESH_RULES,
            data_validation_and_freshness_rules=DATA_VALIDATION_AND_FRESHNESS_RULES,
            parking_policy_constraints=rules,
            authorization_decision={"permitted": False},  # A1 performs no protected record operation.
        )
    except InvalidTripRequest as error:
        # SR-12: an invalid request blocks the recommendation until corrected.
        return {"status": "invalid_trip_request", "reason": str(error), "ranked_options": []}

    # UC.1.13: A3 ranks. A2 is not implemented, so no area has a forecast.
    ranked = rank_parking_options(
        prepared["normalized_trip_requirements"],
        prepared["validated_context_information"],
        prepared["eligible_parking_areas"],
        prepared["data_quality_and_freshness_status"],
        [],
        {},
        ranking_and_fallback_rules=RANKING_AND_FALLBACK_RULES,
    )
    observed = {lot["lot_id"]: lot for lot in prepared["validated_parking_data"]}
    freshness = prepared["data_quality_and_freshness_status"]

    # UC.1.14: the application, not the language model, derives each
    # explanation from the factors it used (ADR-0002, SR-13, SR-15).
    ranked_options = []
    for rank, (option, role) in enumerate(zip(ranked, ("primary", "backup")), start=1):
        lot = observed[option["lot_id"]]
        available = lot["capacity"] - lot["occupied"]
        ranked_options.append({
            "rank": rank,
            "role": role,
            "lot_id": option["lot_id"],
            "available_spaces": available,
            "walking_time_minutes": option["walking_time_minutes"],
            "ranking_basis": option["ranking_basis"],
            "stale": freshness[option["lot_id"]] == "stale",
            "explanation": (
                f"{option['lot_id']} is eligible for {trip_request['declared_eligibility']}, "
                f"{option['walking_time_minutes']} min walk, "
                f"{available} spaces observed now (synthetic). "
                "Forecasts are unavailable, so options are ranked by walking time."
            ),
        })

    # The confirmed request is echoed back so the driver can re-check it on the
    # results screen (A4 receives Normalized Trip Requirements, flow 9.13).
    trip_summary = {field: trip_request[field] for field in REQUIRED_FIELDS}

    return {
        "destination": trip_request["destination"],
        "ranked_options": ranked_options,
        "trip_summary": trip_summary,
        "data_mode": "synthetic",
        "a1_outputs": _a1_outputs(prepared),
    }


def _a1_outputs(prepared: dict) -> dict:
    """What A1.2-A1.4 produced for this trip, for the driver interface to show."""
    eligible = {area["lot_id"] for area in prepared["eligible_parking_areas"]}
    return {
        "lot_names": {lot["lot_id"]: lot["name"] for lot in get_lot_inventory()},
        "availability_data_request": prepared["availability_data_request"],  # A1.2
        "context_data_request": prepared["context_data_request"],
        "parking_policy_request": prepared["parking_policy_request"],
        "validated_parking_data": prepared["validated_parking_data"],  # A1.3
        "data_quality_and_freshness_status": prepared["data_quality_and_freshness_status"],
        "eligible_lot_ids": [lot_id for lot_id in PILOT_LOT_IDS if lot_id in eligible],  # A1.4
        "excluded_lot_ids": [lot_id for lot_id in PILOT_LOT_IDS if lot_id not in eligible],
    }


def _closed_lots(at: datetime) -> list[str]:
    """Lots with a confirmed closure rule in force at this moment."""
    closed = []
    for rule in get_rule_table()["rules"]:
        in_dates = date.fromisoformat(rule["valid_from"]) <= at.date() <= date.fromisoformat(rule["valid_until"])
        in_hours = rule["start_local_time"] <= at.strftime("%H:%M") < rule["end_local_time"]
        if rule["closure"] and in_dates and at.isoweekday() in rule["days_of_week"] and in_hours:
            closed.append(rule["lot_id"])
    return closed


def get_live_parking_status() -> dict:
    """SR-08: timestamped current parking information, with the last three hours of rounds.

    Each round holds one digit per space, in space_id order: 1 occupied, 0 vacant.
    """
    now = datetime.fromisoformat(_now())
    rounds = []
    for back in range(LIVE_ROUNDS - 1, -1, -1):
        at = now - timedelta(minutes=LIVE_ROUND_MINUTES * back)
        events = _store().request_parking_availability({"lot_ids": PILOT_LOT_IDS, "as_of": at.isoformat()})
        spaces = {}
        for event in events:
            digit = "1" if event["status"] == "occupied" else "0"
            zones = spaces.setdefault(event["lot_id"], {})
            zones[event["zone"]] = zones.get(event["zone"], "") + digit
        rounds.append({"as_of": at.isoformat(), "closed_lot_ids": _closed_lots(at), "spaces": spaces})
    return {
        "lot_names": {lot["lot_id"]: lot["name"] for lot in get_lot_inventory()},
        "round_minutes": LIVE_ROUND_MINUTES,
        "rounds": rounds,
        "data_mode": "simulated",
    }


def get_trip_form_options() -> dict:
    """The values the six-field confirmation form offers."""
    return PROVISIONAL_SUPPORTED_VALUES


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
