import json
from datetime import datetime, timedelta

import pytest

from language_model import assemble_contract
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


SUBMISSION_DATE = "2026-10-02"
OFFSET = "-04:00"
SUBMITTED_AT = f"{SUBMISSION_DATE}T10:30:40{OFFSET}"
DECISION_TIME = datetime.fromisoformat(f"{SUBMISSION_DATE}T10:47:00{OFFSET}")
SUPPORTED_VALUES = {
    "destinations": ["campus-center"],
    "vehicle_categories": ["car"],
    "eligibility_values": ["visitor"],
}


@pytest.fixture
def confirmed_trip():
    return {
        "destination": "campus-center",
        "arrival_time": f"{SUBMISSION_DATE}T10:45:00{OFFSET}",
        "departure_time": f"{SUBMISSION_DATE}T12:00:00{OFFSET}",
        "vehicle_category": "car",
        "declared_eligibility": "visitor",
        "access_needs": False,
    }


def interpret(confirmed, **additional_rules):
    return interpret_and_confirm_parking_requests(
        {"message": "I'd like to park on campus.", "submitted_at": SUBMITTED_AT},
        confirmed,
        trip_request_validation_rules={
            "arrival_window_minutes": 60,
            **additional_rules,
        },
    )


# DO-01 Confirmed Trip Request Output and SPEC Data Contract §5 arrival window.
@pytest.mark.parametrize(
    ("arrival_clock", "access_needs", "additional_rules"),
    [
        pytest.param("10:30:00", False, {}, id="submission-minute"),
        pytest.param(
            "11:30:00", True, {"supported_values": SUPPORTED_VALUES}, id="plus-60-minutes"
        ),
    ],
)
def test_a11_accepts_inclusive_window_and_returns_only_confirmed_fields(
    confirmed_trip, arrival_clock, access_needs, additional_rules
):
    confirmed_trip["arrival_time"] = f"{SUBMISSION_DATE}T{arrival_clock}{OFFSET}"
    confirmed_trip["access_needs"] = access_needs
    result = interpret({**confirmed_trip, "extra_field": "discard"}, **additional_rules)

    assert set(result) == {"normalized_trip_requirements"}
    normalized = result["normalized_trip_requirements"]
    assert set(normalized) == set(confirmed_trip)
    for field in ("arrival_time", "departure_time"):
        assert datetime.fromisoformat(normalized[field]) == datetime.fromisoformat(
            confirmed_trip[field]
        )
    for field in ("destination", "vehicle_category", "declared_eligibility"):
        assert normalized[field] == confirmed_trip[field]
    assert normalized["access_needs"] is access_needs


# DO-01 Confirmed Trip Request Output requires all six confirmed fields.
@pytest.mark.parametrize(
    "field",
    [
        "destination",
        "arrival_time",
        "departure_time",
        "vehicle_category",
        "declared_eligibility",
        "access_needs",
    ],
)
def test_a11_rejects_each_missing_field(confirmed_trip, field):
    del confirmed_trip[field]

    with pytest.raises(InvalidTripRequest):
        interpret(confirmed_trip)


# DO-01 Confirmed Trip Request Output requires valid confirmed string fields.
@pytest.mark.parametrize("field", ["destination", "vehicle_category", "declared_eligibility"])
@pytest.mark.parametrize("value", ["", 123], ids=["empty", "non-string"])
def test_a11_rejects_empty_or_non_string_values(confirmed_trip, field, value):
    confirmed_trip[field] = value

    with pytest.raises(InvalidTripRequest):
        interpret(confirmed_trip)


# DO-01 Confirmed Trip Request Output applies supplied supported-value rules.
@pytest.mark.parametrize("field", ["destination", "vehicle_category", "declared_eligibility"])
def test_a11_rejects_values_outside_supplied_lists(confirmed_trip, field):
    confirmed_trip[field] = "unsupported"

    with pytest.raises(InvalidTripRequest):
        interpret(confirmed_trip, supported_values=SUPPORTED_VALUES)


# SPEC Data Contract §5 requires access_needs to be a boolean.
@pytest.mark.parametrize("value", [0, "false", None], ids=["integer", "string", "null"])
def test_a11_rejects_non_boolean_access_needs(confirmed_trip, value):
    confirmed_trip["access_needs"] = value

    with pytest.raises(InvalidTripRequest):
        interpret(confirmed_trip)


# DO-01 Confirmed Trip Request Output and SPEC Data Contract §5 require valid times.
@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("arrival_time", "invalid", id="unparseable-arrival"),
        pytest.param(
            "arrival_time", f"{SUBMISSION_DATE}T10:45:00", id="offsetless-arrival"
        ),
        pytest.param("departure_time", "invalid", id="unparseable-departure"),
        pytest.param(
            "departure_time", f"{SUBMISSION_DATE}T12:00:00", id="offsetless-departure"
        ),
    ],
)
def test_a11_rejects_unparseable_or_offsetless_times(confirmed_trip, field, value):
    confirmed_trip[field] = value

    with pytest.raises(InvalidTripRequest):
        interpret(confirmed_trip)


# SPEC Data Contract §5 limits arrival to the 60-minute window from the submission minute.
@pytest.mark.parametrize("arrival_clock", ["10:29:59", "11:30:01"])
def test_a11_rejects_arrival_outside_window(confirmed_trip, arrival_clock):
    confirmed_trip["arrival_time"] = f"{SUBMISSION_DATE}T{arrival_clock}{OFFSET}"

    with pytest.raises(InvalidTripRequest):
        interpret(confirmed_trip)


# SPEC Data Contract §5 requires departure to be strictly later than arrival.
@pytest.mark.parametrize("departure_clock", ["10:44:59", "10:45:00"])
def test_a11_rejects_departure_at_or_before_arrival(confirmed_trip, departure_clock):
    confirmed_trip["departure_time"] = f"{SUBMISSION_DATE}T{departure_clock}{OFFSET}"

    with pytest.raises(InvalidTripRequest):
        interpret(confirmed_trip)


# DO-02 Information Request Issuance defines the three confirmed-trip requests.
@pytest.mark.parametrize("access_needs", [False, True])
def test_a12_builds_availability_context_and_policy_requests(confirmed_trip, access_needs):
    confirmed_trip["access_needs"] = access_needs
    result = request_parking_context_and_policy_information(
        confirmed_trip,
        {},
        information_acquisition_and_refresh_rules={
            "refresh_interval_seconds": 60,
            "lot_ids": ["lot-a", "lot-b"],
        },
        requested_at=SUBMITTED_AT,
    )

    assert result == {
        "availability_data_request": {
            "lot_ids": ["lot-a", "lot-b"],
            "as_of": SUBMITTED_AT,
            "refresh_interval_seconds": 60,
        },
        "context_data_request": {"destination": "campus-center"},
        "parking_policy_request": {
            "declared_eligibility": "visitor",
            "access_needs": access_needs,
        },
    }
    assert result["parking_policy_request"]["access_needs"] is access_needs


# DO-02 Information Request Issuance defines the selected-lot recheck request.
def test_a12_builds_only_selected_lot_recheck_request(confirmed_trip):
    result = request_parking_context_and_policy_information(
        confirmed_trip,
        {"lot_id": "lot-b"},
        information_acquisition_and_refresh_rules={
            "refresh_interval_seconds": 60,
            "lot_ids": ["lot-a", "lot-b", "lot-c"],
        },
        requested_at=SUBMITTED_AT,
    )

    assert result == {
        "updated_availability_request": {"lot_id": "lot-b", "as_of": SUBMITTED_AT}
    }


def event(space_id="space-1", *, status="occupied", seconds_from_decision=-1):
    return {
        "space_id": space_id,
        "lot_id": "lot-a",
        "zone": "zone-a",
        "status": status,
        "timestamp": (
            DECISION_TIME + timedelta(seconds=seconds_from_decision)
        ).isoformat(),
    }


def validate(events, *, updated=None, context=None):
    return validate_parking_and_context_information(
        {},
        events,
        {} if updated is None else updated,
        [] if context is None else context,
        data_validation_and_freshness_rules={"stale_after_seconds": 120},
        parking_policy_constraints={"rules": []},
        decision_time=DECISION_TIME.isoformat(),
    )


def assert_lot_record(result, *, occupied, capacity, observed_at):
    (record,) = result["validated_parking_data"]
    assert set(record) == {"lot_id", "occupied", "capacity", "observed_at"}
    assert record["lot_id"] == "lot-a"
    assert record["occupied"] == occupied
    assert record["capacity"] == capacity
    assert datetime.fromisoformat(record["observed_at"]) == datetime.fromisoformat(
        observed_at
    )


# DO-03 Observation Validation Status and SPEC Data Contract §1 retain stale observations.
@pytest.mark.parametrize(
    ("age_seconds", "freshness"),
    [(119, "current"), (120, "current"), (121, "stale")],
)
def test_a13_labels_freshness_boundary_and_keeps_stale_lot(age_seconds, freshness):
    observation = event(seconds_from_decision=-age_seconds)
    result = validate([observation])

    assert set(result) == {
        "validated_parking_data",
        "validated_context_information",
        "data_quality_and_freshness_status",
    }
    assert result["data_quality_and_freshness_status"] == {"lot-a": freshness}
    assert_lot_record(
        result, occupied=1, capacity=1, observed_at=observation["timestamp"]
    )


# DO-03 Observation Validation Status and the A1.3 interface exclude invalid events.
@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        pytest.param("timestamp", {}, id="missing-timestamp"),
        pytest.param("timestamp", {"timestamp": "invalid"}, id="unparseable-timestamp"),
        pytest.param(
            "timestamp",
            {"timestamp": f"{SUBMISSION_DATE}T10:46:59"},
            id="offsetless-timestamp",
        ),
        pytest.param("zone", {}, id="missing-zone"),
        pytest.param("space_id", {"space_id": ""}, id="empty-space-id"),
        pytest.param("zone", {"zone": 123}, id="non-string-zone"),
        pytest.param("status", {"status": "unknown"}, id="invalid-status"),
    ],
)
def test_a13_excludes_invalid_events_and_marks_their_lot_stale(field, replacement):
    observation = event()
    del observation[field]
    observation.update(replacement)
    result = validate([observation])

    assert result["validated_parking_data"] == []
    assert result["data_quality_and_freshness_status"] == {"lot-a": "stale"}


# DO-03 Observation Validation Status tracks lots with no valid event alongside current lots.
def test_a13_reports_an_all_invalid_lot_alongside_a_current_lot():
    valid = event()
    missing_timestamp = {**event("space-2"), "lot_id": "lot-b"}
    del missing_timestamp["timestamp"]
    invalid_status = {**event("space-3", status="unknown"), "lot_id": "lot-b"}
    result = validate([missing_timestamp, valid, invalid_status])

    assert result["data_quality_and_freshness_status"] == {
        "lot-a": "current",
        "lot-b": "stale",
    }
    assert_lot_record(result, occupied=1, capacity=1, observed_at=valid["timestamp"])


# DO-03 Observation Validation Status accepts +5 s and excludes +6 s.
def test_a13_accepts_five_seconds_ahead_and_excludes_six():
    five_seconds_ahead = event("space-1", status="vacant", seconds_from_decision=5)
    six_seconds_ahead = event("space-2", seconds_from_decision=6)
    result = validate([five_seconds_ahead, six_seconds_ahead])

    assert result["data_quality_and_freshness_status"] == {"lot-a": "current"}
    assert_lot_record(
        result, occupied=0, capacity=1, observed_at=five_seconds_ahead["timestamp"]
    )


# SPEC Data Contract §1 uses the latest valid observation per space regardless of order.
@pytest.mark.parametrize("newer_first", [False, True], ids=["old-first", "new-first"])
def test_a13_latest_valid_event_wins_for_the_same_space(newer_first):
    older = event(seconds_from_decision=-40)
    newer = event(status="vacant", seconds_from_decision=-10)
    observations = [newer, older] if newer_first else [older, newer]
    result = validate(observations)

    assert result["data_quality_and_freshness_status"] == {"lot-a": "current"}
    assert_lot_record(result, occupied=0, capacity=1, observed_at=newer["timestamp"])


# DO-03 Observation Validation Status applies to both base and recheck observations.
def test_a13_combines_base_and_recheck_observations_before_aggregating():
    base = [
        event("space-1", seconds_from_decision=-30),
        event("space-2", seconds_from_decision=-121),
    ]
    recheck = [
        event("space-1", status="vacant", seconds_from_decision=-5),
        event("space-3", status="vacant", seconds_from_decision=0),
        event("space-4", status="unknown", seconds_from_decision=1),
    ]
    result = validate(base, updated={"lot_id": "lot-a", "observations": recheck})

    assert result["data_quality_and_freshness_status"] == {"lot-a": "current"}
    assert_lot_record(
        result, occupied=1, capacity=3, observed_at=recheck[1]["timestamp"]
    )


# C.1 Spec 1.4.3 and Validated Context Information exclude missing or invalid context.
def test_a13_keeps_valid_context_and_excludes_invalid_records():
    result = validate(
        [],
        context=[
            {"lot_id": "lot-a", "walking_time_minutes": 0},
            {"walking_time_minutes": 3},
            {"lot_id": "lot-b", "walking_time_minutes": -1},
            {"lot_id": "lot-c", "walking_time_minutes": "3"},
        ],
    )

    assert result["validated_context_information"] == [
        {"lot_id": "lot-a", "walking_time_minutes": 0}
    ]


@pytest.fixture
def adapter_fields():
    return {
        "destination": "campus-center",
        "arrival_time": "10:30",
        "departure_time": "12:00",
        "vehicle_category": "car",
        "declared_eligibility": "visitor",
        "access_needs": True,
    }


# SPEC.md Model Response Contract keeps recognized fields and lists unstated fields in order.
def test_adapter_keeps_recognized_fields_and_lists_unstated_fields(adapter_fields):
    adapter_fields.update(destination=None, departure_time=None, declared_eligibility=None)
    result = assemble_contract(json.dumps(adapter_fields), SUBMITTED_AT, SUPPORTED_VALUES)

    assert set(result) == {"status", "trip_request", "missing_fields"}
    assert result["status"] == "incomplete"
    assert result["missing_fields"] == ["destination", "departure_time", "declared_eligibility"]
    trip_request = result["trip_request"]
    assert set(trip_request) == {"arrival_time", "vehicle_category", "access_needs"}
    arrival = datetime.fromisoformat(trip_request["arrival_time"])
    assert arrival == datetime.fromisoformat(f"{SUBMISSION_DATE}T10:30:00{OFFSET}")
    assert arrival.date().isoformat() == SUBMISSION_DATE
    assert trip_request["vehicle_category"] == "car"
    assert trip_request["access_needs"] is True
    assert set(trip_request).isdisjoint(result["missing_fields"])


# SPEC.md Model Response Contract lists unsupported values without substituting values.
@pytest.mark.parametrize("field", ["destination", "vehicle_category", "declared_eligibility"])
def test_adapter_omits_unsupported_values(adapter_fields, field):
    adapter_fields[field] = "unsupported"
    result = assemble_contract(json.dumps(adapter_fields), SUBMITTED_AT, SUPPORTED_VALUES)

    assert result["status"] == "incomplete"
    assert result["missing_fields"] == [field]
    assert field not in result["trip_request"]
    assert datetime.fromisoformat(result["trip_request"]["departure_time"]) == (
        datetime.fromisoformat(f"{SUBMISSION_DATE}T12:00:00{OFFSET}")
    )
    assert set(result["trip_request"]).isdisjoint(result["missing_fields"])


# SPEC.md Model Response Contract defaults unstated access_needs to false.
def test_adapter_keeps_default_false_for_unstated_access_needs(adapter_fields):
    adapter_fields.update(arrival_time=None, access_needs=None)
    result = assemble_contract(json.dumps(adapter_fields), SUBMITTED_AT, SUPPORTED_VALUES)

    assert result["status"] == "incomplete"
    assert result["missing_fields"] == ["arrival_time", "departure_time"]
    assert result["trip_request"]["access_needs"] is False
    assert set(result["trip_request"]).isdisjoint(result["missing_fields"])
