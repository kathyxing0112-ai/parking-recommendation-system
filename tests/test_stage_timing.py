"""Lab Manual §10.4: stage timing at the UC.1 participant boundaries.

The model call goes through a fake transport, so these tests need no running
model. They check that timing is off unless started, that every participant
boundary on the UC.1 path is recorded with entry and exit, that stages nest
as the sequence diagram does, and that nothing but stage names and times is
recorded (SR-04).
"""

import json
import threading
from datetime import datetime, timedelta

import pytest

import cornell_driver_interface as driver_interface
import language_model
import smart_parking_service
import stage_timing
from stage_timing import stage

FIND_PARKING_STAGES = {
    "UC1.find_parking", "X.C.2.availability", "X.C.3.context", "X.C.4.rules",
    "C.1.prepare", "C.1.1.confirm", "C.1.2.requests", "C.1.3.validate", "C.1.4.eligibility",
    "C.3.rank", "C.0.assemble_result",
}
EXPECTED_PARENT = {
    "UC1.find_parking": None,
    "X.C.2.availability": "UC1.find_parking",
    "X.C.3.context": "UC1.find_parking",
    "X.C.4.rules": "UC1.find_parking",
    "C.1.prepare": "UC1.find_parking",
    "C.1.1.confirm": "C.1.prepare",
    "C.1.2.requests": "C.1.prepare",
    "C.1.3.validate": "C.1.prepare",
    "C.1.4.eligibility": "C.1.prepare",
    "C.3.rank": "UC1.find_parking",
    "C.0.assemble_result": "UC1.find_parking",
    "UC1.interpret_request": None,
    "C.1.1.model_call": "UC1.interpret_request",
    "C.1.1.contract_check": "UC1.interpret_request",
}
MESSAGE = "Duffield Hall soon for two hours, sedan, O permit, no accessible space"


@pytest.fixture(autouse=True)
def timing_off_after_each_test():
    yield
    stage_timing.stop()


def confirmed_trip() -> dict:
    now = datetime.now().astimezone().replace(microsecond=0)
    return {
        "destination": "Duffield Hall",
        "arrival_time": (now + timedelta(minutes=30)).isoformat(),
        "departure_time": (now + timedelta(minutes=150)).isoformat(),
        "vehicle_category": "sedan",
        "declared_eligibility": "permit_O",
        "access_needs": False,
    }


@pytest.fixture
def fake_model(monkeypatch):
    """Route the service's model call through a fake Ollama reply."""
    reply = {"destination": "Duffield Hall", "arrival_time": None, "departure_time": None,
             "vehicle_category": "sedan", "declared_eligibility": "permit_O", "access_needs": False}

    def transport(body, timeout):
        return {"message": {"role": "assistant", "content": json.dumps(reply)}, "done": True,
                "done_reason": "stop"}

    def interpret(message, **kwargs):
        return language_model.interpret_trip_request(message, transport=transport, **kwargs)

    monkeypatch.setattr(smart_parking_service, "model_interpret", interpret)


def test_timing_is_off_unless_started():
    assert not stage_timing.is_recording()
    driver_interface.confirm_trip_requirements(confirmed_trip())
    assert stage_timing.stop() == []


def test_every_find_parking_boundary_is_recorded_once_with_entry_and_exit():
    stage_timing.start()
    result = driver_interface.confirm_trip_requirements(confirmed_trip())
    records = stage_timing.stop()

    assert result["ranked_options"], "the confirmed trip should reach ranking"
    assert sorted(r["stage"] for r in records) == sorted(FIND_PARKING_STAGES)
    for record in records:
        assert record["exit_ns"] >= record["entry_ns"]
        assert record["duration_ms"] == pytest.approx((record["exit_ns"] - record["entry_ns"]) / 1e6)
        assert record["parent"] == EXPECTED_PARENT[record["stage"]]


def test_child_stages_fit_inside_their_parent():
    stage_timing.start()
    driver_interface.confirm_trip_requirements(confirmed_trip())
    records = {r["stage"]: r for r in stage_timing.stop()}
    for record in records.values():
        if record["parent"]:
            parent = records[record["parent"]]
            assert parent["entry_ns"] <= record["entry_ns"] <= record["exit_ns"] <= parent["exit_ns"]


def test_interpret_request_records_the_model_call_and_contract_check(fake_model):
    stage_timing.start()
    interpreted = driver_interface.submit_trip_request(MESSAGE)
    records = stage_timing.stop()

    assert interpreted["status"] in ("complete", "incomplete")
    assert [r["stage"] for r in records] == ["C.1.1.model_call", "C.1.1.contract_check",
                                           "UC1.interpret_request"]
    for record in records:
        assert record["parent"] == EXPECTED_PARENT[record["stage"]]


def test_records_hold_stage_names_and_times_only(fake_model):
    stage_timing.start()
    driver_interface.submit_trip_request(MESSAGE)
    driver_interface.confirm_trip_requirements(confirmed_trip())
    records = stage_timing.stop()
    for record in records:
        assert set(record) == {"stage", "parent", "entry_ns", "exit_ns", "duration_ms"}
    assert "Duffield" not in json.dumps(records)


def test_exit_is_recorded_when_a_stage_raises():
    stage_timing.start()
    with pytest.raises(RuntimeError):
        with stage("C.3.rank"):
            raise RuntimeError("boom")
    (record,) = stage_timing.stop()
    assert record["stage"] == "C.3.rank"
    assert record["exit_ns"] >= record["entry_ns"]


def test_unknown_stage_name_is_rejected_while_recording():
    stage_timing.start()
    with pytest.raises(ValueError):
        with stage("not-a-stage"):
            pass


def test_recording_on_one_thread_does_not_capture_another():
    stage_timing.start()
    worker = threading.Thread(target=lambda: driver_interface.confirm_trip_requirements(confirmed_trip()))
    worker.start()
    worker.join()
    assert stage_timing.stop() == []
