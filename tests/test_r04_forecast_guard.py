"""R-04 (docs/risks.md): unsupported availability estimates must not drive ranking or display.

Failure-path tests for the guardrail between A2 and A3
(smart_parking_service.guard_forecasts). Each test feeds one kind of bad A2
output and checks that the estimate is withheld, the lot is marked
"unsupported", and A3 falls back to walking time (SR-13). The last two run the
whole UC.1 flow with a corrupted A2 to check that ranking and the page both
drop the estimate.
"""

from datetime import datetime, timedelta

import pytest

import cornell_driver_interface as driver_interface
import smart_parking_service as service
from rank_parking_options import rank_parking_options

NOW = datetime.fromisoformat("2026-10-07T10:30:30-04:00")
OBSERVED_AT = "2026-10-07T10:30:00-04:00"
ARRIVAL = "2026-10-07T11:00:00-04:00"
TRIP = {"arrival_time": ARRIVAL}
ELIGIBLE = [{"lot_id": "LOT-1"}, {"lot_id": "LOT-2"}]
OBSERVED = [{"lot_id": "LOT-1", "occupied": 150, "capacity": 200, "observed_at": OBSERVED_AT},
            {"lot_id": "LOT-2", "occupied": 60, "capacity": 120, "observed_at": OBSERVED_AT}]
CURRENT = {"LOT-1": "current", "LOT-2": "current"}
WALKING = [{"lot_id": "LOT-1", "walking_time_minutes": 4}, {"lot_id": "LOT-2", "walking_time_minutes": 9}]
RULES = {"weights": {"walking_time": 0.4, "availability": 0.4, "uncertainty": 0.2}}


def estimate(lot_id="LOT-1", **changes):
    capacity = 200 if lot_id == "LOT-1" else 120
    good = {"lot_id": lot_id, "capacity": capacity, "available_spaces": 40, "interval_lower": 30,
            "interval_upper": 52, "interval_level": 0.8, "forecast_time": OBSERVED_AT,
            "arrival_time": ARRIVAL, "lead_minutes": 30, "method": "lightgbm", "long_range": False,
            "data_mode": "simulated"}
    return {**good, **changes}


def a2_output(lot_1, lot_2=None, status=None):
    estimates = [e for e in (lot_1, lot_2 or estimate("LOT-2")) if e is not None]
    return {"arrival_time_availability_estimates": estimates,
            "forecast_validity_status": status or {"LOT-1": "supported", "LOT-2": "supported"}}


def guard(forecast, freshness=CURRENT, now=NOW, observed=OBSERVED):
    return service.guard_forecasts(forecast, TRIP, ELIGIBLE, observed, freshness, now)


def rank(guarded):
    return rank_parking_options(TRIP, WALKING, ELIGIBLE, CURRENT,
                                guarded["arrival_time_availability_estimates"],
                                guarded["forecast_validity_status"], ranking_and_fallback_rules=RULES)


def test_valid_estimates_pass_and_are_ranked_by_score():
    guarded = guard(a2_output(estimate()))
    assert guarded["withheld"] == {}
    assert len(guarded["arrival_time_availability_estimates"]) == 2
    assert {o["ranking_basis"] for o in rank(guarded)} == {"score"}


BAD_ESTIMATES = {
    "other_arrival_time": estimate(arrival_time="2026-10-07T13:00:00-04:00"),
    "other_observation": estimate(forecast_time="2026-10-07T10:20:00-04:00"),
    "capacity_mismatch": estimate(capacity=210, interval_upper=52),
    "bounds_inconsistent": estimate(interval_lower=45),            # lower above the estimate
    "not_whole_numbers": estimate(available_spaces=40.5),
    "wrong_interval_level": estimate(interval_level=0.95),
    "lead_out_of_range": estimate(forecast_time="2026-10-07T11:30:00-04:00"),
}


@pytest.mark.parametrize("reason", sorted(BAD_ESTIMATES))
def test_inconsistent_estimate_is_withheld_and_ranking_falls_back(reason):
    observed = OBSERVED
    if reason == "lead_out_of_range":   # observation after the arrival: forecast_time matches it
        observed = [{**OBSERVED[0], "observed_at": "2026-10-07T11:30:00-04:00"}, OBSERVED[1]]
    guarded = guard(a2_output(BAD_ESTIMATES[reason]), observed=observed,
                    now=NOW if reason != "lead_out_of_range" else NOW + timedelta(hours=1))
    assert guarded["withheld"]["LOT-1"] == reason
    assert guarded["forecast_validity_status"]["LOT-1"] == "unsupported"
    assert "LOT-1" not in {e["lot_id"] for e in guarded["arrival_time_availability_estimates"]}
    assert {o["ranking_basis"] for o in rank(guarded)} == {"fallback_walking_time"}


def test_boolean_is_not_accepted_as_a_count():
    guarded = guard(a2_output(estimate(capacity=True, available_spaces=True, interval_lower=0,
                                       interval_upper=True)))
    assert guarded["withheld"]["LOT-1"] == "not_whole_numbers"


def test_estimate_without_supported_status_is_withheld():
    guarded = guard(a2_output(estimate(), status={"LOT-2": "supported"}))   # LOT-1 status missing
    assert guarded["withheld"]["LOT-1"] == "status_not_supported"
    assert guarded["forecast_validity_status"]["LOT-1"] == "unsupported"


def test_two_estimates_for_one_lot_are_both_withheld():
    forecast = a2_output(estimate())
    forecast["arrival_time_availability_estimates"].append(estimate(available_spaces=45))
    guarded = guard(forecast)
    assert guarded["withheld"]["LOT-1"] == "duplicate_estimates"


def test_estimate_for_a_lot_that_is_not_eligible_is_dropped():
    forecast = a2_output(estimate(), status={"LOT-1": "supported", "LOT-2": "supported",
                                             "LOT-3": "supported"})
    forecast["arrival_time_availability_estimates"].append(estimate("LOT-3", capacity=150))
    guarded = guard(forecast)
    assert guarded["withheld"]["LOT-3"] == "lot_not_eligible"
    assert "LOT-3" not in {e["lot_id"] for e in guarded["arrival_time_availability_estimates"]}


def test_stale_observation_marked_supported_is_withheld():
    guarded = guard(a2_output(estimate()), freshness={"LOT-1": "stale", "LOT-2": "current"})
    assert guarded["withheld"]["LOT-1"] == "observation_not_current"


@pytest.mark.parametrize("age_seconds, withheld", [(120, False), (121, True)])
def test_freshness_is_rechecked_before_display(age_seconds, withheld):
    now = datetime.fromisoformat(OBSERVED_AT) + timedelta(seconds=age_seconds)
    guarded = guard(a2_output(estimate()), now=now)
    assert ("LOT-1" in guarded["withheld"]) is withheld
    if withheld:
        assert guarded["withheld"]["LOT-1"] == "observation_aged_before_display"


def _confirmed_trip():
    now = datetime.now().astimezone().replace(microsecond=0)
    return {"destination": "Duffield Hall", "arrival_time": (now + timedelta(minutes=30)).isoformat(),
            "departure_time": (now + timedelta(minutes=150)).isoformat(), "vehicle_category": "sedan",
            "declared_eligibility": "permit_O", "access_needs": False}


def _corrupt_first_estimate(monkeypatch, change):
    real = service.estimate_arrival_time_availability

    def corrupted(*args, **kwargs):
        result = real(*args, **kwargs)
        estimates = result["arrival_time_availability_estimates"]
        if estimates:
            estimates[0] = {**estimates[0], **change(estimates[0])}
        return result
    monkeypatch.setattr(service, "estimate_arrival_time_availability", corrupted)


def test_whole_flow_withholds_an_estimate_for_another_arrival_time(monkeypatch):
    _corrupt_first_estimate(monkeypatch, lambda e: {
        "arrival_time": (datetime.fromisoformat(e["arrival_time"]) + timedelta(hours=5)).isoformat()})
    result = driver_interface.confirm_trip_requirements(_confirmed_trip())
    assert result["ranked_options"]
    assert result["ranking_basis"] == "fallback_walking_time"
    assert "Forecast at arrival" not in " ".join(o["explanation"] for o in result["ranked_options"])


def test_whole_flow_never_shows_inconsistent_bounds(monkeypatch):
    _corrupt_first_estimate(monkeypatch, lambda e: {"interval_lower": e["capacity"], "interval_upper": 0})
    result = driver_interface.confirm_trip_requirements(_confirmed_trip())
    for option in result["ranked_options"]:
        shown = option["forecast"]
        assert shown is None or 0 <= shown["interval_lower"] <= shown["available_spaces"] <= shown["interval_upper"]
