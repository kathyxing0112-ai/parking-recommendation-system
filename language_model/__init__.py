"""Language model adapter -- part of C.1.1 Trip Request Interpretation Module.

Calls the local language model recorded in docs/environment.md (Qwen3 4B
hosted through Ollama). Per ADR-0002 the model only interprets a driver's
chatbot message. It does not predict availability, check eligibility, rank
parking areas, or write explanations.

The model copies the six fields from the message, with null for any field the
driver did not state, and times as a day word copied from the driver's words
plus "HH:MM" ("tomorrow 09:00", "Monday 10:30", "Nov 24 08:15"). The adapter,
not the model, turns the day word into a date. The adapter then checks each
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

from stage_timing import stage

# Local only: the endpoint is the loopback address, so no project data leaves the machine.
OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen3:4b"
TIMEOUT_SECONDS = 60
# How long Ollama keeps the model in memory after a request (its default is
# 5 minutes). A model that has been unloaded takes seconds to load again, so
# the first driver after a quiet spell waited 4-6 s instead of about 2 s
# (Chapter 10 measurements, docs/measured-behavior.md).
KEEP_ALIVE = "30m"
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
ARRIVAL_WINDOW = timedelta(hours=72)  # SPEC Data Contract section 5 (SR-12)
# An optional day word, then "HH:MM". A 4B model did not copy dates from a
# list reliably (4 of 10 named days right on 2026-11-21) but did copy the
# driver's day words (10 of 11), so the adapter computes the date.
TRIP_TIME = re.compile(r"(?:(.+?) )?([01][0-9]|2[0-3]):([0-5][0-9])")
DAY_OFFSETS = {"today": 0, "tonight": 0, "tomorrow": 1, "day after tomorrow": 2}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
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
- arrival_time and departure_time: a day word, a space, then the clock time "HH:MM", 24-hour. The day word is "today", "tomorrow", "day after tomorrow", a weekday name such as "Monday", or a month and day such as "Nov 24", copied from the driver's words; write "today" if the driver names no day. Convert am/pm ("3:30 pm" -> "15:30"; "7 in the evening" -> "19:00"). If the driver gives no am/pm or morning/afternoon/evening word, write the hour exactly as given ("3:40" -> "03:40"). If the driver gives a length of stay instead of a departure time, add it to the arrival time. Examples: "tomorrow 09:00", "day after tomorrow 13:00", "Monday 10:30", "Nov 24 08:15", "today 16:30".
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
        local_now=submitted.strftime("%A %Y-%m-%d %H:%M"),
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
        "keep_alive": KEEP_ALIVE,
    }


WARM_UP_MESSAGE = "warm up"


def warm_up_model(supported_values: dict, transport=None, timeout: float = TIMEOUT_SECONDS) -> bool:
    """Run one full request before the first driver arrives, and discard the reply.

    Loading the weights alone (a request with no messages) left the first real
    request at about 3.5 s; one complete request with the product's own prompt
    and reply format brought it to about 2.1 s, the warm time (2026-11-15).
    Called once when the product starts. Returns False if the model is not
    reachable; the product still works, and the first request then loads the
    model itself or falls back to the form.
    """
    transport = transport or post_to_local_ollama
    submitted_at = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        transport(build_request(WARM_UP_MESSAGE, submitted_at, supported_values), timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return False
    return True


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


def _date_of(word: str | None, submitted: datetime):
    """The date a day word names, counted from the submission date, or None.

    No word or "today"/"tonight" is the submission date; a weekday name is the
    next date with that weekday (the same weekday is today); "Nov 24" is that
    date in the submission year, or the next year if it has passed.
    """
    today = submitted.date()
    word = (word or "today").strip().casefold().rstrip(",")
    if word in DAY_OFFSETS:
        return today + timedelta(days=DAY_OFFSETS[word])
    for index, name in enumerate(WEEKDAYS):
        if word in (name, name[:3]):
            return today + timedelta(days=(index - today.weekday()) % 7)
    match = re.fullmatch(r"([a-z]+)\.? (\d{1,2})", word)
    if match and match[1][:3] in MONTHS:
        for year in (today.year, today.year + 1):
            try:
                day = today.replace(year=year, month=MONTHS.index(match[1][:3]) + 1, day=int(match[2]))
            except ValueError:              # not a calendar date, such as Nov 31
                return None
            if day >= today:
                return day
    return None


def _trip_time(value, submitted: datetime, after: datetime | None = None) -> datetime | None:
    """value ("<day word> HH:MM" or "HH:MM") as an offset-aware time, or None.

    A departure (after = the arrival) with no day word is on the arrival's
    date; on the arrival's date but earlier than it, it is read as the next
    day (arrive 23:30, leave 01:00). An arrival with no
    day word that is earlier than the submission minute is read as tomorrow.
    The UTC offset is the submission's: within 72 hours that is the local
    offset except across a daylight-saving change (the next one after the
    pilot term is 2027-03-14).
    """
    if not isinstance(value, str):
        return None
    match = TRIP_TIME.fullmatch(value.strip())
    if match is None:
        return None
    word, hour, minute = match.groups()
    date = after.date() if after is not None and word is None else _date_of(word, submitted)
    if date is None:
        return None
    at = submitted.replace(year=date.year, month=date.month, day=date.day,
                           hour=int(hour), minute=int(minute), second=0, microsecond=0)
    if after is not None and at.date() == after.date() and at < after:
        at += timedelta(days=1)
    if after is None and word is None and at < submitted:
        at += timedelta(days=1)
    return at


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

    arrival = _trip_time(reply["arrival_time"], submitted)
    if arrival is not None and not submitted <= arrival <= submitted + ARRIVAL_WINDOW:
        arrival = None
    departure = _trip_time(reply["departure_time"], submitted, after=arrival) if arrival is not None else None
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
        with stage("C.1.1.model_call"):
            reply = transport(build_request(message, submitted_at, supported_values), TIMEOUT_SECONDS)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return {"status": "fallback", "reason": "model_unavailable"}
    if not isinstance(reply, dict) or not isinstance(reply.get("message"), dict):
        return {"status": "fallback", "reason": "malformed_json"}
    if reply.get("done_reason") == "length":
        return {"status": "fallback", "reason": "output_truncated"}
    with stage("C.1.1.contract_check"):
        return assemble_contract(reply["message"].get("content"), submitted_at, supported_values)
