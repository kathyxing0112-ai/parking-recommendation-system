"""Lab Manual §10.4: run UC.1 many times and record per-stage durations.

Scenario 1 (baseline): the driver's message goes through C.1.1 and the local
Qwen3 model. If the model's reply is complete, the driver confirms it
unchanged; otherwise the driver fills in the six-field form. Then the
confirmed request goes through C.1, C.3 and the result assembly.
Scenario 2 (alternative): the driver fills in the six-field form directly,
and no model is called.

Each run uses the next request from measurements/uc1_requests.json, with clock
times filled in for the moment the run starts. Stage durations come from
stage_timing (one record per participant boundary). The time the driver
spends reading and confirming is not measured: only system time is.

Output goes to measurements/runs/<UTC time>-s<scenario>/, which git ignores,
so raw measurements are not pushed by accident before the team's simulation
parameters are committed (team rule for Ch10):
  stages.csv        one row per run and stage
  runs.csv          one row per run: request, path taken, status, total
  environment.json  machine, Python, Ollama and model versions, settings
  summary.md        n / min / median / mean / p95 / max per stage

Usage:
  python scripts/measure_uc1.py --scenario 1 --runs 50 --cold-first
  python scripts/measure_uc1.py --scenario 2 --runs 50
  python scripts/measure_uc1.py --scenario 1 --runs 30 --cold-each   # every run cold (slow)
  python scripts/measure_uc1.py --scenario 1 --runs 50 --cold-first --http

--http goes through the browser entry point instead of calling the driver
interface directly: the script starts web_app's server on a free loopback port
inside this process and POSTs to /api/interpret and /api/confirm, as the page
does. The client times each round trip (HTTP.*_round_trip), and the server-side
stages are still recorded on the handler thread. HTTP.confirm_round_trip is the
SR-13 window up to the reply arriving; page rendering is not included.
With --http, Scenario 1 also loads the model when the server starts, as
web_app.main does; with --cold-first the model is unloaded before that, so
run 1 shows what the first driver after a product start meets.
"""

import argparse
import csv
import json
import platform
import queue
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cornell_driver_interface as driver_interface  # noqa: E402
import language_model  # noqa: E402
import stage_timing  # noqa: E402
import web_app  # noqa: E402

REQUESTS = ROOT / "measurements" / "uc1_requests.json"
RUNS_DIR = ROOT / "measurements" / "runs"
OLLAMA = "http://127.0.0.1:11434"
TOP_LEVEL = ("UC1.interpret_request", "UC1.find_parking")
HTTP_TOP_LEVEL = ("HTTP.interpret_round_trip", "HTTP.confirm_round_trip")


class HttpProduct:
    """web_app's server on a free loopback port, recording server-side stages per request."""

    def __init__(self, warm_up: bool = False):
        self.records: queue.Queue = queue.Queue()
        records = self.records

        class TimedHandler(web_app.DriverRequestHandler):
            def do_POST(self) -> None:
                stage_timing.start()
                try:
                    super().do_POST()
                finally:
                    records.put(stage_timing.stop())

        self.server = web_app.ThreadingHTTPServer((web_app.HOST, 0), TimedHandler)
        self.base = f"http://{web_app.HOST}:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        # web_app.main loads the model when the product starts; do the same,
        # and wait for it, so run 1 meets the product as a driver would.
        self.warmed_up = language_model.warm_up_model() if warm_up else None

    def post(self, path: str, payload: dict, parent: str) -> tuple[dict, list[dict]]:
        request = urllib.request.Request(self.base + path, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
        entry = time.perf_counter_ns()
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.loads(response.read())
        exit_ = time.perf_counter_ns()
        server = self.records.get(timeout=10)
        for record in server:
            record["parent"] = record["parent"] or parent
        client = {"stage": parent, "parent": None, "entry_ns": entry, "exit_ns": exit_,
                  "duration_ms": (exit_ - entry) / 1e6}
        return body, server + [client]

    def close(self) -> None:
        self.server.shutdown()


def clock(at: datetime) -> str:
    """'2:45 pm' -- how a driver would write the time."""
    return at.strftime("%I:%M %p").lstrip("0").lower()


def fill(request: dict, start: datetime) -> tuple[str, dict]:
    """The message and the six-field form for a run that starts at start."""
    form = request["form"]
    arrive = start + timedelta(minutes=form["arrive_in_minutes"])
    leave = arrive + timedelta(minutes=form["stay_minutes"])
    message = request["message_template"].replace("{arrive}", clock(arrive)).replace("{leave}", clock(leave))
    trip = {
        "destination": form["destination"],
        "arrival_time": arrive.isoformat(),
        "departure_time": leave.isoformat(),
        "vehicle_category": form["vehicle_category"],
        "declared_eligibility": form["declared_eligibility"],
        "access_needs": form["access_needs"],
    }
    return message, trip


def ollama(path: str, body: dict | None = None, timeout: float = 10) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(OLLAMA + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def unload_model() -> None:
    """Ask Ollama to drop the model from memory, so the next call is a cold start."""
    ollama("/api/generate", {"model": language_model.MODEL_NAME, "keep_alive": 0}, timeout=30)
    for _ in range(50):  # wait until it is really gone
        loaded = [m["name"] for m in ollama("/api/ps").get("models", [])]
        if language_model.MODEL_NAME not in loaded:
            return
        time.sleep(0.2)


def model_loaded() -> bool:
    try:
        return language_model.MODEL_NAME in [m["name"] for m in ollama("/api/ps").get("models", [])]
    except (urllib.error.URLError, OSError):
        return False


def environment(args) -> dict:
    def run(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return None

    env = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scenario": args.scenario,
        "runs": args.runs,
        "cold_first": args.cold_first,
        "cold_each": args.cold_each,
        "http": args.http,
        "request_set": str(REQUESTS.relative_to(ROOT)),
        "git_commit": run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"]),
        "git_dirty": bool(run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"])),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": run(["sysctl", "-n", "machdep.cpu.brand_string"]) or platform.processor(),
        "memory_bytes": run(["sysctl", "-n", "hw.memsize"]),
        "model": language_model.MODEL_NAME,
        "model_options": language_model.MODEL_OPTIONS,
    }
    if args.scenario == 1:
        env["ollama_version"] = ollama("/api/version").get("version")
        tags = {m["name"]: m for m in ollama("/api/tags").get("models", [])}
        model = tags.get(language_model.MODEL_NAME, {})
        env["model_digest"] = model.get("digest")
        env["model_details"] = model.get("details")
    return env


def one_run(scenario: int, request: dict, http: "HttpProduct | None" = None) -> tuple[dict, list[dict]]:
    message, form_trip = fill(request, datetime.now().astimezone().replace(second=0, microsecond=0))
    if http is not None:
        records = []
        if scenario == 1:
            interpreted, rec = http.post("/api/interpret", {"message": message}, "HTTP.interpret_round_trip")
            records += rec
        result_records = None
    else:
        stage_timing.start()
    try:
        if scenario == 1:
            if http is None:
                interpreted = driver_interface.submit_trip_request(message)
            status = interpreted["status"]
            if status == "complete":
                path, confirmed = "model_confirmed", interpreted["trip_request"]
            else:
                path, confirmed = "form_fallback", form_trip
        else:
            status, path, confirmed = "not_called", "form", form_trip
        if http is None:
            result = driver_interface.confirm_trip_requirements(confirmed)
        else:
            result, result_records = http.post("/api/confirm", {"trip_request": confirmed},
                                               "HTTP.confirm_round_trip")
    finally:
        if http is None:
            records = stage_timing.stop()
    if http is not None:
        records += result_records
    top = HTTP_TOP_LEVEL if http is not None else TOP_LEVEL
    total = sum(r["duration_ms"] for r in records if r["stage"] in top)
    run = {
        "request_id": request["id"],
        "path": path,
        "interpret_status": status,
        "result_status": result.get("status", "ok"),
        "ranked_options": len(result.get("ranked_options", [])),
        "system_total_ms": round(total, 3),
    }
    return run, records


def describe(values: list[float]) -> dict:
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]
    return {"n": len(values), "min": ordered[0], "median": statistics.median(ordered),
            "mean": statistics.fmean(ordered), "p95": p95, "max": ordered[-1],
            "std": statistics.stdev(ordered) if len(ordered) > 1 else 0.0}


def summary_table(rows: list[dict], title: str) -> list[str]:
    by_stage: dict[str, list[float]] = {}
    for row in rows:
        by_stage.setdefault(row["stage"], []).append(row["duration_ms"])
    lines = [f"### {title}", "",
             "| Stage | Participant | n | min ms | median ms | mean ms | p95 ms | max ms | std ms |",
             "|---|---|---|---|---|---|---|---|---|"]
    order = list(stage_timing.STAGES) + ["UC1.system_total"]
    for name in sorted(by_stage, key=lambda s: order.index(s) if s in order else len(order)):
        d = describe(by_stage[name])
        participant = stage_timing.STAGES.get(name, ("sum of the top-level stages", ""))[0]
        lines.append(f"| {name} | {participant} | {d['n']} | {d['min']:.2f} | {d['median']:.2f} | "
                     f"{d['mean']:.2f} | {d['p95']:.2f} | {d['max']:.2f} | {d['std']:.2f} |")
    return lines + [""]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", type=int, choices=(1, 2), required=True)
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--cold-first", action="store_true", help="unload the model before run 1")
    parser.add_argument("--cold-each", action="store_true", help="unload the model before every run")
    parser.add_argument("--http", action="store_true",
                        help="go through web_app's POST /api/interpret and /api/confirm (see above)")
    parser.add_argument("--out", type=Path, help="output folder (default: measurements/runs/<time>-s<scenario>)")
    args = parser.parse_args()
    if args.runs < 30:
        print("note: Lab Manual 10.4 asks for at least thirty runs", file=sys.stderr)

    if args.scenario == 1:
        try:
            ollama("/api/version")
        except (urllib.error.URLError, OSError):
            sys.exit("Ollama is not running at 127.0.0.1:11434. Start it (ollama serve) before Scenario 1; "
                     "otherwise every run would take the form fallback and measure nothing about the model.")

    requests = json.loads(REQUESTS.read_text())["requests"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or RUNS_DIR / f"{stamp}-s{args.scenario}{'-http' if args.http else ''}"
    out.mkdir(parents=True, exist_ok=True)
    env = environment(args)

    if args.http and args.scenario == 1 and args.cold_first:
        unload_model()  # start from an unloaded model, then let the product start as usual
    http = HttpProduct(warm_up=args.scenario == 1) if args.http else None
    if http is not None:
        env["startup_warm_up"] = http.warmed_up
    run_rows, stage_rows = [], []
    for i in range(args.runs):
        request = requests[i % len(requests)]
        if args.scenario == 1 and (args.cold_each or (args.cold_first and i == 0 and not args.http)):
            unload_model()
        model_state = ("cold" if not model_loaded() else "warm") if args.scenario == 1 else "not_used"
        run, records = one_run(args.scenario, request, http)
        run = {"run": i + 1, "scenario": args.scenario, "model_state": model_state,
               "first_in_process": i == 0, **run}
        run_rows.append(run)
        for r in records:
            stage_rows.append({"run": i + 1, "scenario": args.scenario, "request_id": request["id"],
                               "path": run["path"], "model_state": model_state, "stage": r["stage"],
                               "parent": r["parent"] or "", "duration_ms": round(r["duration_ms"], 3)})
        stage_rows.append({"run": i + 1, "scenario": args.scenario, "request_id": request["id"],
                           "path": run["path"], "model_state": model_state, "stage": "UC1.system_total",
                           "parent": "", "duration_ms": run["system_total_ms"]})
        print(f"run {i + 1:>3}/{args.runs}  {request['id']}  {model_state:<8} {run['path']:<16} "
              f"{run['system_total_ms']:>10.1f} ms  options={run['ranked_options']}")

    if http is not None:
        http.close()
    with open(out / "stages.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(stage_rows[0]))
        writer.writeheader()
        writer.writerows(stage_rows)
    with open(out / "runs.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(run_rows[0]))
        writer.writeheader()
        writer.writerows(run_rows)
    (out / "environment.json").write_text(json.dumps(env, indent=2) + "\n")

    paths = {}
    for run in run_rows:
        paths[run["path"]] = paths.get(run["path"], 0) + 1
    lines = [f"# UC.1 Scenario {args.scenario}: {args.runs} runs" + (" through HTTP" if args.http else ""), "",
             f"Measured {env['measured_at_utc']} on {env['cpu']} ({env['platform']}), commit {env['git_commit']}"
             + (" with uncommitted changes" if env["git_dirty"] else "") + ".", "",
             "Paths taken: " + ", ".join(f"{k} {v}" for k, v in sorted(paths.items())), ""]
    lines += summary_table(stage_rows, "All runs")
    if args.scenario == 1:
        warm = [r for r in stage_rows if r["model_state"] == "warm" and r["run"] != 1]
        cold = [r for r in stage_rows if r["model_state"] == "cold"]
        if warm:
            lines += summary_table(warm, "Warm model only (excluding run 1)")
        if cold:
            lines += summary_table(cold, "Cold model only")
    (out / "summary.md").write_text("\n".join(lines))
    shown = out.resolve().relative_to(ROOT) if out.resolve().is_relative_to(ROOT) else out
    print(f"\nwrote {shown}/ (stages.csv, runs.csv, environment.json, summary.md)")


if __name__ == "__main__":
    main()
