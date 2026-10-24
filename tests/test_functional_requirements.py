"""Chapter 5 functional-requirement suite, one test per first-level requirement.

Each test is named for a system functional requirement (1.4.1-1.4.6, Innoslate
model v3) and derived from the requirement text together with the SPEC.md
acceptance criteria of the stakeholder requirements its function traces to
(report Table 2). The tests call the Chapter 4 signatures and fail until the
module bodies are implemented.

Record shapes inside the inputs and controls are not yet fixed by the model;
the shapes below follow SPEC.md's Data Contract and are to be confirmed by the
internal interface contract in Chapter 7.
"""

from datetime import datetime, timedelta, timezone

from apply_personal_data_retention_rules import apply_personal_data_retention_rules
from authorize_protected_data_operations import authorize_protected_data_operations
from estimate_arrival_time_availability import estimate_arrival_time_availability
from prepare_eligible_parking_information import prepare_eligible_parking_information
from present_parking_recommendations_and_status import (
    present_parking_recommendations_and_status,
)
from rank_parking_options import rank_parking_options

TRIP = {
    "destination": "Upson Hall",
    "arrival_time": "2026-10-02T11:20:00-04:00",
    "departure_time": "2026-10-02T13:00:00-04:00",
    "vehicle_category": "sedan",
    "declared_eligibility": "permit_O",
    "access_needs": False,
}

WALKING = [
    {"lot_id": "LOT-1", "walking_time_minutes": 5},
    {"lot_id": "LOT-2", "walking_time_minutes": 10},
    {"lot_id": "LOT-3", "walking_time_minutes": 15},
]


def test_FR_1_4_1_prepares_eligible_parking_information():
    """1.4.1: The system shall Prepare Eligible Parking Information.

    Traced: SR-12 (confirmed six-field request), SR-10 (closed areas and
    areas whose confirmed rule does not allow the declared permit are
    excluded), SR-09 (observation older than 120 seconds is stale).
    """
    submitted_at = "2026-10-02T10:30:00-04:00"
    observations = [
        {"space_id": "L1-001", "lot_id": "LOT-1", "zone": "permit_O",
         "status": "vacant", "timestamp": "2026-10-02T10:29:30-04:00"},
        {"space_id": "L2-001", "lot_id": "LOT-2", "zone": "permit_O",
         "status": "vacant", "timestamp": "2026-10-02T10:29:30-04:00"},
        {"space_id": "L3-001", "lot_id": "LOT-3", "zone": "permit_O",
         "status": "vacant", "timestamp": "2026-10-02T10:27:00-04:00"},
        {"space_id": "L4-001", "lot_id": "LOT-4", "zone": "permit_O",
         "status": "vacant", "timestamp": "2026-10-02T10:29:30-04:00"},
    ]
    walking = WALKING + [{"lot_id": "LOT-4", "walking_time_minutes": 8}]
    rules = {"rules": [
        {"lot_id": "LOT-1", "eligibility_class": "permit_O", "allowed": True, "closure": False},
        {"lot_id": "LOT-2", "eligibility_class": "permit_O", "allowed": True, "closure": True},
        {"lot_id": "LOT-3", "eligibility_class": "permit_O", "allowed": True, "closure": False},
        {"lot_id": "LOT-4", "eligibility_class": "permit_O", "allowed": False, "closure": False},
    ]}

    result = prepare_eligible_parking_information(
        {"message": "Upson Hall, 11:20 to 13:00, sedan, O permit, no accessible space",
         "submitted_at": submitted_at},
        TRIP,
        {},
        observations,
        {},
        walking,
        {},
        trip_request_validation_rules={"arrival_window_minutes": 60},
        information_acquisition_and_refresh_rules={"refresh_interval_seconds": 60},
        data_validation_and_freshness_rules={"stale_after_seconds": 120},
        parking_policy_constraints=rules,
        authorization_decision={"permitted": True},
    )

    assert result["normalized_trip_requirements"] == TRIP
    eligible = {area["lot_id"] for area in result["eligible_parking_areas"]}
    assert eligible == {"LOT-1", "LOT-3"}
    assert result["data_quality_and_freshness_status"]["LOT-1"] == "current"
    assert result["data_quality_and_freshness_status"]["LOT-3"] == "stale"


def test_FR_1_4_2_estimates_arrival_time_availability():
    """1.4.2: The system shall Estimate Arrival Time Availability.

    Traced: SR-14 (forecast only from an observation no more than 120 seconds
    old; an unsupported forecast is withheld).
    """
    validated_parking_data = [
        {"lot_id": "LOT-1", "occupied": 60, "capacity": 100,
         "observed_at": "2026-10-02T10:29:30-04:00"},
        {"lot_id": "LOT-3", "occupied": 150, "capacity": 200,
         "observed_at": "2026-10-02T10:27:00-04:00"},
    ]

    result = estimate_arrival_time_availability(
        validated_parking_data,
        TRIP,
        WALKING,
        [{"lot_id": "LOT-1"}, {"lot_id": "LOT-3"}],
        {"LOT-1": "current", "LOT-3": "stale"},
        forecast_validity_criteria={"max_observation_age_seconds": 120,
                                    "horizons_minutes": [0, 15, 30, 45, 60]},
    )

    estimates = {e["lot_id"]: e for e in result["arrival_time_availability_estimates"]}
    assert set(estimates) == {"LOT-1"}
    lot_1 = estimates["LOT-1"]
    assert 0 <= lot_1["interval_lower"] <= lot_1["available_spaces"] <= lot_1["interval_upper"] <= 100
    assert result["forecast_validity_status"]["LOT-1"] == "supported"
    assert result["forecast_validity_status"]["LOT-3"] == "unsupported"


def test_FR_1_4_3_ranks_parking_options():
    """1.4.3: The system shall Rank Parking Options.

    Traced: SR-13 (S = 0.40W + 0.40A + 0.20Q when every forecast is valid;
    otherwise order by ascending walking time; return the first two).
    Expected scores: LOT-1 0.56, LOT-2 0.68, LOT-3 0.18.
    """
    estimates = [
        {"lot_id": "LOT-1", "capacity": 100, "available_spaces": 10,
         "interval_lower": 0, "interval_upper": 40},
        {"lot_id": "LOT-2", "capacity": 50, "available_spaces": 40,
         "interval_lower": 35, "interval_upper": 45},
        {"lot_id": "LOT-3", "capacity": 200, "available_spaces": 20,
         "interval_lower": 0, "interval_upper": 60},
    ]
    eligible = [{"lot_id": "LOT-1"}, {"lot_id": "LOT-2"}, {"lot_id": "LOT-3"}]
    freshness = {"LOT-1": "current", "LOT-2": "current", "LOT-3": "current"}
    rules = {"weights": {"walking_time": 0.40, "availability": 0.40, "uncertainty": 0.20}}

    scored = rank_parking_options(
        TRIP, WALKING, eligible, freshness, estimates,
        {"LOT-1": "supported", "LOT-2": "supported", "LOT-3": "supported"},
        ranking_and_fallback_rules=rules,
    )
    assert [option["lot_id"] for option in scored] == ["LOT-2", "LOT-1"]

    fallback = rank_parking_options(
        TRIP, WALKING, eligible, freshness, estimates[:2],
        {"LOT-1": "supported", "LOT-2": "supported", "LOT-3": "unsupported"},
        ranking_and_fallback_rules=rules,
    )
    assert [option["lot_id"] for option in fallback] == ["LOT-1", "LOT-2"]

    # SR-13: with one eligible area, return one option; with none, return none.
    single = rank_parking_options(
        TRIP, WALKING, [{"lot_id": "LOT-2"}], {"LOT-2": "current"}, estimates[1:2],
        {"LOT-2": "supported"},
        ranking_and_fallback_rules=rules,
    )
    assert [option["lot_id"] for option in single] == ["LOT-2"]

    none = rank_parking_options(
        TRIP, WALKING, [], {}, [], {},
        ranking_and_fallback_rules=rules,
    )
    assert none == []


def test_FR_1_4_3_tie_breaks_follow_sr13():
    """1.4.3: The system shall Rank Parking Options.

    Traced: SR-13 (rank by descending score, then ascending walking time,
    then area ID).
    """
    rules = {"weights": {"walking_time": 0.40, "availability": 0.40, "uncertainty": 0.20}}

    # Case 1: equal scores (0.5), walking time decides.
    walking = [
        {"lot_id": "LOT-A", "walking_time_minutes": 10},
        {"lot_id": "LOT-B", "walking_time_minutes": 5},
    ]
    estimates = [
        {"lot_id": "LOT-A", "capacity": 100, "available_spaces": 100,
         "interval_lower": 25, "interval_upper": 75},
        {"lot_id": "LOT-B", "capacity": 100, "available_spaces": 0,
         "interval_lower": 0, "interval_upper": 50},
    ]
    ranked = rank_parking_options(
        TRIP, walking, [{"lot_id": "LOT-A"}, {"lot_id": "LOT-B"}],
        {"LOT-A": "current", "LOT-B": "current"}, estimates,
        {"LOT-A": "supported", "LOT-B": "supported"},
        ranking_and_fallback_rules=rules,
    )
    assert [option["lot_id"] for option in ranked] == ["LOT-B", "LOT-A"]
    assert [option["score"] for option in ranked] == [0.5, 0.5]

    # Case 2: equal scores and walking times, area ID decides.
    walking = [
        {"lot_id": "LOT-B", "walking_time_minutes": 5},
        {"lot_id": "LOT-A", "walking_time_minutes": 5},
    ]
    estimates = [
        {"lot_id": "LOT-B", "capacity": 100, "available_spaces": 40,
         "interval_lower": 30, "interval_upper": 50},
        {"lot_id": "LOT-A", "capacity": 100, "available_spaces": 40,
         "interval_lower": 30, "interval_upper": 50},
    ]
    ranked = rank_parking_options(
        TRIP, walking, [{"lot_id": "LOT-B"}, {"lot_id": "LOT-A"}],
        {"LOT-A": "current", "LOT-B": "current"}, estimates,
        {"LOT-A": "supported", "LOT-B": "supported"},
        ranking_and_fallback_rules=rules,
    )
    assert [option["lot_id"] for option in ranked] == ["LOT-A", "LOT-B"]


def test_FR_1_4_4_presents_parking_recommendations_and_status():
    """1.4.4: The system shall Present Parking Recommendations and Status.

    Traced: SR-09 (stale label and last-observed time), SR-15 (an explanation
    for every returned option), SR-13 (no implied reservation or guarantee: an
    advisory notice is shown and no explanation claims a reserved or
    guaranteed space).
    """
    validated_parking_data = [
        {"lot_id": "LOT-1", "occupied": 90, "capacity": 100,
         "observed_at": "2026-10-02T10:29:30-04:00"},
        {"lot_id": "LOT-2", "occupied": 10, "capacity": 50,
         "observed_at": "2026-10-02T10:27:00-04:00"},
    ]
    ranked = [{"lot_id": "LOT-1"}, {"lot_id": "LOT-2"}]

    result = present_parking_recommendations_and_status(
        {},
        {},
        {},
        validated_parking_data,
        TRIP,
        WALKING,
        [{"lot_id": "LOT-1"}, {"lot_id": "LOT-2"}],
        {"LOT-1": "current", "LOT-2": "stale"},
        [],
        {"LOT-1": "unsupported", "LOT-2": "unsupported"},
        ranked,
        authorization_decision={"permitted": True},
        parking_policy_constraints={"rules": []},
        presentation_and_explanation_rules={"stale_after_seconds": 120},
    )

    recommendations = {r["lot_id"]: r for r in result["ranked_parking_recommendations"]}
    assert set(recommendations) == {"LOT-1", "LOT-2"}
    assert recommendations["LOT-1"]["stale"] is False
    assert recommendations["LOT-2"]["stale"] is True
    assert recommendations["LOT-2"]["last_observed_at"] == "2026-10-02T10:27:00-04:00"
    assert result["advisory_notice"]
    affirmative_claims = ("is reserved", "reserved for you", "is guaranteed",
                          "guaranteed space", "guaranteed to")
    for recommendation in recommendations.values():
        explanation = recommendation["explanation"].lower()
        assert explanation
        assert not any(claim in explanation for claim in affirmative_claims)


def test_FR_1_4_5_authorizes_protected_data_operations():
    """1.4.5: The system shall Authorize Protected Data Operations.

    Traced: SR-03 (operations are allowed only by the approved three-role
    matrix; drivers and maintainers access only their own session's trip
    record; zero prohibited operations succeed). Identity establishment is an
    open decision and is not tested here.
    """
    own_session_trip_operations = {
        "save_trip_record": "own_session",
        "read_trip_record": "own_session",
        "update_trip_record": "own_session",
    }
    matrix = {
        "driver": own_session_trip_operations,
        "maintainer": {
            **own_session_trip_operations,
            "change_parking_rules": "any",
            "change_simulator_settings": "any",
            "change_model_version": "any",
        },
        "retention_service": {"delete_expired_trip_record": "any"},
    }

    def decide(role, operation, caller_session_id=None, record_session_id=None):
        request = {"role": role, "operation": operation}
        if caller_session_id is not None:
            request["caller_session_id"] = caller_session_id
        if record_session_id is not None:
            request["record_session_id"] = record_session_id
        return authorize_protected_data_operations(
            request, approved_role_permission_matrix=matrix,
        )["permitted"]

    assert decide("driver", "read_trip_record", "s-1", "s-1") is True
    assert decide("driver", "read_trip_record", "s-1", "s-2") is False
    assert decide("driver", "read_trip_record", None, "s-1") is False
    assert decide("maintainer", "update_trip_record", "s-3", "s-4") is False
    assert decide("maintainer", "change_parking_rules") is True
    assert decide("retention_service", "delete_expired_trip_record") is True
    assert decide("driver", "change_parking_rules") is False
    assert decide("driver", "delete_expired_trip_record", "s-1", "s-1") is False
    assert decide("retention_service", "read_trip_record", "s-1", "s-1") is False
    assert decide("unknown_role", "read_trip_record", "s-1", "s-1") is False


def test_FR_1_4_6_applies_personal_data_retention_rules():
    """1.4.6: The system shall Apply Personal Data Retention Rules.

    Traced: SR-04 (each trip record is deleted no later than 24 hours after
    submission). This increment identifies expired records and authorizes
    their deletion; physical deletion from storage arrives with the storage
    adapter in Chapter 8.
    """
    now = datetime.now(timezone.utc)
    records = [
        {"record_id": "trip-25h", "submitted_at": (now - timedelta(hours=25)).isoformat()},
        {"record_id": "trip-24h01m",
         "submitted_at": (now - timedelta(hours=24, minutes=1)).isoformat()},
        {"record_id": "trip-23h59m",
         "submitted_at": (now - timedelta(hours=23, minutes=59)).isoformat()},
        {"record_id": "trip-1h", "submitted_at": (now - timedelta(hours=1)).isoformat()},
    ]
    schedule = {"retention_hours": 24}

    permitted = apply_personal_data_retention_rules(
        records, authorization_decision={"permitted": True},
        approved_data_retention_schedule=schedule,
    )
    disposition = permitted["personal_record_disposition_result"]
    assert disposition["authorized_for_deletion"] == ["trip-25h", "trip-24h01m"]
    assert "deleted" not in disposition

    denied = apply_personal_data_retention_rules(
        records, authorization_decision={"permitted": False},
        approved_data_retention_schedule=schedule,
    )
    assert denied["personal_record_disposition_result"]["authorized_for_deletion"] == []
