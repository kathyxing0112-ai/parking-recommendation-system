"""Language model adapter -- part of C.1.1 Trip Request Interpretation Module.

Calls the local language model recorded in docs/environment.md (Qwen3 4B
hosted through Ollama). Per ADR-0002 the model only interprets a driver's
chatbot message. It does not predict availability, check eligibility, rank
parking areas, or write explanations.

The model copies the six fields from the message, with null for any field the
driver did not state and clock times as "HH:MM". The adapter then checks each
value and assembles the SPEC.md Model Response Contract object: "complete"
with the six-field trip request, or "incomplete" with the fields that passed
and the missing fields.
A reply that is not a JSON object with exactly the six fields is discarded
and reported as {"status": "fallback", "reason": ...}; the application then
presents the six-field form. The prompt template, parameters, timeout, token
limits and reply format are specified in docs/model-adapter.md. Raw messages
and raw model output are never logged or stored (SR-04).
"""

import json
import re
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
CLOCK_TIME = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")
# Field -> supported_values key, for the three fields checked against approved lists.
LISTED_FIELDS = {
    "destination": "destinations",
    "vehicle_category": "vehicle_categories",
    "declared_eligibility": "eligibility_values",
}
ELIGIBILITY_MEANINGS = {
    "permit_O": "the driver holds an O permit",
    "visitor": "visitor or hourly parking",
}

SYSTEM_PROMPT = """You read one driver's parking request for a campus parking system and reply with one JSON object with exactly these keys: destination, arrival_time, departure_time, vehicle_category, declared_eligibility, access_needs.
Rules:
- Use null for any field the driver did not state. Never guess or fill in a typical value.
- destination, vehicle_category, declared_eligibility: if the driver's words clearly name one of the supported values listed below, write that supported value exactly. Otherwise copy the driver's own words unchanged. Never replace the driver's words with a different supported value. For declared_eligibility, a permit counts only if the driver names that exact permit; any other permit type is copied as written.
- arrival_time and departure_time: local clock time "HH:MM", 24-hour. Convert am/pm ("3:30 pm" -> "15:30"). If the driver gives no am/pm or morning/afternoon/evening word, write the hour exactly as given ("3:40" -> "03:40"). If the driver gives a length of stay instead of a departure time, add it to the arrival time.
- access_needs: true if the driver asks for accessible parking, false if the driver says it is not needed, otherwise null."""

USER_PROMPT_TEMPLATE = """Current local date and time: {local_now} (UTC{utc_offset})
Supported destinations: {destinations}
Supported vehicle categories: {vehicle_categories}
Supported eligibility values: {eligibility_values}
Meaning of eligibility values: {eligibility_meanings}
Driver message: {message}"""

_NULLABLE_STRING = {"type": ["string", "null"]}
# The model's reply format (docs/model-adapter.md). It is not the Model Response
# Contract: the adapter assembles the contract object from it.
RESPONSE_FORMAT = {
    "type": "object",
    "properties": {
        "destination": _NULLABLE_STRING,
        "arrival_time": _NULLABLE_STRING,
        "departure_time": _NULLABLE_STRING,
        "vehicle_category": _NULLABLE_STRING,
        "declared_eligibility": _NULLABLE_STRING,
        "access_needs": {"type": ["boolean", "null"]},
    },
    "required": list(REQUIRED_FIELDS),
}


def build_request(message: str, submitted_at: str, supported_values: dict) -> dict:
    """The Ollama /api/chat request body the adapter sends."""
    submitted = datetime.fromisoformat(submitted_at)
    offset = submitted.strftime("%z")
    user_prompt = USER_PROMPT_TEMPLATE.format(
        local_now=submitted.strftime("%Y-%m-%d %H:%M"),
        utc_offset=f"{offset[:3]}:{offset[3:]}",
        destinations=", ".join(supported_values["destinations"]),
        vehicle_categories=", ".join(supported_values["vehicle_categories"]),
        eligibility_values=", ".join(supported_values["eligibility_values"]),
        eligibility_meanings="; ".join(f"{value} = {ELIGIBILITY_MEANINGS[value]}"
                                       for value in supported_values["eligibility_values"]
                                       if value in ELIGIBILITY_MEANINGS),
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


def _listed_value(value, allowed: list[str]) -> str | None:
    """The approved spelling of value, or None if it is not on the approved list."""
    if not isinstance(value, str):
        return None
    matches = [item for item in allowed if item.casefold() == value.strip().casefold()]
    return matches[0] if matches else None


def _clock_time_on(day: datetime, value) -> datetime | None:
    """value "HH:MM" on day's date, with day's UTC offset."""
    if not isinstance(value, str):
        return None
    match = CLOCK_TIME.fullmatch(value.strip())
    if match is None:
        return None
    return day.replace(hour=int(match[1]), minute=int(match[2]), second=0, microsecond=0)


def assemble_contract(content: str, submitted_at: str, supported_values: dict) -> dict:
    """Turn the model's reply into the Model Response Contract object.

    A field the model left null, or whose value fails its Data Contract
    section 5 check, is listed in missing_fields; the driver supplies it on the
    confirmation step. access_needs left null becomes false (SPEC.md Model
    Response Contract); any other non-boolean access_needs is missing. Returns {"status": "fallback", "reason": ...} only when
    the reply is not a JSON object with exactly the six fields.
    """
    try:
        reply = json.loads(content)
    except (TypeError, ValueError):
        return {"status": "fallback", "reason": "malformed_json"}
    if not isinstance(reply, dict):
        return {"status": "fallback", "reason": "malformed_json"}
    if set(reply) != set(REQUIRED_FIELDS):
        return {"status": "fallback", "reason": "wrong_fields"}

    submitted = datetime.fromisoformat(submitted_at).replace(second=0, microsecond=0)
    trip = {}
    for field, list_key in LISTED_FIELDS.items():
        trip[field] = _listed_value(reply[field], supported_values[list_key])

    arrival = _clock_time_on(submitted, reply["arrival_time"])
    if arrival is not None and not submitted <= arrival <= submitted + ARRIVAL_WINDOW:
        arrival = None
    departure = _clock_time_on(arrival, reply["departure_time"]) if arrival is not None else None
    if departure is not None and departure <= arrival:
        departure = None
    trip["arrival_time"] = arrival.isoformat() if arrival is not None else None
    trip["departure_time"] = departure.isoformat() if departure is not None else None

    # Only an unstated value (null) defaults to false. A value of the wrong
    # type is not "no accessible need": the driver is asked for it instead.
    access = reply["access_needs"]
    trip["access_needs"] = False if access is None else access if isinstance(access, bool) else None

    missing = [field for field in REQUIRED_FIELDS if trip[field] is None]
    if missing:
        known = {field: trip[field] for field in REQUIRED_FIELDS if trip[field] is not None}
        return {"status": "incomplete", "trip_request": known, "missing_fields": missing}
    return {"status": "complete", "trip_request": {field: trip[field] for field in REQUIRED_FIELDS}}


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
    return assemble_contract(reply["message"].get("content"), submitted_at, supported_values)
