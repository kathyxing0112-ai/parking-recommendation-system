"""Ch11 backtest on training weeks only, written before the single holdout run.

Train weeks 1-6, forecast weeks 7-10 (fall break 10/12-13, homecoming game 10/17,
evening concert in week 10). LightGBM settings are the frozen ones; ALT-F2 uses
T_c = 3 h; its short model is calibrated on week 7 (no event window) and checked
on forecasts made in weeks 8-10. Scores are weighted by the team's request shares.
Weeks 11-15 are not read. Simulated data only.

Usage:
  python scripts/backtest_forecast.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spike_forecast as sf  # noqa: E402
df = sf.load(); df = df[df.sim_week <= 10].copy()
df["split"] = np.where(df.sim_week <= 6, "train", "validation")
s = sf.Series(df)
train = sf.samples(s, "train", 15); val = sf.samples(s, "validation", 60)
base = sf.predict_baseline(sf.fit_baseline(df[df.split == "train"]), val)
short = sf.predict_lightgbm(sf.fit_lightgbm(train[train.lead <= 360], band_weights=False), val)
f1 = sf.predict_lightgbm(sf.fit_lightgbm(train, band_weights=True), val)
y = val.y.to_numpy(); near = (val.lead < 180).to_numpy()
ev = (val.event_flag == 1).to_numpy(); brk = (val.is_break == 1).to_numpy()
day = val.target_hour.between(7, 18).to_numpy()
# calibrate short model on week 7 (no event), check weeks 8-10
sb = val.lead.map(sf.band_of).to_numpy(); sc = np.maximum(short[:,0]-y, y-short[:,2]); cal = short.copy()
c = (val.target_week == 7).to_numpy() & ~ev
for b in ["0-1h", "1-6h"]:
    m = c & (sb == b); n = m.sum(); w = np.quantile(sc[m], min(1, np.ceil((n+1)*.8)/n), method="higher")
    cal[sb == b, 0] -= w; cal[sb == b, 2] += w
cal = sf.finish(cal, val.capacity.to_numpy())
f2 = np.where(near[:, None], cal, base)
bands = [("0-1h",0,60),("1-3h",60,180),("3-6h",180,360),("6-24h",360,1440),("24-72h",1440,4320)]
ub = val.lead.map(lambda l: next(n for n,a,b in bands if a<l<=b)).to_numpy(); w = np.array([.5,.25,.1,.1,.05])
def wavg(v, rows):
    t = pd.Series(v[rows]).groupby(ub[rows]).mean().reindex([b[0] for b in bands]); return float((t.to_numpy()*w).sum())
chk = (val.origin_week >= 8).to_numpy()
for name, rows in [("weeks 8-10 all (no event)", chk & ~ev), ("weeks 8-10 daytime (no event)", chk & ~ev & day),
                   ("break days 10/12-13", chk & brk), ("event windows", chk & ev)]:
    out = {k: round(wavg(np.abs(p[:,1]-y), rows), 2) for k, p in [("baseline", base), ("F1", f1), ("F2", f2)]}
    cov = round(wavg(((y >= f2[:,0]) & (y <= f2[:,2])).astype(float), rows), 3)
    bias = round(wavg(f2[:,1]-y, rows), 2)
    print(f"{name:32s} n={rows.sum():6d}  MAE {out}  F2 coverage {cov}  F2 bias {bias}")
print("event days in weeks 8-10:", sorted(val[ev & chk].target_date.unique()))
