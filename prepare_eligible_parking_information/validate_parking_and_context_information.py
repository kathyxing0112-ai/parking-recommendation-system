"""C.1.3 Data Validation Module -- A1.3 Validate Parking and Context Information.

Requirements: C.1 Spec 1.4.3 and 2.1.1; DO-03; SR-09; SPEC Data Contract
section 1. Sensor events become lot-level Validated Parking Data, each lot gets
a current or stale status, and invalid observations are left out. Eligibility
belongs to A1.4, so a stale lot stays in Validated Parking Data.
"""

from datetime import datetime, timedelta

EVENT_FIELDS = ("space_id", "lot_id", "zone", "status", "timestamp")
STATUSES = ("occupied", "vacant", "unknown")
MAX_FUTURE_SKEW = timedelta(seconds=5)  # DO-03 and SPEC Data Contract section 1


def _offset_aware(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _usable_time(event: dict, decision_time: datetime) -> datetime | None:
    """The observation time of a valid event, or None if the event is invalid."""
    if not all(isinstance(event.get(field), str) and event[field] for field in EVENT_FIELDS):
        return None
    if event["status"] not in STATUSES:
        return None
    observed = _offset_aware(event["timestamp"])
    if observed is None or observed > decision_time + MAX_FUTURE_SKEW:
        return None
    return observed


def validate_parking_and_context_information(
    normalized_trip_requirements: dict,
    parking_availability_data: list[dict],
    updated_parking_availability: dict,
    contextual_information: list[dict],
    *,
    data_validation_and_freshness_rules: dict,
    parking_policy_constraints: dict,
    decision_time: str,
) -> dict:
    """A1.3: validate observations and context at decision_time.

    in: normalized_trip_requirements (A1.1; not used in the checks),
    parking_availability_data (SPEC section 1 sensor events),
    updated_parking_availability ({"lot_id", "observations"}; empty when no
    recheck is in progress), contextual_information ({lot_id,
    walking_time_minutes}).
    control: data_validation_and_freshness_rules ({"stale_after_seconds"}),
    parking_policy_constraints (rule coverage is decided in A1.4).
    decision_time: offset-aware ISO 8601 request submission time, the
    reference for freshness (Data Quality and Freshness Status).
    out: validated_parking_data, validated_context_information,
    data_quality_and_freshness_status.
    """
    now = datetime.fromisoformat(decision_time)
    stale_after = timedelta(seconds=data_validation_and_freshness_rules["stale_after_seconds"])
    events = list(parking_availability_data) + list(updated_parking_availability.get("observations", []))

    latest_by_space = {}
    freshness = {}
    for event in events:
        lot_id = event.get("lot_id")
        if isinstance(lot_id, str) and lot_id:
            # A lot with no valid observation stays stale (SR-09).
            freshness.setdefault(lot_id, "stale")
        observed = _usable_time(event, now)
        if observed is None:
            continue
        key = (event["lot_id"], event["space_id"])
        if key not in latest_by_space or observed > latest_by_space[key][0]:
            latest_by_space[key] = (observed, event["status"])

    lots = {}
    for (lot_id, _), (observed, status) in latest_by_space.items():
        lot = lots.setdefault(lot_id, {"occupied": 0, "capacity": 0, "observed_at": observed})
        lot["capacity"] += 1
        # SPEC section 1: an unknown space is not counted as available.
        lot["occupied"] += status in ("occupied", "unknown")
        lot["observed_at"] = max(lot["observed_at"], observed)

    validated_parking_data = []
    for lot_id, lot in lots.items():
        validated_parking_data.append({
            "lot_id": lot_id,
            "occupied": lot["occupied"],
            "capacity": lot["capacity"],
            "observed_at": lot["observed_at"].isoformat(),
        })
        freshness[lot_id] = "current" if now - lot["observed_at"] <= stale_after else "stale"

    validated_context_information = [
        {"lot_id": item["lot_id"], "walking_time_minutes": item["walking_time_minutes"]}
        for item in contextual_information
        if isinstance(item.get("lot_id"), str) and item["lot_id"]
        and isinstance(item.get("walking_time_minutes"), (int, float))
        and not isinstance(item.get("walking_time_minutes"), bool)
        and item["walking_time_minutes"] >= 0
    ]

    return {
        "validated_parking_data": validated_parking_data,
        "validated_context_information": validated_context_information,
        "data_quality_and_freshness_status": freshness,
    }
