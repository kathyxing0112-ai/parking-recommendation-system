"""Contextual Information Sources (X.C.3).

Walking-skeleton participant for UC.1.6 Request / UC.1.7 Provide Context
Information.
"""


def get_contextual_information(destination: str) -> list:
    """Stub: hard-coded, synthetic walking times of the right shape."""
    return [
        {"lot_id": "LOT-1", "walking_time_minutes": 5},
        {"lot_id": "LOT-2", "walking_time_minutes": 9},
    ]
