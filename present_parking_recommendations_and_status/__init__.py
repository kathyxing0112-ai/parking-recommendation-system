"""A4 -- Present Parking Recommendations and Status.

Implements first-level IDEF0 function A4 of A0 Provide Parking Decision
Support.

Mechanism: C.0 Cornell Smart Parking Availability & Recommendation System
(the system itself), so no dependency is injected.

A4 turns A3's ranking into what the driver sees (UC.1.14, UC.1.17, UC.1.21):
the primary and backup options with an explanation built only from the factors
the ranking used (SR-15), the stale label and last-observed time (SR-09), a
forecast only where A2 marked it supported (C.4 part of the R-04 plan), and an
advisory notice that no space is reserved or guaranteed (SR-13).
"""


def present_parking_recommendations_and_status(
    personal_record_disposition_result: dict,
    selected_parking_option: dict,
    status_recheck_request: dict,
    validated_parking_data: list[dict],
    normalized_trip_requirements: dict,
    validated_context_information: list[dict],
    eligible_parking_areas: list[dict],
    data_quality_and_freshness_status: dict,
    arrival_time_availability_estimates: list[dict],
    forecast_validity_status: dict,
    ranked_parking_options: list[dict],
    *,
    authorization_decision: dict,
    parking_policy_constraints: dict,
    presentation_and_explanation_rules: dict,
) -> dict:
    """in: personal_record_disposition_result (A6),
    selected_parking_option (Cornell Driver),
    status_recheck_request (Cornell Driver), validated_parking_data (A1),
    normalized_trip_requirements (A1), validated_context_information (A1),
    eligible_parking_areas (A1), data_quality_and_freshness_status (A1),
    arrival_time_availability_estimates (A2), forecast_validity_status (A2),
    ranked_parking_options (A3).
    control: authorization_decision (A5), parking_policy_constraints,
    presentation_and_explanation_rules.
    out: protected_data_operation_request (A5),
    updated_parking_status (Cornell Driver),
    ranked_parking_recommendations (Cornell Driver),
    selected_parking_information (Cornell Driver).
    """
    observed = {lot["lot_id"]: lot for lot in validated_parking_data}
    estimates = {e["lot_id"]: e for e in arrival_time_availability_estimates
                 if forecast_validity_status.get(e["lot_id"]) == "supported"}

    recommendations = []
    for rank, (option, role) in enumerate(zip(ranked_parking_options, ("primary", "backup")), start=1):
        lot = observed[option["lot_id"]]
        available = lot["capacity"] - lot["occupied"]
        estimate = estimates.get(option["lot_id"])
        recommendations.append({
            "rank": rank,
            "role": role,
            "lot_id": option["lot_id"],
            "available_spaces": available,
            "walking_time_minutes": option["walking_time_minutes"],
            "ranking_basis": option["ranking_basis"],
            "stale": data_quality_and_freshness_status.get(option["lot_id"]) != "current",
            "last_observed_at": lot["observed_at"],
            "forecast": _forecast_summary(estimate),
            "explanation": _explanation(option, normalized_trip_requirements, available, estimate),
        })

    return {
        "ranked_parking_recommendations": recommendations,
        "advisory_notice": ADVISORY_NOTICE if recommendations else NO_OPTION_NOTICE,
        "trip_summary": {field: normalized_trip_requirements[field]
                         for field in TRIP_FIELDS if field in normalized_trip_requirements},
        "selected_parking_information": _selected(recommendations, selected_parking_option),
        "updated_parking_status": _updated_status(observed, data_quality_and_freshness_status,
                                                  status_recheck_request),
        # No trip record is stored in the pilot, so A4 asks A5 for nothing.
        "protected_data_operation_request": None,
    }


ADVISORY_NOTICE = ("Advice only: spaces are not reserved or guaranteed, and availability can change "
                   "before you arrive.")
NO_OPTION_NOTICE = "No confirmed eligible parking option is available for this trip (SR-13)."
TRIP_FIELDS = ("destination", "arrival_time", "departure_time", "vehicle_category",
               "declared_eligibility", "access_needs")


def _forecast_summary(estimate: dict | None) -> dict | None:
    """What the driver sees of a supported A2 estimate for one option."""
    if estimate is None:
        return None
    return {key: estimate[key] for key in ("available_spaces", "interval_lower", "interval_upper",
                                           "interval_level", "lead_minutes", "method", "long_range")}


def _explanation(option: dict, trip: dict, available_now: int, estimate: dict | None) -> str:
    """UC.1.14: the explanation names only the factors the ranking used (SR-15)."""
    text = (f"{option['lot_id']} is eligible for {trip['declared_eligibility']}, "
            f"{option['walking_time_minutes']} min walk, {available_now} spaces observed now (synthetic).")
    if option["ranking_basis"] == "score" and estimate is not None:
        text += (f" Forecast at arrival: about {estimate['available_spaces']} free "
                 f"(80% range {estimate['interval_lower']}-{estimate['interval_upper']}). "
                 "Ranked by walking time, forecast free spaces and forecast certainty.")
        if estimate["long_range"]:
            text += " Arrival is 3 h or more away, so the forecast is the usual level for that day and time: for reference only."
        return text
    return text + " A forecast is unavailable for at least one eligible lot, so options are ranked by walking time."


def _selected(recommendations: list[dict], selected_parking_option: dict) -> dict | None:
    """UC.1.17: the details of the option the driver chose, if any."""
    lot_id = (selected_parking_option or {}).get("lot_id")
    if lot_id is None:
        return None
    for recommendation in recommendations:
        if recommendation["lot_id"] == lot_id:
            return recommendation
    raise ValueError(f"{lot_id} was not among the returned options")


def _updated_status(observed: dict, freshness: dict, status_recheck_request: dict) -> dict | None:
    """UC.1.21: the latest validated observation for the lot the driver asked to recheck."""
    lot_id = (status_recheck_request or {}).get("lot_id")
    if lot_id is None or lot_id not in observed:
        return None
    lot = observed[lot_id]
    return {"lot_id": lot_id, "available_spaces": lot["capacity"] - lot["occupied"],
            "capacity": lot["capacity"], "observed_at": lot["observed_at"],
            "stale": freshness.get(lot_id) != "current"}
