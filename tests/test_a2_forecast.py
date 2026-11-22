"""A2 Estimate Arrival Time Availability with the selected ALT-F2 forecast (SR-14).

All times are in simulated weeks 1-12, so no holdout row (weeks 13-15) is
needed. Expected values come from SR-14's rules, not from the model's output.
"""

from datetime import datetime, timedelta

import pytest

import estimate_arrival_time_availability as a2
import parking_data_access
from rank_parking_options import _is_valid_estimate

NOW = datetime.fromisoformat("2026-10-07T10:30:00-04:00")      # Wednesday, week 7
CRITERIA = {"max_observation_age_seconds": 120, "horizons_minutes": [0, 15, 30, 45, 60, 120]}
LOTS = [{"lot_id": "LOT-1", "occupied": 170, "capacity": 200, "observed_at": NOW.isoformat()},
        {"lot_id": "LOT-2", "occupied": 100, "capacity": 120, "observed_at": NOW.isoformat()},
        {"lot_id": "LOT-3", "occupied": 110, "capacity": 150, "observed_at": NOW.isoformat()}]
AREAS = [{"lot_id": lot["lot_id"]} for lot in LOTS]
CURRENT = {lot["lot_id"]: "current" for lot in LOTS}


def forecast(arrival, lots=LOTS, freshness=CURRENT):
    result = a2.estimate_arrival_time_availability(
        lots, {"arrival_time": arrival.isoformat()}, [], AREAS, freshness,
        forecast_validity_criteria=CRITERIA)
    return {e["lot_id"]: e for e in result["arrival_time_availability_estimates"]}, \
        result["forecast_validity_status"]


def test_model_files_record_the_team_decisions():
    manifest = a2._model()["manifest"]
    assert manifest["t_c_minutes"] == 180
    assert manifest["model_grid_minutes"] == [0, 15, 30, 45, 60, 120]
    assert manifest["trained_on"].startswith("simulated weeks 1-10")
    assert manifest["calibrated_on"] == "week 11 without the event window"
    assert manifest["lightgbm_settings"]["frozen_on"] == "2026-11-21"


@pytest.mark.parametrize("lead", [0, 15, 37.5, 60, 150, 180, 24 * 60, 72 * 60])
def test_supported_estimates_meet_the_a3_input_constraints(lead):
    estimates, status = forecast(NOW + timedelta(minutes=lead))
    assert set(status.values()) == {"supported"}
    for estimate in estimates.values():
        assert _is_valid_estimate(estimate)
        assert estimate["interval_level"] == 0.8


def test_method_follows_the_lead_time():
    method = lambda lead: forecast(NOW + timedelta(minutes=lead))[0]["LOT-1"]["method"]  # noqa: E731
    assert method(30) == "lightgbm"
    assert method(120) == "lightgbm"
    assert method(150) == "lightgbm_to_baseline"   # between the last model point and T_c
    assert method(180) == "historical_baseline"
    assert method(72 * 60) == "historical_baseline"
    assert forecast(NOW + timedelta(minutes=179))[0]["LOT-1"]["long_range"] is False
    assert forecast(NOW + timedelta(minutes=180))[0]["LOT-1"]["long_range"] is True


def test_zero_lead_is_the_current_observation():
    estimate = forecast(NOW)[0]["LOT-1"]
    assert estimate["available_spaces"] == estimate["interval_lower"] == estimate["interval_upper"] == 30


def test_from_t_c_on_the_baseline_for_the_arrival_time_slot_is_used():
    arrival = NOW + timedelta(hours=26, minutes=7)            # Thursday 12:37 -> the 12:30 slot
    q10, q50, q90 = a2._model()["baseline"][("LOT-1", 3, "12:30")]
    estimate = forecast(arrival)[0]["LOT-1"]
    assert estimate["available_spaces"] == round(200 - q50 * 200)
    assert estimate["interval_lower"] <= 200 - q90 * 200 <= estimate["interval_lower"] + 1
    assert estimate["interval_upper"] - 1 <= 200 - q10 * 200 <= estimate["interval_upper"]


def test_estimates_between_grid_points_are_interpolated():
    at = lambda lead: forecast(NOW + timedelta(minutes=lead))[0]["LOT-2"]["available_spaces"]  # noqa: E731
    low, high = sorted((at(30), at(45)))
    assert low <= at(37.5) <= high


@pytest.mark.parametrize("lead", [timedelta(hours=72, minutes=1), timedelta(days=5)])
def test_arrivals_beyond_72_hours_get_no_forecast(lead):
    estimates, status = forecast(NOW + lead)
    assert estimates == {} and set(status.values()) == {"unsupported"}


def test_stale_or_invalid_observations_get_no_forecast():
    lots = [LOTS[0], {**LOTS[1], "capacity": 0}, {**LOTS[2], "observed_at": "not a time"}]
    estimates, status = forecast(NOW + timedelta(minutes=30), lots=lots,
                                 freshness={"LOT-1": "stale", "LOT-2": "current", "LOT-3": "current"})
    assert estimates == {}
    assert status == {"LOT-1": "unsupported", "LOT-2": "unsupported", "LOT-3": "unsupported"}


def test_future_occupancy_cannot_change_the_forecast(monkeypatch):
    before = forecast(NOW + timedelta(minutes=60))[0]
    parking_data_access.occupancy_rate_history("LOT-1", [], NOW)    # load the series
    poisoned = {lot: {at: (1.0 if at > NOW else rate) for at, rate in series.items()}
                for lot, series in parking_data_access._series.items()}
    monkeypatch.setattr(parking_data_access, "_series", poisoned)
    assert forecast(NOW + timedelta(minutes=60))[0] == before


def test_missing_look_back_inputs_fall_back_to_the_baseline():
    first_day = datetime.fromisoformat("2026-08-24T10:30:00-04:00")   # no week before it
    lots = [{**lot, "observed_at": first_day.isoformat()} for lot in LOTS]
    estimates, status = forecast(first_day + timedelta(minutes=30), lots=lots)
    assert set(status.values()) == {"supported"}
    assert {e["method"] for e in estimates.values()} == {"historical_baseline"}
