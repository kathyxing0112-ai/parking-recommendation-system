"""Cornell Driver Interface — the driver-facing component of the SoI.

Internal to the system-of-interest: the Cornell Driver (X.C.1) is a person, so
what the repository holds is the system's interface to that actor, following
the pattern used for boundary elements in Chapter 1.

Walking-skeleton participant. Calls 1, 2, 11, and 12 of
docs/walking-skeleton.md.
"""

from smart_parking_service import find_suitable_parking


def submit_trip_request(trip_request: dict) -> dict:
    """Forward a trip request and return the ranked parking recommendations."""
    return find_suitable_parking(trip_request)
