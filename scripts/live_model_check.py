"""Live check of the C.1.1 model adapter against the local Qwen3 4B model.

The pytest suite replaces the model with a fake transport, so it never shows
what the real model returns. This script sends a fixed set of simulated
driver messages through the real adapter to the local Ollama server and
prints, for each message:

- the driver message,
- the model's raw reply,
- the adapter result (complete, incomplete with the missing fields, or fallback
  to the six-field form),
- whether that result is what the message should give.

It is a manual check, not part of CI: CI has no Ollama (docs/deployment.md).
Model output can vary between Ollama versions, so record the date, Ollama
version and summary in docs/prompt-log.md when you use a run as evidence.

All messages are simulated. Raw output is printed to this terminal only and
is never written to disk (SR-04).

Usage, from the repository root, with Ollama running and qwen3:4b pulled:

    python scripts/live_model_check.py
    python scripts/live_model_check.py --message "Gates Hall at 3:30 until 5, sedan, visitor, no accessible parking"
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import language_model  # noqa: E402
from smart_parking_service import PROVISIONAL_SUPPORTED_VALUES  # noqa: E402

# Fixed so expected times are reproducible; the arrival window is checked against this.
# After the 2026-11-01 daylight-saving change, so the offset is -05:00.
SUBMITTED_AT = "2026-11-02T15:00:00-05:00"


def _trip(destination, arrival, departure, vehicle, eligibility, access):
    return {
        "destination": destination,
        "arrival_time": f"2026-11-02T{arrival}:00-05:00",
        "departure_time": f"2026-11-02T{departure}:00-05:00",
        "vehicle_category": vehicle,
        "declared_eligibility": eligibility,
        "access_needs": access,
    }


# Four ordinary messages, then two non-standard ones whose values are not on
# the approved lists. expect is the result a correct interpretation gives:
#   {"complete": trip}      -- must be complete with exactly these values
#   {"missing": [fields]}   -- must be incomplete and list exactly these fields
CASES = [
    {
        "name": "full_request",
        "message": "I'm heading to Duffield Hall, arriving around 3:30 pm today and leaving at 6 pm. "
                   "I drive a sedan, I have an O permit, and I don't need accessible parking.",
        "expect": {"complete": _trip("Duffield Hall", "15:30", "18:00", "sedan", "permit_O", False)},
    },
    {
        "name": "length_of_stay",
        "message": "Visitor here, driving an SUV to Upson Hall. I'll get there at 3:45pm and stay two hours. "
                   "I need an accessible space.",
        "expect": {"complete": _trip("Upson Hall", "15:45", "17:45", "suv", "visitor", True)},
    },
    {
        "name": "destination_only",
        "message": "I need parking near Gates Hall soon.",
        "expect": {"missing": ["arrival_time", "departure_time", "vehicle_category", "declared_eligibility"]},
    },
    {
        "name": "departure_not_stated",
        "message": "Sedan with a visitor pass, going to Gates Hall at 3:40 pm, no accessibility needs.",
        "expect": {"missing": ["departure_time"]},
    },
    {
        "name": "unsupported_destination",
        "message": "Going to Statler Hall at 3:30pm until 5pm, sedan, O permit, no accessible parking needed.",
        "expect": {"missing": ["destination"]},
    },
    {
        "name": "unapproved_permit",
        "message": "Upson Hall at 3:30 pm till 5 pm, SUV, I have a faculty CU permit, no accessibility needs.",
        "expect": {"missing": ["declared_eligibility"]},
    },
]


def judge(result: dict, case: dict) -> bool:
    expect = case["expect"]
    if "complete" in expect:
        return result == {"status": "complete", "trip_request": expect["complete"]}
    return result["status"] == "incomplete" and result["missing_fields"] == expect["missing"]


def model_is_ready() -> bool:
    tags_url = language_model.OLLAMA_CHAT_URL.replace("/api/chat", "/api/tags")
    try:
        with urllib.request.urlopen(tags_url, timeout=5) as response:
            models = [m["name"] for m in json.loads(response.read())["models"]]
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        print(f"Ollama is not reachable at {tags_url}. Start it with: brew services start ollama")
        return False
    if language_model.MODEL_NAME not in models:
        print(f"{language_model.MODEL_NAME} is not pulled. Run: ollama pull {language_model.MODEL_NAME}")
        return False
    return True


def run(name: str, message: str) -> dict:
    """One adapter call; returns the adapter result plus the raw reply and timing."""
    raw = {}

    def recording_transport(body, timeout):
        reply = language_model.post_to_local_ollama(body, timeout)
        raw.update(reply)
        return reply

    start = time.perf_counter()
    result = language_model.interpret_trip_request(
        message, submitted_at=SUBMITTED_AT, supported_values=PROVISIONAL_SUPPORTED_VALUES,
        transport=recording_transport)
    seconds = time.perf_counter() - start
    content = raw.get("message", {}).get("content", "(no reply)")
    print(f"\n== {name} ({seconds:.1f} s)")
    print(f"Driver message : {message}")
    print(f"Model raw reply: {' '.join(str(content).split())}")
    print(f"Adapter result : {json.dumps(result, ensure_ascii=False)}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--message", help="send one message of your own instead of the fixed cases")
    args = parser.parse_args()

    if not model_is_ready():
        return 1
    print(f"Model {language_model.MODEL_NAME} at {language_model.OLLAMA_CHAT_URL}")
    print(f"Submitted at {SUBMITTED_AT}; supported values: "
          f"{json.dumps(PROVISIONAL_SUPPORTED_VALUES, ensure_ascii=False)}")

    if args.message:
        run("your_message", args.message)
        return 0

    as_expected = 0
    for case in CASES:
        result = run(case["name"], case["message"])
        ok = judge(result, case)
        as_expected += ok
        print(f"Expected       : {json.dumps(case['expect'], ensure_ascii=False)}")
        print(f"Verdict        : {'as expected' if ok else 'NOT as expected'}")

    print(f"\nSummary: {as_expected} of {len(CASES)} messages gave the expected result.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
