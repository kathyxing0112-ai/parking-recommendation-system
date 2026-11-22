"""Ch11 trade-study spike: compare the C.2 forecast alternatives on validation weeks 11-12.

Alternatives (DEC.2 / trade study topic):
  baseline   historical time-slot baseline: median and 10/90% quantiles of occupied
             spaces per lot x day of week x 15-minute time of day, weeks 1-10
  ALT-F1     one LightGBM quantile model (10/50/90%) for every lead time
  ALT-F2     LightGBM for lead times shorter than the cutoff T_c, baseline from T_c on.
             T_c is the shortest lead time where LightGBM validation MAE exceeds the
             baseline's (set from data, not traded)
  ALT-F3     zero-shot foundation models, no training on this data:
             Chronos-2 with known future covariates, and Chronos-Bolt-Small on occupancy only

Rules followed (team decisions, 2026-11-20):
  - Weeks 13-15 (holdout) are never read.
  - The forecast time and the target time are in the same split: training samples
    have both in weeks 1-10, validation samples both in weeks 11-12.
  - Inputs use only occupancy at or before the forecast time. Calendar, event and
    weather-forecast values for the target day are known in advance and may be used.
  - Times are handled as UTC; "same time last week" uses local wall-clock time.

Evaluation: forecasts made at every whole hour of weeks 11-12 for 43 lead times
(15-60 min by 15, 2-24 h hourly, 27-72 h every 3 h), three lots. MAE in spaces,
80% interval coverage, mean interval width, reported all-day and daytime (target
time 07:00-18:59), by lead time and lead-time band. Also pinball (quantile) loss and
bias (median forecast minus observation). The 2026-11-07 event window is reported on
its own (one event, for reference only).

Interval calibration: the LightGBM intervals are widened by split conformal calibration
(one amount per lead-time band) fitted on forecasts for week 11, without the event window,
and checked on forecasts made in week 12, next to the uncalibrated methods on the same
week-12 forecasts.

Usage-weighted scores (team decisions, 2026-11-21): the selection score weights each
lead-time band by the team's assumed share of requests (most requests come close to
arrival), read without the event window; two other share sets test whether the ranking
depends on the assumption. T_c is read without the event window (3 h); the reading with
the event (7 h) is still reported.

Leakage checks run inside the script and stop it if a rule is broken; the checks that
held are listed in run.json. The LightGBM settings were frozen on 2026-11-21.

All data are simulated; results describe the simulator, not Cornell lots.

Usage:
  python scripts/spike_forecast.py [--out docs/measurements/ch11] [--skip-chronos]
"""

import argparse
import hashlib
import json
import pickle
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "simulated" / "occupancy_15min.csv"
LOCAL = "America/New_York"
LEADS = [15, 30, 45, 60] + [60 * h for h in range(2, 25)] + [60 * h for h in range(27, 73, 3)]
BANDS = [("0-1h", 0, 60), ("1-6h", 60, 360), ("6-24h", 360, 1440), ("24-48h", 1440, 2880), ("48-72h", 2880, 4320)]
QUANTILES = (0.1, 0.5, 0.9)
DAYTIME_HOURS = range(7, 19)
EVENT_DAY, EVENT_HOURS, EVENT_LOTS = "2026-11-07", range(10, 18), ("LOT-1", "LOT-2")
CHRONOS_CONTEXT_STEPS = 21 * 96           # 21 days of 15-minute history
CHRONOS_HORIZON_STEPS = 72 * 4            # 72 hours
CHRONOS_COVARIATES = ["is_class_day", "is_break", "is_weekend", "event_flag", "precipitation_probability", "temp_c"]
LATENCY_RUNS = 30
SEED = 5151

TARGET_CONTEXT = ["day_of_week", "is_class_day", "is_break", "is_weekend", "temp_c",
                  "precipitation_probability", "snow_flag"]
FEATURES = ["lot_code", "lead", "origin_minute", "rate_now", "lag_15", "lag_30", "lag_60", "rolling_mean_1h",
            "same_time_last_week", "target_last_week", "target_minute", "event_flag"] + TARGET_CONTEXT + [
            "origin_profile", "target_profile", "dev_now", "dev_1h"]
PROFILE_WEEKS = 15            # look back as many weeks as exist before the time
SHORT_MODEL_MAX_LEAD = 360    # ALT-F2 trains its LightGBM on lead times up to 6 h only
CALIBRATION_WEEK, CHECK_WEEK = 11, 12
# Team assumption (2026-11-21): share of requests by how long before arrival they are made.
USAGE_BANDS = [("0-1h", 0, 60), ("1-3h", 60, 180), ("3-6h", 180, 360), ("6-24h", 360, 1440), ("24-72h", 1440, 4320)]
USAGE_SHARES = {"team": (0.50, 0.25, 0.10, 0.10, 0.05),        # the team's assumption
                "more near": (0.70, 0.15, 0.05, 0.05, 0.05),   # sensitivity checks
                "more far": (0.30, 0.20, 0.15, 0.20, 0.15)}
INTERVAL_LEVEL = 0.8

CHECKS: list[str] = []        # leakage checks that passed in this run, written to run.json


def check(condition: bool, statement: str):
    """Stop the run if a leakage rule is broken; otherwise record that it held."""
    if not condition:
        raise AssertionError(f"leakage check failed: {statement}")
    if statement not in CHECKS:
        CHECKS.append(statement)


# ---------------------------------------------------------------- data

def load():
    df = pd.read_csv(DATA)
    df = df[df["split"] != "holdout"].copy()          # holdout weeks are never read past this line
    df["t"] = pd.to_datetime(df["as_of_timestamp"], utc=True)
    check(set(df["split"]) == {"train", "validation"} and df["sim_week"].max() <= 12,
          "no holdout row (weeks 13-15) is kept after loading")
    return df


class Series:
    """Wide per-lot arrays on the UTC 15-minute index, plus per-time context."""

    def __init__(self, df):
        self.lots = sorted(df["lot_id"].unique())
        self.capacity = df.groupby("lot_id")["capacity"].first().to_dict()
        self.occupied = df.pivot(index="t", columns="lot_id", values="occupied").sort_index()
        self.rate = df.pivot(index="t", columns="lot_id", values="occupancy_rate").sort_index()
        self.event = df.pivot(index="t", columns="lot_id", values="event_flag").sort_index()
        self.times = self.rate.index
        self.info = df[df["lot_id"] == self.lots[0]].set_index("t").sort_index()
        local = self.times.tz_convert(LOCAL)
        self.info["minute"] = local.hour * 60 + local.minute


def week_before(times: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Same local wall-clock time seven days earlier, as UTC."""
    wall = times.tz_convert(LOCAL).tz_localize(None) - pd.Timedelta(days=7)
    return wall.tz_localize(LOCAL, ambiguous=np.ones(len(wall), bool), nonexistent="shift_forward").tz_convert("UTC")


def profile(rate: pd.Series, times: pd.DatetimeIndex) -> np.ndarray:
    """Mean rate at the same local weekday and time in every earlier week that exists.

    Uses only weeks before `times`, so it never sees the time it describes; for a
    target time at most 72 h ahead, every week used is before the forecast time too.
    """
    values, at = [], times
    for _ in range(PROFILE_WEEKS):
        at = week_before(at)
        values.append(rate.reindex(at).to_numpy())
    return np.nanmean(np.vstack(values), axis=0)


def samples(s: Series, split: str, every_minutes: int) -> pd.DataFrame:
    """One row per lot, forecast time and lead time; forecast and target time both in `split`."""
    split_times = s.info.index[s.info["split"] == split]
    last = split_times.max()
    origins = split_times[s.info.loc[split_times, "minute"].to_numpy() % every_minutes == 0]
    origins = origins[week_before(origins) >= s.times[0]]          # needs one week of history
    frames = []
    for lead in LEADS:
        target = origins + pd.Timedelta(minutes=lead)
        keep = target <= last
        o, tg = origins[keep], target[keep]
        ctx = s.info.reindex(tg)
        check((s.info.reindex(o)["split"] == split).all() and (ctx["split"] == split).all(),
              "forecast time and target time are in the same split")
        check((week_before(o) < o).all() and (week_before(tg) <= o).all(),
              "lag, same-time-last-week and profile inputs are at or before the forecast time")
        check((tg > o).all(), "every label is after its forecast time")
        for code, lot in enumerate(s.lots):
            r = s.rate[lot]
            look = lambda at: r.reindex(at).to_numpy()  # noqa: E731
            lag = lambda minutes: look(o - pd.Timedelta(minutes=minutes))  # noqa: E731
            frame = pd.DataFrame({
                "lot": lot, "lot_code": code, "origin": o, "target": tg, "lead": lead,
                "origin_minute": s.info.reindex(o)["minute"].to_numpy(),
                "rate_now": look(o), "lag_15": lag(15), "lag_30": lag(30), "lag_60": lag(60),
                "same_time_last_week": look(week_before(o)),
                "target_last_week": look(week_before(tg)),
                "target_minute": ctx["minute"].to_numpy(),
                "event_flag": s.event[lot].reindex(tg).to_numpy(),
                "y_rate": look(tg),
                "y": s.occupied[lot].reindex(tg).to_numpy(),
                "capacity": s.capacity[lot],
                "target_hour": tg.tz_convert(LOCAL).hour,
                "target_date": tg.tz_convert(LOCAL).strftime("%Y-%m-%d"),
                "target_time_of_day": ctx["time_of_day"].to_numpy(),
            })
            frame["rolling_mean_1h"] = np.mean([lag(m) for m in (60, 45, 30, 15)], axis=0)
            frame["origin_profile"] = profile(r, o)
            frame["target_profile"] = profile(r, tg)
            frame["dev_now"] = frame["rate_now"] - frame["origin_profile"]
            frame["dev_1h"] = frame["rolling_mean_1h"] - frame["origin_profile"]
            for col in TARGET_CONTEXT:
                frame[col] = ctx[col].to_numpy()
            frames.append(frame)
    out = pd.concat(frames, ignore_index=True)
    assert not out[FEATURES + ["y"]].isna().any().any(), "missing feature or label"
    check(not {"y", "y_rate", "target"} & set(FEATURES), "labels are not model features")
    out["origin_week"] = s.info["sim_week"].reindex(pd.DatetimeIndex(out["origin"])).to_numpy()
    out["target_week"] = s.info["sim_week"].reindex(pd.DatetimeIndex(out["target"])).to_numpy()
    return out


def finish(pred: np.ndarray, capacity: np.ndarray) -> np.ndarray:
    """Clip quantile forecasts to [0, capacity] and keep q10 <= q50 <= q90."""
    return np.sort(np.clip(pred, 0, capacity[:, None]), axis=1)


# ---------------------------------------------------------------- alternatives

def fit_baseline(train_df):
    check(set(train_df["split"]) == {"train"}, "the baseline table uses weeks 1-10 only")
    grouped = train_df.groupby(["lot_id", "day_of_week", "time_of_day"])["occupied"]
    return pd.concat({q: grouped.quantile(q) for q in QUANTILES}, axis=1)


def predict_baseline(table, frame):
    keys = pd.MultiIndex.from_arrays([frame["lot"], frame["day_of_week"], frame["target_time_of_day"]])
    return finish(table.reindex(keys).to_numpy(), frame["capacity"].to_numpy())


def fit_lightgbm(train, band_weights: bool):
    """Quantile models of the rate's departure from the target-time profile.

    With band_weights, each lead-time band carries equal total weight, so the many
    long lead times on the grid do not crowd out the short ones.
    """
    import lightgbm as lgb
    weight = None
    if band_weights:
        leads_per_band = pd.Series(LEADS).map(band_of).value_counts()
        weight = 1.0 / train["lead"].map(band_of).map(leads_per_band)
    models = {}
    for q in QUANTILES:
        models[q] = lgb.LGBMRegressor(objective="quantile", alpha=q, n_estimators=400, learning_rate=0.05,
                                      num_leaves=63, min_child_samples=100, random_state=SEED, verbose=-1)
        models[q].fit(train[FEATURES], train["y_rate"] - train["target_profile"], sample_weight=weight,
                      categorical_feature=["lot_code"])
    return models


def predict_lightgbm(models, frame):
    rates = np.column_stack([models[q].predict(frame[FEATURES]) for q in QUANTILES])
    rates += frame["target_profile"].to_numpy()[:, None]
    return finish(rates * frame["capacity"].to_numpy()[:, None], frame["capacity"].to_numpy())


def chronos_inputs(s: Series, origins, lot, covariates: bool):
    occ = s.occupied[lot].to_numpy(dtype=np.float32)
    idx = s.times.get_indexer(origins)
    items = []
    check((idx >= 0).all() and (s.times[idx] == origins).all(), "Chronos history ends at the forecast time")
    check(not set(CHRONOS_COVARIATES) & {"occupied", "occupancy_rate"},
          "Chronos future covariates are calendar, event and weather-forecast values only")
    for i in idx:
        target = occ[max(0, i - CHRONOS_CONTEXT_STEPS + 1): i + 1]
        if not covariates:
            items.append(target)
            continue
        past = slice(max(0, i - CHRONOS_CONTEXT_STEPS + 1), i + 1)
        future = slice(i + 1, i + 1 + CHRONOS_HORIZON_STEPS)
        cov = {c: (s.event[lot] if c == "event_flag" else s.info[c]).to_numpy(dtype=np.float32) for c in CHRONOS_COVARIATES}
        items.append({"target": target,
                      "past_covariates": {c: v[past] for c, v in cov.items()},
                      "future_covariates": {c: _pad(v[future]) for c, v in cov.items()}})
    return items


def _pad(values):
    """Future covariates past the end of the validation weeks are never scored; repeat the last value."""
    if len(values) == CHRONOS_HORIZON_STEPS:
        return values
    return np.concatenate([values, np.repeat(values[-1:], CHRONOS_HORIZON_STEPS - len(values))])


def load_chronos(name):
    import torch
    from chronos import BaseChronosPipeline
    torch.manual_seed(SEED)
    return BaseChronosPipeline.from_pretrained(name, device_map="cpu", dtype=torch.float32)


def run_chronos(pipe, items, covariates: bool, batch=64):
    out = []
    for start in range(0, len(items), batch):
        chunk = items[start:start + batch]
        if covariates:
            quantiles, _ = pipe.predict_quantiles(chunk, prediction_length=CHRONOS_HORIZON_STEPS,
                                                  quantile_levels=list(QUANTILES))
            out.extend(q[0].numpy() for q in quantiles)            # (horizon, 3)
        else:
            import torch
            quantiles, _ = pipe.predict_quantiles([torch.tensor(x) for x in chunk],
                                                  prediction_length=CHRONOS_HORIZON_STEPS,
                                                  quantile_levels=list(QUANTILES))
            out.extend(quantiles.numpy())
    return np.stack(out)                                            # (n, horizon, 3)


def predict_chronos(pipe, s, val, covariates):
    preds = np.empty((len(val), 3))
    for lot in s.lots:
        rows = val["lot"] == lot
        origins = pd.DatetimeIndex(val.loc[rows, "origin"].unique())
        paths = run_chronos(pipe, chronos_inputs(s, origins, lot, covariates), covariates)
        at = pd.Series(np.arange(len(origins)), index=origins)
        o = at.reindex(val.loc[rows, "origin"]).to_numpy()
        k = val.loc[rows, "lead"].to_numpy() // 15 - 1
        preds[rows.to_numpy()] = paths[o, k]
    return finish(preds, val["capacity"].to_numpy())


# ---------------------------------------------------------------- metrics

def band_of(lead):
    return next(name for name, lo, hi in BANDS if lo < lead <= hi)


def pinball(y, p):
    """Mean quantile (pinball) loss over the 10/50/90% forecasts, in spaces. Lower is better.
    It rewards an accurate median and an interval that is neither too narrow nor too wide."""
    losses = [np.where(y >= p[:, i], (y - p[:, i]) * q, (p[:, i] - y) * (1 - q)) for i, q in enumerate(QUANTILES)]
    return np.mean(losses, axis=0)


def score(val, preds: dict) -> pd.DataFrame:
    rows = []
    for method, p in preds.items():
        frame = val[["lot", "lead", "y", "target_hour", "target_date", "origin_week", "target_week"]].copy()
        frame["err"] = np.abs(p[:, 1] - frame["y"])
        frame["bias"] = p[:, 1] - frame["y"]          # below 0: occupancy forecast too low (more risk for drivers)
        frame["pinball"] = pinball(frame["y"].to_numpy(), p)
        frame["covered"] = (frame["y"] >= p[:, 0]) & (frame["y"] <= p[:, 2])
        frame["width"] = p[:, 2] - p[:, 0]
        frame["method"] = method
        rows.append(frame)
    return pd.concat(rows, ignore_index=True)


def summarize(scored, by):
    g = scored.groupby(["method"] + by)
    return g.agg(n=("err", "size"), mae=("err", "mean"), bias=("bias", "mean"), pinball=("pinball", "mean"),
                 coverage=("covered", "mean"), width=("width", "mean")).reset_index()


def in_event_window(frame) -> np.ndarray:
    return ((frame["target_date"] == EVENT_DAY) & frame["target_hour"].isin(EVENT_HOURS)
            & frame["lot"].isin(EVENT_LOTS)).to_numpy()


def band_table(scored):
    """By lead-time band and for 0-72 h: all-day, daytime, and all-day without the one event window."""
    scored = scored.assign(band=scored["lead"].map(band_of))
    scopes = {"all-day": scored, "daytime": scored[scored["target_hour"].isin(DAYTIME_HOURS)],
              "all-day, no event window": scored[~in_event_window(scored)]}
    table = pd.concat([summarize(frame.assign(band=band) if band else frame, ["band"]).assign(scope=scope)
                       for scope, frame in scopes.items() for band in (None, "0-72h")])
    table["band"] = pd.Categorical(table["band"], [b[0] for b in BANDS] + ["0-72h"], ordered=True)
    return table.sort_values(["scope", "method", "band"])


def usage_weighted(scored) -> pd.DataFrame:
    """Each metric by usage band, and weighted by each share set in USAGE_SHARES."""
    names = [b[0] for b in USAGE_BANDS]
    scored = scored.assign(usage_band=scored["lead"].map(lambda l: next(n for n, a, b in USAGE_BANDS if a < l <= b)),
                           covered=scored["covered"].astype(float))
    event = in_event_window(scored)
    day = scored["target_hour"].isin(DAYTIME_HOURS).to_numpy()
    scopes = {"all-day, no event window": ~event, "daytime, no event window": ~event & day,
              "all-day": np.ones(len(scored), bool), "daytime": day, "event window": event}
    rows = []
    for scope, m in scopes.items():
        if not m.any():
            continue
        for metric, column in [("mae", "err"), ("bias", "bias"), ("pinball", "pinball"),
                               ("coverage", "covered"), ("width", "width")]:
            t = scored[m].groupby(["method", "usage_band"])[column].mean().unstack()[names]
            for name, shares in USAGE_SHARES.items():
                t[f"weighted {name}"] = t[names].to_numpy() @ np.array(shares)
            rows.append(t.reset_index().assign(scope=scope, metric=metric))
    return pd.concat(rows, ignore_index=True)


def tables(scored):
    day = scored[scored["target_hour"].isin(DAYTIME_HOURS)]
    event = scored[in_event_window(scored)]
    per_lead = pd.concat([summarize(scored, ["lead"]).assign(scope="all-day"),
                          summarize(day, ["lead"]).assign(scope="daytime")])
    event_band = summarize(event.assign(band=event["lead"].map(band_of)), ["band"]).assign(
        scope="event 2026-11-07 10:00-17:59 LOT-1/2")
    return per_lead, band_table(scored), event_band


def calibrate(val, pred, bands):
    """Split conformal calibration of the 80% interval, one widening amount per lead-time band.

    For each forecast with target time in week 11 (outside the event window), the score is how far the observation falls
    outside the interval (negative when inside). The widening for a band is the
    ceil((n+1)*0.8)/n quantile of its scores, so that about 80% of week-11 observations fall
    inside the widened interval. The median forecast is not changed. Week 12 is the check.
    Bands not listed are left as they are.
    """
    y = val["y"].to_numpy()
    band = val["lead"].map(band_of).to_numpy()
    calibration = (val["target_week"] == CALIBRATION_WEEK).to_numpy()   # forecast time is then in week 11 too
    calibration &= ~in_event_window(val)                              # team decision 2026-11-21
    scores = np.maximum(pred[:, 0] - y, y - pred[:, 2])
    out, widen = pred.copy(), {}
    for b in bands:
        m = calibration & (band == b)
        n = int(m.sum())
        level = min(1.0, np.ceil((n + 1) * INTERVAL_LEVEL) / n)
        widen[b] = round(float(np.quantile(scores[m], level, method="higher")), 3)
        rows = band == b
        out[rows, 0] -= widen[b]
        out[rows, 2] += widen[b]
    return finish(out, val["capacity"].to_numpy()), widen


def cutoff(val, model_pred, baseline_pred, rows=None):
    """T_c: the shortest lead where the short-lead LightGBM's all-day validation MAE exceeds
    the baseline's. If it never does within its 6 h training range, T_c is the next lead after 6 h.
    Returns T_c and the per-lead MAE pair it was read from."""
    rows = np.ones(len(val), bool) if rows is None else rows
    frame = pd.DataFrame({"lead": val["lead"].to_numpy(),
                          "model": np.abs(model_pred[:, 1] - val["y"].to_numpy()),
                          "baseline": np.abs(baseline_pred[:, 1] - val["y"].to_numpy())})
    mae = frame[rows & (frame["lead"] <= SHORT_MODEL_MAX_LEAD).to_numpy()].groupby("lead").mean()
    worse = mae.index[mae["model"] > mae["baseline"]]
    t_c = int(worse.min()) if len(worse) else min(l for l in LEADS if l > SHORT_MODEL_MAX_LEAD)
    return t_c, mae.round(3)


# ---------------------------------------------------------------- cost

def latency(fn, runs=LATENCY_RUNS):
    fn()                                                            # warm-up, not counted
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)
    return {"runs": runs, "median_ms": round(float(np.median(times)), 3),
            "p95_ms": round(float(np.percentile(times, 95)), 3)}


def rss_mb():
    return psutil.Process().memory_info().rss / 2**20


def environment():
    import lightgbm
    import torch
    import chronos
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "scripts", "data"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    return {"commit": commit, "uncommitted_changes_in_scripts_or_data": dirty,
            "data_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
            "machine": platform.machine(), "processor": _cpu(), "memory_gb": round(psutil.virtual_memory().total / 2**30),
            "os": platform.platform(), "python": platform.python_version(),
            "lightgbm": lightgbm.__version__, "torch": torch.__version__,
            "chronos_forecasting": getattr(chronos, "__version__", _pkg_version("chronos-forecasting")),
            "device": "cpu", "torch_threads": torch.get_num_threads()}


def _cpu():
    out = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    return out or platform.processor()


def _pkg_version(name):
    from importlib.metadata import version
    return version(name)


# ---------------------------------------------------------------- main

def memory_in_fresh_process(kind: str, model, inputs) -> float:
    """Memory added by loading one model and answering one request, measured in a new Python
    process so that training and other models do not distort it. Libraries are imported before
    the first reading, so the figure is the model and its working memory only."""
    with tempfile.TemporaryDirectory() as folder:
        model_path, inputs_path = Path(folder) / "model.pkl", Path(folder) / "inputs.pkl"
        model_path.write_bytes(pickle.dumps(model))
        inputs_path.write_bytes(pickle.dumps(inputs))
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--measure-memory", kind,
                                 str(model_path), str(inputs_path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout.strip().splitlines()[-1])["rss_increase_mb"]


def _measure_memory(kind, model_path, inputs_path):
    if kind == "lightgbm":
        import lightgbm  # noqa: F401
    if kind == "chronos":
        import chronos  # noqa: F401
        import torch  # noqa: F401
    before = rss_mb()
    model = pickle.loads(Path(model_path).read_bytes())
    inputs = pickle.loads(Path(inputs_path).read_bytes())
    if kind == "baseline":
        predict_baseline(model, inputs)
    elif kind == "lightgbm":
        predict_lightgbm(model, inputs)
    else:
        items, covariates = inputs
        run_chronos(load_chronos(model), items, covariates)
    print(json.dumps({"rss_increase_mb": round(rss_mb() - before, 1)}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "measurements" / "ch11")
    parser.add_argument("--skip-chronos", action="store_true")
    parser.add_argument("--measure-memory", nargs=3, metavar=("KIND", "MODEL", "INPUTS"), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.measure_memory:
        _measure_memory(*args.measure_memory)
        return
    args.out.mkdir(parents=True, exist_ok=True)

    df = load()
    s = Series(df)
    train = samples(s, "train", every_minutes=15)
    val = samples(s, "validation", every_minutes=60)
    print(f"training samples {len(train)}, validation samples {len(val)}", flush=True)

    preds, cost = {}, {}
    one = val[val["origin"] == val["origin"].iloc[0]]              # one request: 3 lots x 43 leads

    start = time.perf_counter()
    table = fit_baseline(df[df["split"] == "train"])
    cost["baseline"] = {"fit_s": round(time.perf_counter() - start, 3), "trained_on": "weeks 1-10",
                        "model_size_kb": round(table.memory_usage(deep=True).sum() / 1024, 1),
                        "memory_mb": memory_in_fresh_process("baseline", table, one),
                        "latency_one_request": latency(lambda: predict_baseline(table, one))}
    preds["baseline"] = predict_baseline(table, val)

    start = time.perf_counter()
    models = fit_lightgbm(train, band_weights=True)
    fit_s = time.perf_counter() - start
    preds["ALT-F1 LightGBM"] = predict_lightgbm(models, val)
    cost["ALT-F1 LightGBM"] = {
        "fit_s": round(fit_s, 1), "trained_on": "weeks 1-10, lead times 15 min-72 h", "training_samples": len(train),
        "model_size_kb": round(sum(len(m.booster_.model_to_string()) for m in models.values()) / 1024, 1),
        "memory_mb": memory_in_fresh_process("lightgbm", models, one),
        "latency_one_request": latency(lambda: predict_lightgbm(models, one))}
    print("ALT-F1 done", flush=True)

    short_train = train[train["lead"] <= SHORT_MODEL_MAX_LEAD]
    start = time.perf_counter()
    short_models = fit_lightgbm(short_train, band_weights=False)
    fit_s = time.perf_counter() - start
    short_pred = predict_lightgbm(short_models, val)
    t_c, cutoff_table = cutoff(val, short_pred, preds["baseline"])
    # The same rule read on ordinary times only (without the one event window), for the team to compare.
    t_c_ordinary, cutoff_ordinary = cutoff(val, short_pred, preds["baseline"], rows=~in_event_window(val))
    hybrid = lambda model_part, tc=t_c: np.where((val["lead"] < tc).to_numpy()[:, None],  # noqa: E731
                                                 model_part, preds["baseline"])
    preds["ALT-F2 hybrid"] = hybrid(short_pred)
    f2b = f"ALT-F2 hybrid, T_c {t_c_ordinary // 60} h (no event)"
    if t_c_ordinary != t_c:
        preds[f2b] = hybrid(short_pred, t_c_ordinary)
    near, far = one[one["lead"] < t_c], one[one["lead"] >= t_c]
    cost["ALT-F2 hybrid"] = {
        "fit_s": round(fit_s + cost["baseline"]["fit_s"], 1),
        "trained_on": f"weeks 1-10; LightGBM on lead times 15 min-{SHORT_MODEL_MAX_LEAD // 60} h",
        "training_samples": len(short_train),
        "model_size_kb": round(sum(len(m.booster_.model_to_string()) for m in short_models.values()) / 1024
                               + cost["baseline"]["model_size_kb"], 1),
        "memory_mb": round(memory_in_fresh_process("lightgbm", short_models, near) + cost["baseline"]["memory_mb"], 1),
        "latency_one_request": latency(lambda: (predict_lightgbm(short_models, near), predict_baseline(table, far)))}
    print(f"ALT-F2 done, T_c = {t_c} min", flush=True)

    if not args.skip_chronos:
        for label, name, covariates in [("ALT-F3 Chronos-2 + covariates", "amazon/chronos-2", True),
                                        ("ALT-F3b Chronos-Bolt-Small", "amazon/chronos-bolt-small", False)]:
            start = time.perf_counter()
            pipe = load_chronos(name)
            load_s = time.perf_counter() - start
            start = time.perf_counter()
            preds[label] = predict_chronos(pipe, s, val, covariates)
            run_s = time.perf_counter() - start
            first = pd.DatetimeIndex([one["origin"].iloc[0]])
            items = [item for lot in s.lots for item in chronos_inputs(s, first, lot, covariates)]
            request = lambda: run_chronos(pipe, items, covariates)  # noqa: E731  (3 lots in one call)
            cost[label] = {"fit_s": 0, "trained_on": "none (zero-shot)", "model": name,
                           "load_s": round(load_s, 1), "validation_run_s": round(run_s, 1),
                           "parameters_m": round(sum(p.numel() for p in pipe.model.parameters()) / 1e6, 1),
                           "memory_mb": memory_in_fresh_process("chronos", name, (items, covariates)),
                           "latency_one_request": latency(request)}
            print(f"{label} done", flush=True)
            del pipe

    # Uncalibrated results on all of weeks 11-12.
    per_lead, by_band, event_band = tables(score(val, preds))
    per_lead.round(4).to_csv(args.out / "per_lead.csv", index=False)
    by_band.round(4).to_csv(args.out / "by_band.csv", index=False)
    event_band.round(4).to_csv(args.out / "event_window.csv", index=False)
    usage_weighted(score(val, preds)).round(4).to_csv(args.out / "usage_weighted.csv", index=False)
    cutoff_table.join(cutoff_ordinary, rsuffix="_no_event_window").to_csv(
        args.out / "cutoff_short_model_vs_baseline.csv")

    # Interval calibration of the LightGBM parts on week 11, checked on week 12 against every method.
    f1_calibrated, f1_widen = calibrate(val, preds["ALT-F1 LightGBM"], [b[0] for b in BANDS])
    short_bands = [name for name, lo, hi in BANDS if hi <= SHORT_MODEL_MAX_LEAD]
    short_calibrated, f2_widen = calibrate(val, short_pred, short_bands)
    calibrated = dict(preds)
    calibrated["ALT-F1 LightGBM, calibrated"] = f1_calibrated
    calibrated["ALT-F2 hybrid, calibrated"] = hybrid(short_calibrated)
    if f2b in preds:
        calibrated[f2b + ", calibrated"] = hybrid(short_calibrated, t_c_ordinary)
    check_rows = (val["origin_week"] == CHECK_WEEK).to_numpy()   # target time is then in week 12 too
    check_table = band_table(score(val[check_rows], {k: v[check_rows] for k, v in calibrated.items()}))
    check_table.round(4).to_csv(args.out / "calibration_check_week12.csv", index=False)
    usage_weighted(score(val[check_rows], {k: v[check_rows] for k, v in calibrated.items()})).round(4).to_csv(
        args.out / "usage_weighted_week12_calibrated.csv", index=False)

    run = {"cutoff_T_c_minutes": t_c, "cutoff_T_c_minutes_without_event_window": t_c_ordinary,
           "cutoff_rule": "shortest lead where the ALT-F2 LightGBM (trained on leads <= 6 h) has higher all-day "
                          "validation MAE than the baseline; if none, the next lead after 6 h. "
                          "ALT-F2 = that LightGBM below T_c, baseline from T_c on",
           "team_T_c_reading": "without the event window (decided 2026-11-21)",
           "usage_shares": {"bands": [b[0] for b in USAGE_BANDS], **USAGE_SHARES},
           "calibration": {"method": "split conformal, one widening per lead-time band (spaces added to each side)",
                           "calibrated_on": f"forecasts with target time in week {CALIBRATION_WEEK}, without the event window",
                           "checked_on": f"forecasts made in week {CHECK_WEEK}",
                           "ALT-F1 widening": f1_widen, "ALT-F2 LightGBM part widening": f2_widen},
           "validation_forecast_times": int(val["origin"].nunique()), "validation_samples": len(val),
           "training_samples": len(train), "leakage_checks_passed": CHECKS,
           "cost": cost, "environment": environment()}
    (args.out / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    print(by_band.round(3).to_string(index=False))
    print(check_table.round(3).to_string(index=False))
    print(json.dumps(run, indent=2))


if __name__ == "__main__":
    main()
