"""Train the selected forecast approach (ALT-F2, hybrid) for A2 and save it for the product.

ALT-F2 (Ch11 trade study, T_c read without the 2026-11-07 event window):
  - lead times shorter than T_c: LightGBM quantile models (10/50/90%) of the rate's
    departure from the same-weekday-and-time profile, trained on simulated weeks 1-10
    for lead times up to 6 h, with the settings frozen on 2026-11-21;
  - lead times from T_c to 72 h: the lot x day-of-week x 15-minute time-slot baseline
    (10/50/90% quantiles) from the same weeks.

The 80% interval of the LightGBM part is widened by split conformal calibration fitted
on week 11 without the event window (one widening per lead-time band, in spaces).
T_c is recomputed on weeks 11-12 without the event window and must equal the team's
reading (180 minutes). Everything reuses scripts/spike_forecast.py, so the saved
models are the ones the trade study scored. Weeks 13-15 (holdout) are never read.

Writes estimate_arrival_time_availability/model/:
  short_q10.txt, short_q50.txt, short_q90.txt  LightGBM boosters
  baseline.csv                                  baseline quantiles as occupancy rates
  manifest.json                                 T_c, widenings, features, data hash, settings

Usage:
  python scripts/train_forecast.py
"""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spike_forecast as sf  # noqa: E402

OUT = sf.ROOT / "estimate_arrival_time_availability" / "model"
TEAM_T_C_MINUTES = 180   # team reading, 2026-11-21 (without the event window)


def main() -> None:
    df = sf.load()                                        # weeks 1-12 only
    s = sf.Series(df)
    train = sf.samples(s, "train", 15)
    val = sf.samples(s, "validation", 60)

    table = sf.fit_baseline(df[df["split"] == "train"])
    short_train = train[train["lead"] <= sf.SHORT_MODEL_MAX_LEAD]
    models = sf.fit_lightgbm(short_train, band_weights=False)

    short_pred = sf.predict_lightgbm(models, val)
    t_c, _ = sf.cutoff(val, short_pred, sf.predict_baseline(table, val), rows=~sf.in_event_window(val))
    if t_c != TEAM_T_C_MINUTES:
        raise SystemExit(f"T_c recomputed as {t_c} min, not the team's {TEAM_T_C_MINUTES} min; stopping")
    bands = [name for name, lo, hi in sf.BANDS if hi <= sf.SHORT_MODEL_MAX_LEAD]
    _, widen = sf.calibrate(val, short_pred, bands)

    OUT.mkdir(parents=True, exist_ok=True)
    for q, model in models.items():
        model.booster_.save_model(str(OUT / f"short_q{int(q * 100)}.txt"))
    capacity = df.groupby("lot_id")["capacity"].first()
    rates = table.div(capacity, axis=0, level="lot_id").round(6)
    rates.columns = [f"q{int(q * 100)}" for q in rates.columns]
    rates.reset_index().to_csv(OUT / "baseline.csv", index=False)

    manifest = {
        "approach": "ALT-F2 hybrid: LightGBM below T_c, lot/day/time-slot baseline from T_c to 72 h",
        "t_c_minutes": t_c,
        "t_c_reading": "without the 2026-11-07 event window (team decision 2026-11-21)",
        "model_grid_minutes": [g for g in [0, 15, 30, 45, 60] + list(range(120, 360, 60)) if g < t_c],
        "interval_widening_spaces": widen,
        "widening_bands_minutes": {name: [lo, hi] for name, lo, hi in sf.BANDS if name in widen},
        "lot_codes": {lot: code for code, lot in enumerate(s.lots)},
        "training_capacity": capacity.astype(int).to_dict(),
        "features": sf.FEATURES,
        "profile_weeks": sf.PROFILE_WEEKS,
        "series_start": df["t"].min().isoformat(),
        "lightgbm_settings": {"n_estimators": 400, "learning_rate": 0.05, "num_leaves": 63,
                              "min_child_samples": 100, "random_state": sf.SEED,
                              "frozen_on": "2026-11-21"},
        "trained_on": "simulated weeks 1-10, leads 15 min to 6 h, forecast every 15 min",
        "calibrated_on": "week 11 without the event window",
        "data_sha256": hashlib.sha256(sf.DATA.read_bytes()).hexdigest(),
        "simulated": True,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"t_c_minutes": t_c, "widening": widen,
                      "short_training_samples": len(short_train),
                      "files": sorted(p.name for p in OUT.iterdir()),
                      "size_kb": round(sum(p.stat().st_size for p in OUT.iterdir()) / 1024)}, indent=2))


if __name__ == "__main__":
    main()
