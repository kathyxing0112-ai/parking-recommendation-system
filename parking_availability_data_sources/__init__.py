"""Parking Availability Data Sources (X.C.2).

Walking-skeleton participant for UC.1.4 / UC.1.5 (current availability) and
UC.1.19 / UC.1.20 (updated availability before arrival).
"""


def get_current_parking_availability(destination: str) -> list:
    """UC.1.4 Request / UC.1.5 Provide Current Parking Availability.

    Stub: hard-coded, synthetic values of the right shape.
    """
    return [
        {"lot_id": "LOT-1", "available_spaces": 10, "observed_at": "2026-10-01T09:30:00-04:00"},
        {"lot_id": "LOT-2", "available_spaces": 4, "observed_at": "2026-10-01T09:30:00-04:00"},
    ]


def get_updated_parking_availability(lot_id: str) -> dict:
    """UC.1.19 Request / UC.1.20 Provide Updated Parking Availability.

    Stub: hard-coded, synthetic value of the right shape.
    """
    return {"lot_id": lot_id, "available_spaces": 8, "observed_at": "2026-10-01T09:50:00-04:00"}
