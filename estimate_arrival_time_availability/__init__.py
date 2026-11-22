"""A2 -- Estimate Arrival Time Availability.

Implements first-level IDEF0 function A2 of A0 Provide Parking Decision
Support.

Mechanism: C.0 Cornell Smart Parking Availability & Recommendation System
(the system itself), so no dependency is injected.

Signature from the ICOMs in Chapter 4; body added after the Ch11 forecast trade
study selected ALT-F2 (hybrid), with T_c read without the 2026-11-07 event window.

How a forecast is made (SR-14), per eligible area with a current observation:
  - The forecast time is the area's observation time; the lead time is the arrival
    time minus that, in minutes. The arrival time is not shifted to a grid point.
  - Below T_c (180 min) the LightGBM quantile models give the 10/50/90% occupancy at
    the grid lead times (0, 15, 30, 45, 60, 120 min); 0 min is the current
    observation itself. Their 80% interval is widened by the calibration amounts.
    The estimate and its bounds are interpolated linearly between the two grid points
    around the arrival; between the last model grid point and T_c the right-hand point
    is the baseline at T_c, so the forecast hands over to the baseline smoothly.
  - From T_c to 72 h the lot x day-of-week x 15-minute time-slot baseline for the
    arrival's time slot is used ("long range": for reference only).
  - If the model's look-back inputs are missing, the baseline is used. If neither
    model nor baseline has valid inputs, the area gets no forecast ("unsupported").

The model files in model/ are written by scripts/train_forecast.py from simulated
weeks 1-10. Results describe the simulator, not Cornell lots.
"""

import json
import math
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from contextual_information_sources import get_calendar_day, get_events, get_weather_forecast
from parking_data_access import occupancy_rate_history
from parking_availability_data_sources import LOCAL_TIME

MODEL_DIR = Path(__file__).with_name("model")
MAX_LEAD_MINUTES = 72 * 60          # SR-12 / SR-14: arrivals 0-72 h ahead
SLOT = timedelta(minutes=15)
QUANTILES = ("q10", "q50", "q90")


def estimate_arrival_time_availability(
    validated_parking_data: list[dict],
    normalized_trip_requirements: dict,
    validated_context_information: list[dict],
    eligible_parking_areas: list[dict],
    data_quality_and_freshness_status: dict,
    *,
    forecast_validity_criteria: dict,
) -> dict:
    """in: validated_parking_data (A1), normalized_trip_requirements (A1),
    validated_context_information (A1), eligible_parking_areas (A1),
    data_quality_and_freshness_status (A1).
    control: forecast_validity_criteria.
    out: arrival_time_availability_estimates (A3, A4),
    forecast_validity_status (A3, A4).
    """
    model = _model()
    t_c = model["manifest"]["t_c_minutes"]
    grid = sorted({0, *(g for g in forecast_validity_criteria.get(
        "horizons_minutes", model["manifest"]["model_grid_minutes"]) if 0 <= g < t_c)})
    observed = {lot["lot_id"]: lot for lot in validated_parking_data}
    arrival = _parse(normalized_trip_requirements.get("arrival_time"))

    estimates, status = [], {}
    for area in eligible_parking_areas:
        lot_id = area["lot_id"]
        lot = observed.get(lot_id)
        forecast_time = _parse(lot.get("observed_at")) if lot else None
        capacity = lot.get("capacity") if lot else None
        if (data_quality_and_freshness_status.get(lot_id) != "current" or forecast_time is None
                or arrival is None or not isinstance(capacity, int) or capacity <= 0
                or not 0 <= lot.get("occupied", -1) <= capacity):
            status[lot_id] = "unsupported"
            continue
        lead = max((arrival - forecast_time).total_seconds() / 60, 0.0)
        if lead > MAX_LEAD_MINUTES:
            status[lot_id] = "unsupported"
            continue
        result = _forecast(model, lot_id, lot["occupied"], capacity, forecast_time, lead, arrival, grid, t_c)
        if result is None:
            status[lot_id] = "unsupported"
            continue
        occupied, method = result
        estimates.append(_estimate(lot_id, capacity, occupied, method, forecast_time, arrival, lead, t_c))
        status[lot_id] = "supported"
    return {"arrival_time_availability_estimates": estimates, "forecast_validity_status": status}


# ---------------------------------------------------------------- forecast

def _forecast(model, lot_id, occupied_now, capacity, forecast_time, lead, arrival, grid, t_c):
    """Occupied-space (q10, q50, q90) at arrival and the method used, or None."""
    if lead >= t_c:
        at_arrival = _baseline(model, lot_id, arrival, capacity)
        return (at_arrival, "historical_baseline") if at_arrival else None

    points = {0: (occupied_now,) * 3}
    model_points = _model_points(model, lot_id, occupied_now / capacity, capacity, forecast_time,
                                 [g for g in grid if g > 0])
    if model_points is None:                      # look-back inputs missing: baseline only
        at_arrival = _baseline(model, lot_id, arrival, capacity)
        return (at_arrival, "historical_baseline") if at_arrival else None
    points.update(model_points)
    last = max(points)
    if lead > last:
        at_t_c = _baseline(model, lot_id, forecast_time + timedelta(minutes=t_c), capacity)
        if at_t_c is None:
            return None
        points[t_c] = at_t_c
    leads = sorted(points)
    right = next(g for g in leads if g >= lead)
    left = max(g for g in leads if g <= lead)
    share = 0.0 if right == left else (lead - left) / (right - left)
    value = tuple(a + (b - a) * share for a, b in zip(points[left], points[right]))
    return value, "lightgbm" if lead <= last else "lightgbm_to_baseline"


def _model_points(model, lot_id, rate_now, capacity, forecast_time, grid):
    """LightGBM (q10, q50, q90) occupied spaces at each grid lead, widened, or None."""
    code = model["manifest"]["lot_codes"].get(lot_id)
    if code is None or not grid:
        return None if code is None else {}
    origin = _floor_slot(forecast_time)
    history = lambda times: occupancy_rate_history(lot_id, times, origin)  # noqa: E731
    lags = history([origin - timedelta(minutes=m) for m in (15, 30, 45, 60)])
    weeks = model["manifest"]["profile_weeks"]
    origin_profile = _profile(history, origin, weeks)
    same_time_last_week = history([_week_before(origin)])[0]
    if None in lags or origin_profile is None or same_time_last_week is None:
        return None
    rolling = sum(lags) / 4
    rows = []
    for g in grid:
        target = origin + timedelta(minutes=g)
        target_profile = _profile(history, target, weeks)
        target_last_week = history([_week_before(target)])[0]
        if target_profile is None or target_last_week is None:
            return None
        local = target.astimezone(LOCAL_TIME)
        calendar = get_calendar_day(local.date())
        weather = get_weather_forecast(local.date())
        event = any(lot_id in e["lot_ids"] and e["start_hour"] <= local.hour < e["end_hour"]
                    for e in get_events(local.date()))
        origin_local = origin.astimezone(LOCAL_TIME)
        features = {
            "lot_code": code, "lead": g, "origin_minute": origin_local.hour * 60 + origin_local.minute,
            "rate_now": rate_now, "lag_15": lags[0], "lag_30": lags[1], "lag_60": lags[3],
            "rolling_mean_1h": rolling, "same_time_last_week": same_time_last_week,
            "target_last_week": target_last_week, "target_minute": local.hour * 60 + local.minute,
            "event_flag": int(event), "day_of_week": local.weekday(),
            "is_class_day": int(calendar["is_class_day"]), "is_break": int(calendar["is_break"]),
            "is_weekend": int(calendar["is_weekend"]), "temp_c": weather["temp_c"],
            "precipitation_probability": weather["precipitation_probability"],
            "snow_flag": int(weather["snow_flag"]), "origin_profile": origin_profile,
            "target_profile": target_profile, "dev_now": rate_now - origin_profile,
            "dev_1h": rolling - origin_profile,
        }
        rows.append([features[name] for name in model["manifest"]["features"]])
    predicted = {q: model["boosters"][q].predict(rows) for q in QUANTILES}
    widen = model["manifest"]["interval_widening_spaces"]
    points = {}
    for i, g in enumerate(grid):
        profile = rows[i][model["manifest"]["features"].index("target_profile")]
        low, mid, high = sorted(_clip((predicted[q][i] + profile) * capacity, capacity) for q in QUANTILES)
        extra = widen["0-1h"] if g <= 60 else widen["1-6h"]
        points[g] = (_clip(low - extra, capacity), mid, _clip(high + extra, capacity))
    return points


def _baseline(model, lot_id, at, capacity):
    """Baseline (q10, q50, q90) occupied spaces for the 15-minute time slot containing `at`."""
    local = _floor_slot(at).astimezone(LOCAL_TIME)
    rates = model["baseline"].get((lot_id, local.weekday(), local.strftime("%H:%M")))
    if rates is None:
        return None
    return tuple(sorted(_clip(r * capacity, capacity) for r in rates))


def _profile(history, at, weeks):
    """Mean rate at the same local weekday and time in up to `weeks` earlier weeks."""
    times, t = [], at
    for _ in range(weeks):
        t = _week_before(t)
        times.append(t)
    values = [v for v in history(times) if v is not None]
    return sum(values) / len(values) if values else None


def _estimate(lot_id, capacity, occupied, method, forecast_time, arrival, lead, t_c):
    low, mid, high = occupied
    available = min(max(int(math.floor(capacity - mid + 0.5)), 0), capacity)
    lower = min(max(int(math.floor(capacity - high)), 0), available)
    upper = max(min(int(math.ceil(capacity - low)), capacity), available)
    return {
        "lot_id": lot_id,
        "capacity": capacity,
        "available_spaces": available,
        "interval_lower": lower,
        "interval_upper": upper,
        "interval_level": 0.8,
        "forecast_time": forecast_time.isoformat(),
        "arrival_time": arrival.isoformat(),
        "lead_minutes": round(lead),
        "method": method,
        "long_range": lead >= t_c,
        "data_mode": "simulated",
    }


# ---------------------------------------------------------------- helpers

@lru_cache(maxsize=1)
def _model() -> dict:
    import csv

    import lightgbm as lgb
    manifest = json.loads((MODEL_DIR / "manifest.json").read_text())
    boosters = {q: lgb.Booster(model_file=str(MODEL_DIR / f"short_{q}.txt")) for q in QUANTILES}
    baseline = {}
    with (MODEL_DIR / "baseline.csv").open(newline="") as file:
        for row in csv.DictReader(file):
            baseline[(row["lot_id"], int(row["day_of_week"]), row["time_of_day"])] = tuple(
                float(row[q]) for q in QUANTILES)
    return {"manifest": manifest, "boosters": boosters, "baseline": baseline}


def _parse(value) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _floor_slot(at: datetime) -> datetime:
    """The start of the 15-minute slot containing `at`, in UTC (slots align with local quarter hours)."""
    utc = at.astimezone(timezone.utc)
    return utc.replace(minute=utc.minute - utc.minute % 15, second=0, microsecond=0)


def _week_before(at: datetime) -> datetime:
    """Same local wall-clock time seven days earlier (the earlier one if the hour repeats)."""
    wall = at.astimezone(LOCAL_TIME).replace(tzinfo=None) - timedelta(days=7)
    return wall.replace(tzinfo=LOCAL_TIME, fold=0).astimezone(timezone.utc)


def _clip(value: float, capacity: int) -> float:
    return min(max(float(value), 0.0), float(capacity))


def warm_up() -> None:
    """Load the model files and the occupancy history once, before the first request."""
    _model()
    occupancy_rate_history("LOT-1", [], datetime.now(timezone.utc))
