"""Language model adapter -- part of C.1.1 Trip Request Interpretation Module.

Calls the local language model recorded in docs/environment.md (Qwen3 4B
hosted through Ollama). Per ADR-0002 the model only interprets a driver's
chatbot message into the six-field trip request of the SPEC.md Model Response
Contract, or lists the missing fields. It does not predict availability, check
eligibility, rank parking areas, or write explanations.

The adapter contract (prompt template, parameters, timeout, token limits,
response schema, and schema-violation behavior) is specified in
docs/model-adapter.md. Any output that does not satisfy the Model Response
Contract is discarded and reported as {"status": "fallback", "reason": ...};
the application then presents the six-field form. Raw messages and raw model
output are never logged or stored (SR-04).
"""

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta

# Local only: the endpoint is the loopback address, so no project data leaves the machine.
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen3:4b"
TIMEOUT_SECONDS = 60
MAX_MESSAGE_CHARACTERS = 2000
MODEL_OPTIONS = {"temperature": 0, "seed": 5151, "num_predict": 512, "num_ctx": 4096}

REQUIRED_FIELDS = (
    "destination",
    "arrival_time",
    "departure_time",
    "vehicle_category",
    "declared_eligibility",
    "access_needs",
)
ARRIVAL_WINDOW = timedelta(minutes=60)  # SPEC Data Contract section 5

SYSTEM_PROMPT = """You convert one driver's parking request into JSON for a campus parking system.
Reply with exactly one JSON object and nothing else. It must be one of:
{"status": "complete", "trip_request": {"destination": ..., "arrival_time": ..., "departure_time": ..., "vehicle_category": ..., "declared_eligibility": ..., "access_needs": ...}}
{"status": "incomplete", "missing_fields": [...]}
Rules:
- destination, vehicle_category and declared_eligibility must be copied exactly from the supported values given.
- arrival_time and departure_time are ISO 8601 timestamps with a UTC offset, computed from the current date and time given.
- access_needs is true or false only if the driver says whether accessible parking is needed.
- If any field is not stated or cannot be determined reliably, do not guess: return "incomplete" and list every such field in missing_fields, using these names: destination, arrival_time, departure_time, vehicle_category, declared_eligibility, access_needs."""

USER_PROMPT_TEMPLATE = """Current date and time: {submitted_at}
Supported destinations: {destinations}
Supported vehicle categories: {vehicle_categories}
Supported eligibility values: {eligibility_values}
Driver message: {message}"""

RESPONSE_FORMAT = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["complete", "incomplete"]},
        "trip_request": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "arrival_time": {"type": "string"},
                "departure_time": {"type": "string"},
                "vehicle_category": {"type": "string"},
                "declared_eligibility": {"type": "string"},
                "access_needs": {"type": "boolean"},
            },
        },
        "missing_fields": {"type": "array", "items": {"type": "string", "enum": list(REQUIRED_FIELDS)}},
    },
    "required": ["status"],
}


def build_request(message: str, submitted_at: str, supported_values: dict) -> dict:
    """The Ollama /api/chat request body the adapter sends."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        submitted_at=submitted_at,
        destinations=", ".join(supported_values["destinations"]),
        vehicle_categories=", ".join(supported_values["vehicle_categories"]),
        eligibility_values=", ".join(supported_values["eligibility_values"]),
        message=message,
    )
    return {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "format": RESPONSE_FORMAT,
        "stream": False,
        "think": False,
        "options": dict(MODEL_OPTIONS),
    }


def post_to_local_ollama(body: dict, timeout: float) -> dict:
    """Default transport: one POST to the local Ollama server."""
    request = urllib.request.Request(
        OLLAMA_CHAT_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def _offset_aware(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _trip_request_is_valid(trip: dict, submitted_at: datetime, supported_values: dict) -> bool:
    if not isinstance(trip, dict) or set(trip) != set(REQUIRED_FIELDS):
        return False
    if trip["destination"] not in supported_values["destinations"]:
        return False
    if trip["vehicle_category"] not in supported_values["vehicle_categories"]:
        return False
    if trip["declared_eligibility"] not in supported_values["eligibility_values"]:
        return False
    if not isinstance(trip["access_needs"], bool):
        return False
    arrival = _offset_aware(trip["arrival_time"])
    departure = _offset_aware(trip["departure_time"])
    if arrival is None or departure is None:
        return False
    if not submitted_at <= arrival <= submitted_at + ARRIVAL_WINDOW:
        return False
    return departure > arrival


def validate_model_output(content: str, submitted_at: str, supported_values: dict) -> dict:
    """Check model text against the Model Response Contract.

    Returns the parsed response, or {"status": "fallback", "reason": ...}.
    """
    try:
        response = json.loads(content)
    except (TypeError, ValueError):
        return {"status": "fallback", "reason": "malformed_json"}
    if not isinstance(response, dict):
        return {"status": "fallback", "reason": "malformed_json"}

    status = response.get("status")
    if status == "complete":
        if set(response) != {"status", "trip_request"}:
            return {"status": "fallback", "reason": "invalid_fields"}
        if not _trip_request_is_valid(response["trip_request"], datetime.fromisoformat(submitted_at),
                                      supported_values):
            return {"status": "fallback", "reason": "invalid_fields"}
        return {"status": "complete", "trip_request": dict(response["trip_request"])}
    if status == "incomplete":
        missing = response.get("missing_fields")
        if (set(response) != {"status", "missing_fields"} or not isinstance(missing, list) or not missing
                or len(set(missing)) != len(missing) or not set(missing) <= set(REQUIRED_FIELDS)):
            return {"status": "fallback", "reason": "invalid_fields"}
        return {"status": "incomplete", "missing_fields": list(missing)}
    return {"status": "fallback", "reason": "unsupported_status"}


def interpret_trip_request(message: str, *, submitted_at: str, supported_values: dict,
                           transport=post_to_local_ollama) -> dict:
    """UC.1.2 Interpret and Confirm Trip Request: one model call through the adapter.

    submitted_at: offset-aware ISO 8601 request submission time.
    supported_values: {"destinations", "vehicle_categories", "eligibility_values"}.
    transport: callable(body, timeout) -> Ollama response dict; injectable for tests.
    """
    if len(message) > MAX_MESSAGE_CHARACTERS:
        return {"status": "fallback", "reason": "message_too_long"}
    try:
        reply = transport(build_request(message, submitted_at, supported_values), TIMEOUT_SECONDS)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {"status": "fallback", "reason": "model_unavailable"}
    if not isinstance(reply, dict) or not isinstance(reply.get("message"), dict):
        return {"status": "fallback", "reason": "malformed_json"}
    if reply.get("done_reason") == "length":
        return {"status": "fallback", "reason": "output_truncated"}
    return validate_model_output(reply["message"].get("content"), submitted_at, supported_values)
