"""Cornell Transportation and Parking Services (X.C.4).

Walking-skeleton participant for UC.1.8 Request / UC.1.9 Provide Parking Rules
and Closures.
"""


def get_parking_rules_and_closures(declared_eligibility: str, access_needs: bool) -> list:
    """Stub: hard-coded, synthetic values of the right shape.

    The values do not represent real Cornell parking policy.
    """
    return [
        {"lot_id": "LOT-1", "eligible": True, "closure": False},
        {"lot_id": "LOT-2", "eligible": True, "closure": False},
    ]
