"""Does an idle gap before /api/confirm slow it, with no language model involved?
Model unloaded. Gaps alternate run by run so drift affects all equally."""
import json, statistics, sys, time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import measure_uc1 as m
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
GAPS = [0.0, 0.1, 0.5, 2.0]
reqs = json.loads(m.REQUESTS.read_text())["requests"]
m.unload_model()
http = m.HttpProduct()
for _ in range(3):  # warm-up
    _, trip = m.fill(reqs[0], datetime.now().astimezone().replace(second=0, microsecond=0))
    http.post("/api/confirm", {"trip_request": trip}, "HTTP.confirm_round_trip")
res = defaultdict(lambda: defaultdict(list))
for i in range(N):
    for gap in GAPS:
        _, trip = m.fill(reqs[i % len(reqs)], datetime.now().astimezone().replace(second=0, microsecond=0))
        time.sleep(gap)
        _, recs = http.post("/api/confirm", {"trip_request": trip}, "HTTP.confirm_round_trip")
        for r in recs:
            res[gap][r["stage"]].append(r["duration_ms"])
http.close()
print(f"model loaded during test: {m.model_loaded()}  ({N} runs per gap, medians in ms)")
for gap in GAPS:
    d = res[gap]
    print(f"gap {gap:>4.1f} s  round_trip={statistics.median(d['HTTP.confirm_round_trip']):7.3f}  "
          f"X.C.2={statistics.median(d['X.C.2.availability']):7.3f}  validate={statistics.median(d['C.1.3.validate']):6.3f}  "
          f"context={statistics.median(d['X.C.3.context']):6.3f}  rules={statistics.median(d['X.C.4.rules']):6.3f}")
