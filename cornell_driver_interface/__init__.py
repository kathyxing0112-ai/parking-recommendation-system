"""Cornell Driver Interface — the driver-facing component of the SoI.

Internal to the system-of-interest: the Cornell Driver (X.C.1) is a person, so
the repository holds the system's interface to that actor. Each function is
one driver-facing message in the updated UC.1 sequence diagram.
"""

import smart_parking_service as service


def submit_trip_request(message: str) -> dict:
    """UC.1.1 Submit Trip Request -> UC.1.2 Interpret and Confirm Trip Request."""
    return service.interpret_trip_request(message)


def confirm_trip_requirements(trip_request: dict) -> dict:
    """UC.1.3 Confirm Trip Requirements -> UC.1.14 Present Ranked Parking Recommendations."""
    return service.find_suitable_parking(trip_request)


def select_parking_option(recommendations: dict, lot_id: str) -> dict:
    """UC.1.16 Select Parking Option -> UC.1.17 Present Selected Parking Information."""
    return service.get_selected_parking_information(recommendations, lot_id)


def request_pre_arrival_recheck(lot_id: str) -> dict:
    """UC.1.18 Request Pre-Arrival Status Recheck -> UC.1.21 Present Updated Parking Status."""
    return service.recheck_parking_status(lot_id)
