"""Is the post-confirmation path slower while qwen3:4b is loaded in Ollama?
Same process: S2 x N with the model unloaded, then one model call to load it,
then S2 x N with the model loaded (no further model calls), then unload and S2 x N again."""
import json, statistics, sys
from datetime import datetime
from pathlib import Path
REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
import measure_uc1 as m
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
reqs = json.loads(m.REQUESTS.read_text())["requests"]
http = m.HttpProduct()
def block(label):
    vals = {"HTTP.confirm_round_trip": [], "X.C.2.availability": [], "C.1.3.validate": [], "X.C.3.context": []}
    for i in range(N):
        _, trip = m.fill(reqs[i % len(reqs)], datetime.now().astimezone().replace(second=0, microsecond=0))
        _, recs = http.post("/api/confirm", {"trip_request": trip}, "HTTP.confirm_round_trip")
        for r in recs:
            if r["stage"] in vals: vals[r["stage"]].append(r["duration_ms"])
    print(f"{label:34s} loaded={m.model_loaded()!s:5s} " + "  ".join(f"{k.split('.')[-1] if k!='HTTP.confirm_round_trip' else 'round_trip'}={statistics.median(v):.3f}" for k, v in vals.items()))
m.unload_model()
block("1 model unloaded")
msg, _ = m.fill(reqs[0], datetime.now().astimezone().replace(second=0, microsecond=0))
http.post("/api/interpret", {"message": msg}, "HTTP.interpret_round_trip")
block("2 model loaded, no further calls")
m.unload_model()
block("3 model unloaded again")
http.close()
