"""Chapter 8 language model adapter, including the schema-violation path.

The transport is replaced by a fake Ollama reply, so these tests do not need
a running model. A value the adapter cannot use must come back as a
missing field, never as a substituted value. A reply without exactly the six
fields must come back as a fallback, which sends the driver to the six-field
form (SPEC.md Model Response Contract, Fallback).
"""

import json
import socket
from urllib.parse import urlparse

import pytest

import language_model
import smart_parking_service
from language_model import interpret_trip_request

SUBMITTED_AT = "2026-10-02T10:30:00-04:00"
SUPPORTED = {
    "destinations": ["Upson Hall", "Duffield Hall"],
    "vehicle_categories": ["sedan", "suv"],
    "eligibility_values": ["permit_O", "visitor"],
}
# What the model replies: copied values, null when not stated, "HH:MM" times.
REPLY = {
    "destination": "Upson Hall",
    "arrival_time": "11:20",
    "departure_time": "13:00",
    "vehicle_category": "sedan",
    "declared_eligibility": "permit_O",
    "access_needs": False,
}
# The Model Response Contract trip request the adapter assembles from REPLY.
TRIP = {
    "destination": "Upson Hall",
    "arrival_time": "2026-10-02T11:20:00-04:00",
    "departure_time": "2026-10-02T13:00:00-04:00",
    "vehicle_category": "sedan",
    "declared_eligibility": "permit_O",
    "access_needs": False,
}


def replying(content, done_reason="stop"):
    """A fake transport that returns content as the model's message."""
    sent = []

    def transport(body, timeout):
        sent.append((body, timeout))
        text = content if isinstance(content, str) else json.dumps(content)
        return {"message": {"role": "assistant", "content": text}, "done": True, "done_reason": done_reason}

    transport.sent = sent
    return transport


def interpret(transport, message="Upson Hall at 11:20 until 1 pm, sedan, O permit, no accessible space"):
    return interpret_trip_request(message, submitted_at=SUBMITTED_AT, supported_values=SUPPORTED,
                                  transport=transport)


def test_complete_reply_is_assembled_into_contract():
    assert interpret(replying(REPLY)) == {"status": "complete", "trip_request": TRIP}


def test_listed_values_match_without_case():
    result = interpret(replying({**REPLY, "vehicle_category": "SUV", "destination": "upson hall"}))
    assert result["trip_request"]["vehicle_category"] == "suv"
    assert result["trip_request"]["destination"] == "Upson Hall"


def test_unstated_access_needs_defaults_to_false():
    result = interpret(replying({**REPLY, "access_needs": None}))
    assert result == {"status": "complete", "trip_request": TRIP}


def test_unstated_fields_are_listed_as_missing():
    reply = {**REPLY, "vehicle_category": None, "declared_eligibility": None, "departure_time": None}
    assert interpret(replying(reply)) == {
        "status": "incomplete",
        "missing_fields": ["departure_time", "vehicle_category", "declared_eligibility"],
    }


@pytest.mark.parametrize("field, value", [
    ("destination", "Statler Hall"),              # not a supported destination
    ("vehicle_category", "bus"),                  # not an approved category
    ("declared_eligibility", "faculty CU permit"),  # not an approved eligibility value
    ("arrival_time", "11:20 am"),                 # not HH:MM
    ("arrival_time", "2026-10-02T11:20:00-04:00"),  # not HH:MM
    ("arrival_time", "10:00"),                    # before submission
    ("arrival_time", "11:31"),                    # more than 60 minutes after submission
    ("arrival_time", "25:00"),                    # not a clock time
    ("departure_time", "11:20"),                  # not after arrival
    ("destination", 7),                           # wrong type
])
def test_unusable_value_is_listed_as_missing_not_substituted(field, value):
    result = interpret(replying({**REPLY, field: value}))
    assert result["status"] == "incomplete"
    assert field in result["missing_fields"]


def test_departure_is_missing_when_arrival_is_missing():
    result = interpret(replying({**REPLY, "arrival_time": None}))
    assert result == {"status": "incomplete", "missing_fields": ["arrival_time", "departure_time"]}


def test_access_needs_of_wrong_type_defaults_to_false():
    result = interpret(replying({**REPLY, "access_needs": "no"}))
    assert result == {"status": "complete", "trip_request": TRIP}


def test_times_use_the_submission_date_and_offset():
    result = interpret_trip_request(
        "x", submitted_at="2026-11-02T15:00:00-05:00", supported_values=SUPPORTED,
        transport=replying({**REPLY, "arrival_time": "15:30", "departure_time": "18:00"}))
    assert result["trip_request"]["arrival_time"] == "2026-11-02T15:30:00-05:00"
    assert result["trip_request"]["departure_time"] == "2026-11-02T18:00:00-05:00"


def test_arrival_in_the_submission_minute_is_accepted():
    result = interpret_trip_request(
        "x", submitted_at="2026-10-02T11:20:40-04:00", supported_values=SUPPORTED,
        transport=replying(REPLY))
    assert result["status"] == "complete"


def test_request_follows_adapter_specification():
    transport = replying(REPLY)
    interpret(transport, message="park please")
    body, timeout = transport.sent[0]
    assert body["model"] == "qwen3:4b"
    assert body["stream"] is False and body["think"] is False
    assert body["options"] == {"temperature": 0, "seed": 5151, "num_predict": 512, "num_ctx": 4096}
    assert body["format"]["required"] == list(language_model.REQUIRED_FIELDS)
    assert "enum" not in json.dumps(body["format"])
    user_prompt = body["messages"][1]["content"]
    assert "Driver message: park please" in user_prompt
    assert "Current local date and time: 2026-10-02 10:30 (UTC-04:00)" in user_prompt
    assert "Supported eligibility values: permit_O, visitor" in user_prompt
    assert timeout == 60


@pytest.mark.parametrize("content, reason", [
    ("not json at all", "malformed_json"),
    ("<think>hmm</think>{\"destination\": null}", "malformed_json"),
    (["Upson Hall"], "malformed_json"),
    ({k: v for k, v in REPLY.items() if k != "access_needs"}, "wrong_fields"),
    ({**REPLY, "group_size": 2}, "wrong_fields"),
    ({**REPLY, "explanation": "LOT-1 is best"}, "wrong_fields"),
    ({"status": "complete", "trip_request": TRIP}, "wrong_fields"),
])
def test_reply_without_the_six_fields_falls_back(content, reason):
    assert interpret(replying(content)) == {"status": "fallback", "reason": reason}


def test_truncated_output_falls_back():
    result = interpret(replying(REPLY, done_reason="length"))
    assert result == {"status": "fallback", "reason": "output_truncated"}


@pytest.mark.parametrize("error", [ConnectionRefusedError(), socket.timeout(), TimeoutError()])
def test_unreachable_or_slow_model_falls_back(error):
    def transport(body, timeout):
        raise error
    assert interpret(transport) == {"status": "fallback", "reason": "model_unavailable"}


def test_unexpected_ollama_envelope_falls_back():
    assert interpret(lambda body, timeout: {"error": "model not found"}) == \
        {"status": "fallback", "reason": "malformed_json"}


def test_overlong_message_is_not_sent_to_model():
    transport = replying(REPLY)
    result = interpret(transport, message="x" * 2001)
    assert result == {"status": "fallback", "reason": "message_too_long"}
    assert transport.sent == []


def test_model_endpoint_is_local():
    assert urlparse(language_model.OLLAMA_CHAT_URL).hostname in ("127.0.0.1", "localhost", "::1")


def test_fallback_presents_six_field_form_without_raw_output(monkeypatch):
    monkeypatch.setattr(smart_parking_service, "model_interpret",
                        lambda message, **kwargs: {"status": "fallback", "reason": "malformed_json"})
    result = smart_parking_service.interpret_trip_request("anything")
    assert result == {"status": "form_required", "trip_request": {},
                      "missing_fields": list(smart_parking_service.REQUIRED_FIELDS)}
