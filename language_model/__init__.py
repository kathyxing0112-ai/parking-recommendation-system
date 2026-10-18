"""Language Model — internal to the system-of-interest.

Stands in for the local language model recorded in docs/environment.md
(Qwen3 4B hosted through Ollama). Per ADR-0002, the model only interprets a
driver's chatbot message into the six-field trip request defined in SPEC.md
(Model Response Contract). It does not predict availability, check
eligibility, rank parking areas, or write explanations.

Walking-skeleton participant for UC.1.2 Interpret and Confirm Trip Request.
No real model call is made in this increment.
"""


def interpret_trip_request(message: str) -> dict:
    """Stub: return a hard-coded response in the Model Response Contract shape.

    The values are synthetic and are not derived from ``message``.
    """
    return {
        "status": "complete",
        "trip_request": {
            "destination": "Duffield Hall",
            "arrival_time": "2026-10-01T10:00:00-04:00",
            "departure_time": "2026-10-01T12:00:00-04:00",
            "vehicle_category": "sedan",
            "declared_eligibility": "permit_O",
            "access_needs": False,
        },
    }
