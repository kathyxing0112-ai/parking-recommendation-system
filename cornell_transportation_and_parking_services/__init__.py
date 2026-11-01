"""Cornell Transportation and Parking Services (X.C.4).

Walking-skeleton participant for UC.1.8 Request / UC.1.9 Provide Parking Rules
and Closures.

parking_rules_draft.json is a DRAFT rule table in the SPEC Data Contract
section 4 shape, built from public Cornell pages plus labeled simulator
assumptions. It is not Cornell policy and is not confirmed (SR-10); the C.1.4
Eligibility Filter Module reads it through get_rule_table().
"""

import json
from pathlib import Path

RULE_TABLE_PATH = Path(__file__).with_name("parking_rules_draft.json")


def get_rule_table() -> dict:
    """The draft section 4 rule table: {"version", "status", "conventions", "rules"}."""
    return json.loads(RULE_TABLE_PATH.read_text(encoding="utf-8"))


def get_parking_rules_and_closures(declared_eligibility: str, access_needs: bool) -> list:
    """Stub: hard-coded, synthetic values of the right shape.

    The values do not represent real Cornell parking policy. Replaced when
    C.1.4 applies get_rule_table() (K6).
    """
    return [
        {"lot_id": "LOT-1", "eligible": True, "closure": False},
        {"lot_id": "LOT-3", "eligible": True, "closure": False},
    ]
