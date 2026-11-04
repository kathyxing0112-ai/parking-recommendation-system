"""Cornell Transportation and Parking Services (X.C.4).

Walking-skeleton participant for UC.1.8 Request / UC.1.9 Provide Parking Rules
and Closures.

parking_rules.json is the team-confirmed rule table (SR-10) in the SPEC Data
Contract section 4 shape, built from public Cornell pages plus labeled
simulator assumptions. It is not Cornell policy. The C.1.4 Eligibility Filter
Module reads it through get_rule_table().
"""

import json
from pathlib import Path

RULE_TABLE_PATH = Path(__file__).with_name("parking_rules.json")


def get_rule_table() -> dict:
    """The section 4 rule table: {"version", "status", "conventions", "rules"}."""
    return json.loads(RULE_TABLE_PATH.read_text(encoding="utf-8"))


def get_parking_rules_and_closures(declared_eligibility: str, access_needs: bool) -> dict:
    """UC.1.9 Provide Parking Rules and Closures: the confirmed rule table.

    A1.4 picks the rules that apply to the trip, so the whole table is returned.
    The values do not represent real Cornell parking policy.
    """
    table = get_rule_table()
    return {"version": table["version"], "rules": table["rules"]}
