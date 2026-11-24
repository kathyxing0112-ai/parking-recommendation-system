"""SR-14 verification: one run of the frozen ALT-F2 forecast on the held-out weeks 13-15.

Written and committed before the run (2026-11-22). Everything below -- cases, metrics,
primary scopes, breakdowns and the trip check -- is fixed here, before any holdout result
is seen. The run uses the product code and model files exactly as merged into main
(PR #16): no training, no tuning, no recalibration. Whatever the result, the weights,
the model, T_c and the selection stay as they are (X4, ADR-0004).

What is evaluated
  The product's A2 (`estimate_arrival_time_availability`) and the lot x weekday x
  15-minute baseline (q50 of `model/baseline.csv`, weeks 1-10), on identical cases:
  forecasts made at every whole hour of the evaluated weeks, for the 43 lead times of the
  trade study (15 min to 72 h), with forecast time and target time both in those weeks.
  The forecast time is the lot's observation time; only occupancy at or before it is used.
  Errors are in free spaces, using the integer counts the product returns (the baseline
  is rounded the same way).

SR-14 checks (primary scope: all day, weighted by the team's request shares
0-1 h 50%, 1-3 h 25%, 3-6 h 10%, 6-24 h 10%, 24-72 h 5%, the same weighting as X4):
  1. MAE of ALT-F2 not above the baseline's.
  2. Coverage of the stated 80% interval between 0.75 and 0.85.
  3. Trips: of 100 preselected trips (20 per band 0-1 h, 1-6 h, 6-24 h, 24-48 h, 48-72 h),
     at least 85 whose primary option has a free space on arrival.

Reported alongside, not as the check: the unweighted numbers; each usage band; the
LightGBM part (lead < 180 min) and the baseline part (lead >= 180 min); day types by target
time: ordinary (no event, not a break day), Thanksgiving break days, event windows
(event_flag for that lot and time); daytime 07:00-18:59.

Trips (seed 5151, drawn before the run from rules and calendar only, never occupancy):
  arrival on a 15-minute slot in the evaluated weeks, local time 07:00-18:45; lead time a
  multiple of 15 min drawn uniformly within its band; submission = arrival - lead, also in
  the evaluated weeks; stay 2 h; destination drawn from the walking-time table; permit
  permit_O or visitor; sedan; no access need. A drawn trip with no eligible lot under the
  confirmed rules is skipped and the next one drawn. Each trip runs the product path:
  A1.4 eligibility, A2, the R-04 guardrail, A3 ranking. Success: the primary lot has at
  least one free space at the arrival slot (lot level; zones are not modelled).
  For context only, the same trips ranked by walking time alone are also scored.

Usage:
  python scripts/evaluate_sr14_holdout.py --weeks validation   # dry run on weeks 11-12
  python scripts/evaluate_sr14_holdout.py --weeks holdout      # the single SR-14 run
The holdout run refuses to start if this file has uncommitted changes or a holdout
result already exists. Simulated data only; results describe the simulator.
"""

import argparse
import json
import math
import random
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import estimate_arrival_time_availability as a2  # noqa: E402
from contextual_information_sources import get_contextual_information, get_destinations  # noqa: E402
from cornell_transportation_and_parking_services import get_parking_rules_and_closures  # noqa: E402
from parking_availability_data_sources import LOCAL_TIME  # noqa: E402
from prepare_eligible_parking_information.determine_eligible_parking_areas import (  # noqa: E402
    determine_eligible_parking_areas)
from rank_parking_options import rank_parking_options  # noqa: E402
from smart_parking_service import (FORECAST_VALIDITY_CRITERIA, RANKING_AND_FALLBACK_RULES,  # noqa: E402
                                   guard_forecasts)

DATA = ROOT / "data" / "simulated" / "occupancy_15min.csv"
OUT = ROOT / "docs" / "measurements" / "ch11" / "holdout"
LEADS = [15, 30, 45, 60] + [60 * h for h in range(2, 25)] + [60 * h for h in range(27, 73, 3)]
USAGE_BANDS = [("0-1h", 0, 60), ("1-3h", 60, 180), ("3-6h", 180, 360), ("6-24h", 360, 1440), ("24-72h", 1440, 4320)]
SHARES = np.array([0.50, 0.25, 0.10, 0.10, 0.05])
TRIP_BANDS = [("0-1h", 0, 60), ("1-6h", 60, 360), ("6-24h", 360, 1440), ("24-48h", 1440, 2880), ("48-72h", 2880, 4320)]
TRIPS_PER_BAND = 20
T_C = 180
SEED = 5151


def load(split: str) -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df["t"] = pd.to_datetime(df["as_of_timestamp"], utc=True)
    if split == "validation":
        df = df[df["split"] != "holdout"]          # the dry run never reads the holdout
    return df


class Truth:
    """Occupancy and context per lot and 15-minute UTC time."""

    def __init__(self, df):
        self.occupied = df.pivot(index="t", columns="lot_id", values="occupied")
        self.event = df.pivot(index="t", columns="lot_id", values="event_flag")
        first = df[df["lot_id"] == df["lot_id"].iloc[0]].set_index("t")
        self.is_break = first["is_break"]
        self.capacity = df.groupby("lot_id")["capacity"].first().astype(int).to_dict()
        self.lots = sorted(self.capacity)


def observation(truth, lot, at):
    return {"lot_id": lot, "occupied": int(truth.occupied.at[at, lot]), "capacity": truth.capacity[lot],
            "observed_at": at.tz_convert(LOCAL_TIME).isoformat()}


def baseline_free(model, lot, target, capacity):
    occ = a2._baseline(model, lot, target.to_pydatetime(), capacity)
    return None if occ is None else min(max(int(math.floor(capacity - occ[1] + 0.5)), 0), capacity)


def forecast_cases(truth, times, model):
    lots = [{"lot_id": lot} for lot in truth.lots]
    current = {lot: "current" for lot in truth.lots}
    origins = [t for t in times if t.tz_convert(LOCAL_TIME).minute == 0]
    last = times[-1]
    rows = []
    for o in origins:
        obs = [observation(truth, lot, o) for lot in truth.lots]
        for lead in LEADS:
            target = o + pd.Timedelta(minutes=lead)
            if target > last:
                break
            arrival = target.tz_convert(LOCAL_TIME).isoformat()
            out = a2.estimate_arrival_time_availability(
                obs, {"arrival_time": arrival}, [], lots, current,
                forecast_validity_criteria=FORECAST_VALIDITY_CRITERIA)
            est = {e["lot_id"]: e for e in out["arrival_time_availability_estimates"]}
            for lot in truth.lots:
                cap = truth.capacity[lot]
                actual = cap - int(truth.occupied.at[target, lot])
                e = est.get(lot)
                rows.append({
                    "lot": lot, "origin": o, "target": target, "lead": lead,
                    "supported": e is not None,
                    "f2": e["available_spaces"] if e else np.nan,
                    "lower": e["interval_lower"] if e else np.nan,
                    "upper": e["interval_upper"] if e else np.nan,
                    "method": e["method"] if e else "unsupported",
                    "baseline": baseline_free(model, lot, target, cap),
                    "actual": actual,
                    "event": int(truth.event.at[target, lot]),
                    "is_break": int(truth.is_break.at[target]),
                    "hour": target.tz_convert(LOCAL_TIME).hour,
                })
    frame = pd.DataFrame(rows)
    frame["err_f2"] = (frame["f2"] - frame["actual"]).abs()
    frame["err_base"] = (frame["baseline"] - frame["actual"]).abs()
    frame["bias_f2"] = frame["actual"] - frame["f2"]       # > 0: forecast says fuller than it is (safe side)
    frame["covered"] = ((frame["actual"] >= frame["lower"]) & (frame["actual"] <= frame["upper"])).astype(float)
    frame["usage_band"] = frame["lead"].map(lambda l: next(n for n, a, b in USAGE_BANDS if a < l <= b))
    return frame


def weighted(frame, column):
    t = frame.groupby("usage_band")[column].mean().reindex([b[0] for b in USAGE_BANDS])
    if t.isna().any():
        return None
    return float(t.to_numpy() @ SHARES)


def summary(frame):
    ok = frame[frame["supported"]]
    return {"n": int(len(frame)), "n_supported": int(len(ok)),
            "weighted_mae_f2": weighted(ok, "err_f2"), "weighted_mae_baseline": weighted(ok, "err_base"),
            "weighted_coverage": weighted(ok, "covered"), "weighted_bias": weighted(ok, "bias_f2"),
            "mae_f2": float(ok["err_f2"].mean()), "mae_baseline": float(ok["err_base"].mean()),
            "coverage": float(ok["covered"].mean()), "bias": float(ok["bias_f2"].mean())}


def plain(frame):
    ok = frame[frame["supported"]]
    return {"n": int(len(ok)), "mae_f2": float(ok["err_f2"].mean()), "mae_baseline": float(ok["err_base"].mean()),
            "coverage": float(ok["covered"].mean()), "bias": float(ok["bias_f2"].mean())}


def breakdowns(frame):
    ordinary = (frame["event"] == 0) & (frame["is_break"] == 0)
    day = frame["hour"].between(7, 18)
    out = {"scope": {
        "all day": summary(frame), "daytime": summary(frame[day]),
        "ordinary days": summary(frame[ordinary]), "ordinary days, daytime": summary(frame[ordinary & day]),
        "Thanksgiving break days": plain(frame[frame["is_break"] == 1]),
        "event windows": plain(frame[frame["event"] == 1]),
    }}
    out["usage_band"] = {b: plain(frame[frame["usage_band"] == b]) for b, _, _ in USAGE_BANDS}
    part = {"LightGBM part (lead < 180 min)": frame["lead"] < T_C, "baseline part (lead >= 180 min)": frame["lead"] >= T_C}
    out["part"] = {}
    for name, m in part.items():
        out["part"][name] = {
            "all": plain(frame[m]), "ordinary days": plain(frame[m & ordinary]),
            "Thanksgiving break days": plain(frame[m & (frame["is_break"] == 1)]),
            "event windows": plain(frame[m & (frame["event"] == 1)])}
    return out


def draw_trips(truth, times):
    rng = random.Random(SEED)
    destinations = get_destinations()
    rules = get_parking_rules_and_closures("permit_O", False)
    lots_obs = [{"lot_id": lot} for lot in truth.lots]
    first, last = times[0], times[-1]
    arrivals = [t for t in times if 7 * 60 <= t.tz_convert(LOCAL_TIME).hour * 60 + t.tz_convert(LOCAL_TIME).minute <= 18 * 60 + 45]
    trips = []
    for band, lo, hi in TRIP_BANDS:
        leads = list(range(lo + 15, hi + 1, 15))
        kept = 0
        while kept < TRIPS_PER_BAND:
            arrival = rng.choice(arrivals)
            lead = rng.choice(leads)
            submitted = arrival - pd.Timedelta(minutes=lead)
            destination = rng.choice(destinations)
            permit = rng.choice(["permit_O", "visitor"])
            if submitted < first or arrival > last:
                continue
            local = arrival.tz_convert(LOCAL_TIME)
            trip = {"destination": destination, "arrival_time": local.isoformat(),
                    "departure_time": (local + timedelta(hours=2)).isoformat(), "vehicle_category": "sedan",
                    "declared_eligibility": permit, "access_needs": False}
            if not determine_eligible_parking_areas(lots_obs, trip, [], {}, parking_policy_constraints=rules):
                continue
            trips.append({"band": band, "lead": lead, "submitted": submitted, "arrival": arrival, "trip": trip})
            kept += 1
    return trips


def run_trips(truth, trips):
    rules = get_parking_rules_and_closures("permit_O", False)
    rows = []
    for t in trips:
        s, trip = t["submitted"], t["trip"]
        obs = [observation(truth, lot, s) for lot in truth.lots]
        walking = get_contextual_information(trip["destination"])
        current = {lot: "current" for lot in truth.lots}
        eligible = determine_eligible_parking_areas(obs, trip, walking, current, parking_policy_constraints=rules)
        forecast = a2.estimate_arrival_time_availability(obs, trip, walking, eligible, current,
                                                         forecast_validity_criteria=FORECAST_VALIDITY_CRITERIA)
        guarded = guard_forecasts(forecast, trip, eligible, obs, current, s.tz_convert(LOCAL_TIME).to_pydatetime())
        ranked = rank_parking_options(trip, walking, eligible, current,
                                      guarded["arrival_time_availability_estimates"],
                                      guarded["forecast_validity_status"],
                                      ranking_and_fallback_rules=RANKING_AND_FALLBACK_RULES)
        nearest = min(eligible, key=lambda e: (next(w["walking_time_minutes"] for w in walking
                                                     if w["lot_id"] == e["lot_id"]), e["lot_id"]))["lot_id"]
        free = lambda lot: truth.capacity[lot] - int(truth.occupied.at[t["arrival"], lot])  # noqa: E731
        primary = ranked[0]["lot_id"]
        rows.append({"band": t["band"], "lead_minutes": t["lead"],
                     "submitted": s.tz_convert(LOCAL_TIME).isoformat(), "arrival": trip["arrival_time"],
                     "destination": trip["destination"], "permit": trip["declared_eligibility"],
                     "eligible": " ".join(e["lot_id"] for e in eligible),
                     "ranking_basis": ranked[0]["ranking_basis"], "primary": primary,
                     "primary_free_at_arrival": free(primary), "success": free(primary) > 0,
                     "nearest_lot": nearest, "nearest_free_at_arrival": free(nearest),
                     "nearest_success": free(nearest) > 0,
                     "event_at_arrival": int(truth.event.at[t["arrival"], primary]),
                     "break_at_arrival": int(truth.is_break.at[t["arrival"]])})
    return pd.DataFrame(rows)


def commit_of_this_file() -> str:
    path = str(Path(__file__).relative_to(ROOT))
    dirty = subprocess.run(["git", "status", "--porcelain", path], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if dirty:
        raise SystemExit(f"{path} has uncommitted changes; commit it before the holdout run")
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", choices=["validation", "holdout"], required=True)
    args = parser.parse_args()
    out_dir = OUT if args.weeks == "holdout" else OUT.parent / "holdout_dry_run_validation"
    if args.weeks == "holdout":
        if (OUT / "results.json").exists():
            raise SystemExit("the holdout has already been run once; see docs/measurements/ch11/holdout/")
        commit = commit_of_this_file()
    else:
        commit = None

    started = time.time()
    df = load(args.weeks)
    truth = Truth(df)
    times = truth.occupied.index[truth.occupied.index.isin(df.loc[df["split"] == args.weeks, "t"])]
    model = a2._model()
    cases = forecast_cases(truth, times, model)
    trips = run_trips(truth, draw_trips(truth, times))

    s = summary(cases)
    checks = {
        "MAE not above the baseline (weighted, all day)": {
            "alt_f2": s["weighted_mae_f2"], "baseline": s["weighted_mae_baseline"],
            "met": s["weighted_mae_f2"] <= s["weighted_mae_baseline"]},
        "80% interval coverage within 0.75-0.85 (weighted, all day)": {
            "coverage": s["weighted_coverage"], "met": 0.75 <= s["weighted_coverage"] <= 0.85},
        "primary option has a free space on arrival, at least 85 of 100 trips": {
            "successes": int(trips["success"].sum()), "trips": int(len(trips)),
            "met": int(trips["success"].sum()) >= 85},
    }
    result = {
        "weeks": args.weeks, "script_commit": commit,
        "model_manifest": {k: model["manifest"][k] for k in ("t_c_minutes", "model_grid_minutes",
                                                           "interval_widening_spaces", "trained_on", "data_sha256")},
        "sr14_checks": checks, "breakdowns": breakdowns(cases),
        "trips": {"by_band": trips.groupby("band")["success"].agg(["sum", "count"]).astype(int).to_dict("index"),
                  "nearest_lot_successes_context_only": int(trips["nearest_success"].sum()),
                  "ranking_basis": trips["ranking_basis"].value_counts().to_dict()},
        "runtime_seconds": round(time.time() - started, 1), "simulated": True,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(result, indent=2, default=float) + "\n")
    trips.to_csv(out_dir / "trips.csv", index=False)
    print(json.dumps({"checks": checks, "runtime_seconds": result["runtime_seconds"]}, indent=2, default=float))


if __name__ == "__main__":
    main()
