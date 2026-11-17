"""Why is the post-confirmation path 2-4x slower in S1 than in S2?

Same process, same server, same requests. Conditions alternate run by run
(a, b, c, a, b, c, ...) so drift over time affects all three equally:
  a  confirm immediately (S2 as measured)
  b  sleep 2.1 s, then confirm (idle wait as long as an inference, no model)
  c  one real Qwen3 call through /api/interpret, then confirm (S1 as measured)
Only the /api/confirm part is compared.
"""

import csv
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import json  # noqa: E402

import measure_uc1 as m  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("idle_experiment.csv")
STAGES = ["HTTP.confirm_round_trip", "UC1.find_parking", "X.C.2.availability", "C.1.3.validate",
          "X.C.3.context", "X.C.4.rules", "C.1.4.eligibility"]

requests = json.loads(m.REQUESTS.read_text())["requests"]
http = m.HttpProduct()
rows = []
# one warm-up of each kind, not recorded
for warm in range(3):
    msg, trip = m.fill(requests[0], datetime.now().astimezone().replace(second=0, microsecond=0))
    http.post("/api/interpret", {"message": msg}, "HTTP.interpret_round_trip")
    http.post("/api/confirm", {"trip_request": trip}, "HTTP.confirm_round_trip")
for i in range(N):
    for cond in ("a", "b", "c"):
        req = requests[i % len(requests)]
        msg, trip = m.fill(req, datetime.now().astimezone().replace(second=0, microsecond=0))
        if cond == "b":
            time.sleep(2.1)
        elif cond == "c":
            http.post("/api/interpret", {"message": msg}, "HTTP.interpret_round_trip")
        _, recs = http.post("/api/confirm", {"trip_request": trip}, "HTTP.confirm_round_trip")
        for r in recs:
            if r["stage"] in STAGES:
                rows.append({"round": i + 1, "condition": cond, "stage": r["stage"],
                             "duration_ms": round(r["duration_ms"], 4)})
http.close()

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

by = defaultdict(list)
for r in rows:
    by[(r["stage"], r["condition"])].append(r["duration_ms"])
print(f"{N} rounds per condition. Median ms (mean).  a=no wait  b=2.1 s idle sleep  c=real Qwen3 call")
print(f"{'stage':26s} {'a':>16s} {'b':>16s} {'c':>16s}   b/a   c/a")
for s in STAGES:
    med = {c: statistics.median(by[(s, c)]) for c in "abc"}
    mean = {c: statistics.fmean(by[(s, c)]) for c in "abc"}
    print(f"{s:26s} " + " ".join(f"{med[c]:8.3f} ({mean[c]:6.3f})" for c in "abc")
          + f"  {med['b'] / med['a']:5.2f} {med['c'] / med['a']:5.2f}")
