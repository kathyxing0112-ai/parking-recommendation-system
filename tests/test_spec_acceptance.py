"""Chapter 3 red acceptance suite, traced to SPEC.md.

Each test corresponds to one need-to-requirement acceptance criterion.
These failures are intentional until later chapters implement the behavior.
"""


def test_SN01_SR01_mobility_value_against_static_baseline():
    assert False, "SR-01: pilot comparison and search-time improvement not implemented"


def test_SN02_SR02_only_approved_data_sources_are_used():
    assert False, "SR-02: source inventory and permission checks not implemented"


def test_SN02_SR03_role_permissions_block_prohibited_operations():
    assert False, "SR-03: access-control enforcement not implemented"


def test_SN02_SR04_pilot_trip_records_expire_within_24_hours():
    assert False, "SR-04: 24-hour deletion and storage inspection not implemented"


def test_SN03_SR05_requirements_baseline_is_traceable():
    assert False, "SR-05: versioned baseline and PR trace review not implemented"


def test_SN04_SR06_handoff_tasks_complete_without_author_help():
    assert False, "SR-06: five-task independent handoff not implemented"


def test_SN04_SR07_each_pilot_activity_has_an_owner():
    assert False, "SR-07: responsibility matrix and owner check not implemented"


def test_SN05_SR08_parking_status_is_fresh():
    assert False, "SR-08: 30/60/120-second freshness behavior not implemented"


def test_SN05_SR09_stale_observations_are_labeled():
    assert False, "SR-09: stale boundary and label not implemented"


def test_SN06_SR10_recommendations_follow_confirmed_rules():
    assert False, "SR-10: permit, accessibility, closure, and time rules not implemented"


def test_SN07_SR08_drivers_see_fresh_parking_status():
    assert False, "SR-08: driver-facing freshness evidence not implemented"


def test_SN07_SR09_drivers_recognize_stale_status():
    assert False, "SR-09: driver stale-information recognition not evaluated"


def test_SN07_SR11_drivers_interpret_parking_information():
    assert False, "SR-11: usability task success not evaluated"


def test_SN07_SR15_drivers_understand_recommendation_reasons():
    assert False, "SR-15: explanation comprehension not evaluated"


def test_SN08_SR10_returned_options_are_policy_eligible():
    assert False, "SR-10: policy filter before ranking not implemented"


def test_SN08_SR12_six_trip_fields_are_confirmed_and_validated():
    assert False, "SR-12: six-field request validation not implemented"


def test_SN08_SR13_primary_and_backup_are_ranked_within_five_seconds():
    assert False, "SR-13: ranked primary/backup and timing not implemented"


def test_SN08_SR14_arrival_forecasts_are_valid_and_evaluated():
    assert False, "SR-14: forecast validity and holdout evaluation not implemented"


def test_SN08_SR15_returned_options_have_faithful_explanations():
    assert False, "SR-15: explanations tied to actual ranking factors not implemented"
