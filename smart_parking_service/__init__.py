"""Smart Parking Service — the orchestration layer of the SoI.

Internal to the system-of-interest. The context diagram shows the Cornell
Smart Parking system as a single element; this module coordinates the UC.1
messages inside it, in the order of the updated UC.1 sequence diagram
(see docs/walking-skeleton.md).

Since Chapter 8, parking availability comes from the simulated X.C.2 feed
through the data access component, and trip interpretation goes through the
local language model adapter (docs/deployment.md). UC.1.10 and UC.1.11 run
through A1, UC.1.12 forecasts availability at arrival through A2 (ALT-F2,
SR-14), and UC.1.13 ranks through A3, which falls back to walking time when any
eligible area has no supported forecast (SR-13). UC.1.14 presents the result through A4.
"""

from datetime import date, datetime, timedelta

from contextual_information_sources import get_contextual_information, get_destinations
from estimate_arrival_time_availability import estimate_arrival_time_availability
from estimate_arrival_time_availability import warm_up as warm_up_forecast
from cornell_transportation_and_parking_services import get_parking_rules_and_closures, get_rule_table
from language_model import interpret_trip_request as model_interpret
from language_model import warm_up_model
from parking_availability_data_sources import get_lot_inventory
from parking_data_access import ParkingDataStore
from prepare_eligible_parking_information import InvalidTripRequest, prepare_eligible_parking_information
from present_parking_recommendations_and_status import present_parking_recommendations_and_status
from rank_parking_options import rank_parking_options
from stage_timing import stage

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
    "destinations": get_destinations(),  # the buildings in the walking-time table
    "vehicle_categories": ["sedan", "suv", "van"],
    "eligibility_values": ["permit_O", "visitor"],
}

TRIP_REQUEST_VALIDATION_RULES = {
    "arrival_window_minutes": 72 * 60,  # SPEC Data Contract section 5 (SR-12: 0-72 h)
    "supported_values": PROVISIONAL_SUPPORTED_VALUES,
}
INFORMATION_ACQUISITION_AND_REFRESH_RULES = {"refresh_interval_seconds": 60, "lot_ids": PILOT_LOT_IDS}  # C.1 Spec 2.3.2
DATA_VALIDATION_AND_FRESHNESS_RULES = {"stale_after_seconds": 120}  # SR-09
# SR-14: forecast only from an observation at most 120 s old; model grid below T_c.
FORECAST_VALIDITY_CRITERIA = {"max_observation_age_seconds": 120, "horizons_minutes": [0, 15, 30, 45, 60, 120]}
# SR-13: S = 0.40W + 0.40A + 0.20Q when every eligible area has a supported forecast.
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


def warm_up_forecast_model() -> None:
    """Load the forecast model and occupancy history before the first driver (A2)."""
    warm_up_forecast()


def warm_up_language_model() -> bool:
    """Load the local model with the product's own prompt before the first driver (keep_alive in language_model)."""
    return warm_up_model(PROVISIONAL_SUPPORTED_VALUES)


def find_suitable_parking(trip_request: dict) -> dict:
    """UC.1.4-UC.1.14: gather inputs, run A1, A2 and A3, and return recommendations."""
    submitted_at = _now()
    # UC.1.4-UC.1.9: request and receive data from the three external sources.
    with stage("X.C.2.availability"):
        availability = _store().request_parking_availability({"lot_ids": PILOT_LOT_IDS, "as_of": submitted_at})
    with stage("X.C.3.context"):
        context = get_contextual_information(trip_request.get("destination"))
    with stage("X.C.4.rules"):
        rules = get_parking_rules_and_closures(
            trip_request.get("declared_eligibility"), trip_request.get("access_needs")
        )

    # UC.1.10-UC.1.11: A1 validates the data and filters the areas.
    try:
        with stage("C.1.prepare"):
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

    # UC.1.12: A2 forecasts free spaces at the arrival time (SR-14).
    with stage("C.2.estimate"):
        forecast = estimate_arrival_time_availability(
            prepared["validated_parking_data"],
            prepared["normalized_trip_requirements"],
            prepared["validated_context_information"],
            prepared["eligible_parking_areas"],
            prepared["data_quality_and_freshness_status"],
            forecast_validity_criteria=FORECAST_VALIDITY_CRITERIA,
        )
    # R-04 guardrail: an estimate reaches ranking and display only if it is the
    # supported forecast for this lot, this trip and a still-current observation.
    with stage("C.0.forecast_guard"):
        forecast = guard_forecasts(forecast, prepared["normalized_trip_requirements"],
                                   prepared["eligible_parking_areas"], prepared["validated_parking_data"],
                                   prepared["data_quality_and_freshness_status"],
                                   datetime.now().astimezone())

    # UC.1.13: A3 ranks; without a supported forecast for every area it uses walking time.
    with stage("C.3.rank"):
        ranked = rank_parking_options(
            prepared["normalized_trip_requirements"],
            prepared["validated_context_information"],
            prepared["eligible_parking_areas"],
            prepared["data_quality_and_freshness_status"],
            forecast["arrival_time_availability_estimates"],
            forecast["forecast_validity_status"],
            ranking_and_fallback_rules=RANKING_AND_FALLBACK_RULES,
        )
    # UC.1.14: A4 presents the options with explanations derived by the
    # application from the factors the ranking used (ADR-0002, SR-13, SR-15).
    with stage("C.4.present"):
        presented = present_parking_recommendations_and_status(
            {}, {}, {},
            prepared["validated_parking_data"],
            prepared["normalized_trip_requirements"],
            prepared["validated_context_information"],
            prepared["eligible_parking_areas"],
            prepared["data_quality_and_freshness_status"],
            forecast["arrival_time_availability_estimates"],
            forecast["forecast_validity_status"],
            ranked,
            authorization_decision={"permitted": False},  # no trip record is stored in the pilot
            parking_policy_constraints=rules,
            presentation_and_explanation_rules=DATA_VALIDATION_AND_FRESHNESS_RULES,
        )

    return {
        "destination": trip_request["destination"],
        "ranked_options": presented["ranked_parking_recommendations"],
        "advisory_notice": presented["advisory_notice"],
        # The confirmed request is echoed back so the driver can re-check it on the
        # results screen (A4 receives Normalized Trip Requirements, flow 9.13).
        "trip_summary": presented["trip_summary"],
        "data_mode": "synthetic",
        "ranking_basis": ranked[0]["ranking_basis"] if ranked else None,
        "a1_outputs": _a1_outputs(prepared),
    }


def guard_forecasts(forecast: dict, normalized_trip_requirements: dict, eligible_parking_areas: list[dict],
                    validated_parking_data: list[dict], data_quality_and_freshness_status: dict,
                    now: datetime) -> dict:
    """R-04 guardrail (docs/risks.md): withhold any A2 estimate that ranking or display must not use.

    Runs between A2 and A3, so A3 and the page see only estimates that pass.
    An estimate is kept only if all of these hold; otherwise the lot is marked
    "unsupported" and A3 falls back to walking time (SR-13):
      - A2 marked the lot "supported", the lot is eligible, and A2 returned exactly one estimate for it;
      - the values are whole numbers with 0 <= lower <= estimate <= upper <= capacity,
        the capacity is the observed one, and the interval level is 80%;
      - the estimate is for this trip's arrival time, made from this lot's observation,
        with a lead time of 0-72 h;
      - the observation is still "current" and, rechecked now, at most 120 s old (SR-14:
        recheck freshness before display).
    Returns {"arrival_time_availability_estimates", "forecast_validity_status", "withheld"},
    where "withheld" maps each withheld lot to the first failed check.
    """
    status = dict(forecast.get("forecast_validity_status") or {})
    eligible = {area["lot_id"] for area in eligible_parking_areas}
    observed = {lot["lot_id"]: lot for lot in validated_parking_data}
    arrival = _aware(normalized_trip_requirements.get("arrival_time"))
    by_lot = {}
    for estimate in forecast.get("arrival_time_availability_estimates") or []:
        lot_id = estimate.get("lot_id") if isinstance(estimate, dict) else None
        by_lot.setdefault(lot_id, []).append(estimate)

    kept, withheld = [], {}
    for lot_id in sorted(eligible | {k for k in by_lot if isinstance(k, str)}):
        reason = _forecast_problem(lot_id, status.get(lot_id), by_lot.get(lot_id, []), lot_id in eligible,
                                   observed.get(lot_id), data_quality_and_freshness_status.get(lot_id),
                                   arrival, now)
        if reason is None:
            kept.append(by_lot[lot_id][0])
        else:
            if lot_id in status or lot_id in eligible:
                status[lot_id] = "unsupported"
            if reason != "not_supported":
                withheld[lot_id] = reason
    return {"arrival_time_availability_estimates": kept, "forecast_validity_status": status,
            "withheld": withheld}


def _forecast_problem(lot_id, status, estimates, is_eligible, lot, freshness, arrival, now) -> str | None:
    """The first check an estimate fails, or None if ranking and display may use it."""
    if not estimates or status != "supported":
        return "not_supported" if not estimates else "status_not_supported"
    if not is_eligible:
        return "lot_not_eligible"
    if len(estimates) != 1:
        return "duplicate_estimates"
    e = estimates[0]
    numbers = [e.get(k) for k in ("capacity", "available_spaces", "interval_lower", "interval_upper")]
    if not all(isinstance(n, int) and not isinstance(n, bool) for n in numbers):
        return "not_whole_numbers"
    capacity, available, lower, upper = numbers
    if not 0 <= lower <= available <= upper <= capacity or capacity <= 0:
        return "bounds_inconsistent"
    if e.get("interval_level") != 0.8:
        return "wrong_interval_level"
    if lot is None or capacity != lot.get("capacity"):
        return "capacity_mismatch"
    if arrival is None or _aware(e.get("arrival_time")) != arrival:
        return "other_arrival_time"
    forecast_time = _aware(e.get("forecast_time"))
    observed_at = _aware(lot.get("observed_at"))
    if forecast_time is None or forecast_time != observed_at:
        return "other_observation"
    if not timedelta(0) <= arrival - forecast_time <= timedelta(hours=72):
        return "lead_out_of_range"
    if freshness != "current":
        return "observation_not_current"
    age = (now - observed_at).total_seconds()
    if age > FORECAST_VALIDITY_CRITERIA["max_observation_age_seconds"]:
        return "observation_aged_before_display"
    return None


def _aware(value) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


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
