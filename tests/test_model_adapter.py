"""Chapter 8 language model adapter, including the schema-violation path.

The transport is replaced by a fake Ollama reply, so these tests do not need
a running model. Every reply that violates the SPEC.md Model Response
Contract must come back as a fallback, which sends the driver to the
six-field form (Model Response Contract, Fallback).
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


def test_complete_response_passes_through_adapter():
    result = interpret(replying({"status": "complete", "trip_request": TRIP}))
    assert result == {"status": "complete", "trip_request": TRIP}


def test_incomplete_response_lists_missing_fields():
    result = interpret(replying({"status": "incomplete", "missing_fields": ["access_needs"]}))
    assert result == {"status": "incomplete", "missing_fields": ["access_needs"]}


def test_request_follows_adapter_specification():
    transport = replying({"status": "incomplete", "missing_fields": ["destination"]})
    interpret(transport, message="park please")
    body, timeout = transport.sent[0]
    assert body["model"] == "qwen3:4b"
    assert body["stream"] is False and body["think"] is False
    assert body["options"] == {"temperature": 0, "seed": 5151, "num_predict": 512, "num_ctx": 4096}
    assert body["format"]["properties"]["status"]["enum"] == ["complete", "incomplete"]
    assert "Driver message: park please" in body["messages"][1]["content"]
    assert f"Current date and time: {SUBMITTED_AT}" in body["messages"][1]["content"]
    assert timeout == 60


@pytest.mark.parametrize("content, reason", [
    ("not json at all", "malformed_json"),
    ("<think>hmm</think>{\"status\": \"complete\"}", "malformed_json"),
    (["complete"], "malformed_json"),
    ({"status": "done", "trip_request": TRIP}, "unsupported_status"),
    ({"trip_request": TRIP}, "unsupported_status"),
    ({"status": "complete", "trip_request": {k: v for k, v in TRIP.items() if k != "access_needs"}},
     "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "group_size": 2}}, "invalid_fields"),
    ({"status": "complete", "trip_request": TRIP, "explanation": "LOT-1 is best"}, "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "destination": "Mars"}}, "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "vehicle_category": "bus"}}, "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "declared_eligibility": "unknown"}}, "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "access_needs": "no"}}, "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "arrival_time": "11:20"}}, "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "arrival_time": "2026-10-02T11:20:00"}}, "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "arrival_time": "2026-10-02T10:00:00-04:00"}},
     "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "arrival_time": "2026-10-02T11:31:00-04:00"}},
     "invalid_fields"),
    ({"status": "complete", "trip_request": {**TRIP, "departure_time": "2026-10-02T11:20:00-04:00"}},
     "invalid_fields"),
    ({"status": "incomplete", "missing_fields": []}, "invalid_fields"),
    ({"status": "incomplete", "missing_fields": ["group_size"]}, "invalid_fields"),
    ({"status": "incomplete", "missing_fields": ["destination", "destination"]}, "invalid_fields"),
    ({"status": "incomplete", "missing_fields": ["destination"], "trip_request": TRIP}, "invalid_fields"),
])
def test_schema_violations_fall_back(content, reason):
    assert interpret(replying(content)) == {"status": "fallback", "reason": reason}


def test_truncated_output_falls_back():
    result = interpret(replying({"status": "complete", "trip_request": TRIP}, done_reason="length"))
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
    transport = replying({"status": "complete", "trip_request": TRIP})
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
