"""The draft parking-rule table matches the SPEC Data Contract section 4 shape.

These tests check the table's structure only. Whether a rule is correct
policy is a team review question, not a test (SR-10).
"""

import re
from datetime import date

import pytest

from cornell_transportation_and_parking_services import get_rule_table
from parking_availability_data_sources import get_lot_inventory

SECTION_4_FIELDS = {
    "rule_id", "version", "lot_id", "zone", "eligibility_class",
    "valid_from", "valid_until", "time_zone",
    "days_of_week", "start_local_time", "end_local_time",
    "allowed", "closure", "source", "owner", "reviewed_at",
}
TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]|24:00")
RULES = get_rule_table()["rules"]


def test_table_is_labeled_as_unconfirmed_draft():
    table = get_rule_table()
    assert "DRAFT" in table["status"] and "Not Cornell policy" in table["status"]


def test_rule_ids_are_unique():
    assert len({rule["rule_id"] for rule in RULES}) == len(RULES)


@pytest.mark.parametrize("rule", RULES, ids=[rule["rule_id"] for rule in RULES])
def test_rule_has_section_4_fields_and_valid_values(rule):
    assert set(rule) == SECTION_4_FIELDS
    lots = {lot["lot_id"]: lot for lot in get_lot_inventory()}
    assert rule["lot_id"] in lots
    # A rule names a zone only where that lot actually has spaces in it.
    assert rule["zone"] == "*" or lots[rule["lot_id"]]["capacity_by_zone"].get(rule["zone"], 0) > 0
    assert rule["eligibility_class"] in {"*", "permit_O", "visitor", "accessible"}
    assert date.fromisoformat(rule["valid_from"]) <= date.fromisoformat(rule["valid_until"])
    assert rule["days_of_week"] and set(rule["days_of_week"]) <= set(range(1, 8))
    assert TIME.fullmatch(rule["start_local_time"]) and TIME.fullmatch(rule["end_local_time"])
    assert isinstance(rule["allowed"], bool) and isinstance(rule["closure"], bool)
    assert not (rule["closure"] and rule["allowed"])
    assert rule["source"] and rule["owner"]
