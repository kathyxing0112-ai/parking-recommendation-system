"""Smart Parking Service — the orchestration layer of the SoI.

Internal to the system-of-interest. The system context diagram shows the
Smart Parking System (C.0) as a single element; this module is the component
that coordinates the request inside it.

Walking-skeleton participant. This is the one participant that is not a dead
end: it calls the other stubs in the order given in docs/walking-skeleton.md
and returns what they give it, so a single driver action traverses the whole
path. Calls 2 through 11.
"""

from contextual_information_sources import get_contextual_information
from cornell_transportation_and_parking_services import (
    get_parking_policy_constraints,
)
from parking_availability_data_sources import get_current_parking_availability
from recommendation_model import compose_recommendation_explanation

def find_suitable_parking(trip_request: dict) -> dict:
    """Traverse every participant once and return a stubbed response."""
    parking_availability = get_current_parking_availability(
        trip_request["destination"]
    )
    contextual_information = get_contextual_information(
        trip_request["destination"]
    )
    policy_constraints = get_parking_policy_constraints(
        trip_request["parking_eligibility"]
    )

    # Hard-coded value of the shape call 10 of the sequence diagram asks for
    # ("return ranked parking recommendations"). This is a stubbed response,
    # not a ranking computed from the availability data above: no ranking
    # algorithm is specified yet.
    ranked_options = [{"rank": 1, "lot_id": "LOT-1", "available_spaces": 10}]

    explanation = compose_recommendation_explanation(ranked_options)

    return {
        "destination": trip_request["destination"],
        "ranked_options": ranked_options,
        "parking_availability": parking_availability,
        "contextual_information": contextual_information,
        "policy_constraints": policy_constraints,
        "explanation": explanation,
        "data_mode": "synthetic",
    }
