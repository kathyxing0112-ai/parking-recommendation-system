"""Lab Manual §10.4: set measured UC.1 stage times against the Innoslate simulation.

Reads the B4 simulation workbook (100 Monte Carlo samples per action, X2 V0.3)
and two measurement runs made with scripts/measure_uc1.py --http, and writes:
  comparison.csv           one row per scenario and compared stage
  comparison.md            the same, as a table for the report
  fig_stage_comparison.png measured distribution vs simulated distribution per stage
  fig_windows.png          windows C and D: simulated vs measured, with the 5 s SR-13 line

Each simulated stage maps to the measured stage(s) that cover the same work
(MAP below). Where the code joins two modeled actions, the simulated samples
are added run by run before comparing (s1.6 + s1.7 -> X.C.2.availability).

Usage:
  python scripts/compare_sim_measured.py \\
      --sim docs/measurements/simulation/HW6_B4_Simulation_Results.xlsx \\
      --s1 docs/measurements/2026-11-15/s1-http --s2 docs/measurements/2026-11-15/s2-http \\
      --out docs/measurements/2026-11-15
"""

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import openpyxl  # noqa: E402

# (label, simulated actions added together, measured expression)
# A measured expression is a stage name, or ("minus", a, b, ...) for a - b - ...
MAP = {
    1: [
        ("s1.2 Initiate interpretation", ["s1.2"],
         ("minus", "UC1.interpret_request", "C.1.1.model_call", "C.1.1.contract_check")),
        ("s1.3 Language model inference", ["s1.3"], "C.1.1.model_call"),
        ("s1.4 Structure criteria", ["s1.4"], "C.1.1.contract_check"),
        ("s1.6 + s1.7 Retrieve parking records", ["s1.6", "s1.7"], "X.C.2.availability"),
        ("s1.8 Validate records", ["s1.8"], "C.1.3.validate"),
        ("s1.9 Parking rules (X.C.4)", ["s1.9"], "X.C.4.rules"),
        ("s1.10 Filter eligible options", ["s1.10"], "C.1.4.eligibility"),
        ("s1.11 Rank recommendations", ["s1.11"], "C.3.rank"),
        ("s1.12 Deliver recommendations", ["s1.12"],
         ("plus_http", "C.0.assemble_result", "HTTP.confirm_round_trip", "UC1.find_parking")),
        ("Window C: interpretation (s1.2-s1.4)", ["C Interpretation (s)"], "UC1.interpret_request"),
        ("Window D: confirmed request to delivery", ["D SR-13 window (s)"], "HTTP.confirm_round_trip"),
    ],
    2: [
        ("s2.2 + s2.3 Retrieve parking records", ["s2.2", "s2.3"], "X.C.2.availability"),
        ("s2.4 Validate records", ["s2.4"], "C.1.3.validate"),
        ("s2.5 Parking rules (X.C.4)", ["s2.5"], "X.C.4.rules"),
        ("s2.6 Filter eligible options", ["s2.6"], "C.1.4.eligibility"),
        ("s2.7 Rank recommendations", ["s2.7"], "C.3.rank"),
        ("s2.8 Deliver recommendations", ["s2.8"],
         ("plus_http", "C.0.assemble_result", "HTTP.confirm_round_trip", "UC1.find_parking")),
        ("Window D: confirmed request to delivery", ["D SR-13 window (s)"], "HTTP.confirm_round_trip"),
    ],
}
# Measured stages with no modeled action (reported, not compared).
UNMODELED = ["X.C.3.context", "C.1.1.confirm", "C.1.2.requests"]
SR13_LIMIT_S = 5.0


def sim_samples(path: Path, scenario: int) -> dict[str, list[float]]:
    ws = openpyxl.load_workbook(path, data_only=True)[f"S{scenario} Samples"]
    rows = list(ws.iter_rows(values_only=True))
    header_at = next(i for i, r in enumerate(rows) if r and r[0] == "Run ID")
    header = rows[header_at]
    columns = defaultdict(list)
    for row in rows[header_at + 1:]:
        if row[0] is None:
            continue
        for name, value in zip(header, row):
            if isinstance(value, (int, float)):
                columns[name].append(float(value))
    return columns


def measured_runs(run_dir: Path) -> tuple[dict[int, dict[str, float]], dict[int, str]]:
    per_run: dict[int, dict[str, float]] = defaultdict(dict)
    state = {}
    with open(run_dir / "stages.csv") as f:
        for row in csv.DictReader(f):
            per_run[int(row["run"])][row["stage"]] = float(row["duration_ms"]) / 1000
            state[int(row["run"])] = row["model_state"]
    return per_run, state


def measured_values(per_run, expression) -> list[float]:
    values = []
    for stages in per_run.values():
        if isinstance(expression, str):
            if expression in stages:
                values.append(stages[expression])
        elif expression[0] == "minus":
            values.append(stages[expression[1]] - sum(stages[s] for s in expression[2:]))
        elif expression[0] == "plus_http":  # assembly + (HTTP round trip - server time)
            _, assemble, trip, server = expression
            values.append(stages[assemble] + stages[trip] - stages[server])
    return values


def stats(values: list[float]) -> dict:
    ordered = sorted(values)
    return {"n": len(values), "mean": statistics.fmean(values), "sd": statistics.stdev(values),
            "median": statistics.median(values), "min": ordered[0], "max": ordered[-1],
            "p95": ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]}


def ms(x: float) -> str:
    v = x * 1000
    return f"{v:,.1f}" if v >= 10 else f"{v:.2f}" if v >= 0.1 else f"{v:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sim", type=Path, required=True)
    parser.add_argument("--s1", type=Path, required=True)
    parser.add_argument("--s2", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows, plot_data, unmodeled = [], {}, []
    for scenario, run_dir in ((1, args.s1), (2, args.s2)):
        sim = sim_samples(args.sim, scenario)
        per_run, state = measured_runs(run_dir)
        for label, actions, expression in MAP[scenario]:
            simulated = [sum(vals) for vals in zip(*(sim[a] for a in actions))]
            measured = measured_values(per_run, expression)
            s, m = stats(simulated), stats(measured)
            rows.append({"scenario": f"S{scenario}", "stage": label,
                         "sim_n": s["n"], "sim_mean_ms": s["mean"] * 1000, "sim_sd_ms": s["sd"] * 1000,
                         "sim_min_ms": s["min"] * 1000, "sim_max_ms": s["max"] * 1000,
                         "meas_n": m["n"], "meas_mean_ms": m["mean"] * 1000, "meas_sd_ms": m["sd"] * 1000,
                         "meas_median_ms": m["median"] * 1000, "meas_p95_ms": m["p95"] * 1000,
                         "meas_min_ms": m["min"] * 1000, "meas_max_ms": m["max"] * 1000,
                         "sim_to_meas_mean_ratio": s["mean"] / m["mean"] if m["mean"] > 0 else float("nan")})
            plot_data[(scenario, label)] = (simulated, measured)
        if scenario == 1:
            warm = [v["C.1.1.model_call"] for r, v in per_run.items() if state[r] == "warm"]
            cold = [v["C.1.1.model_call"] for r, v in per_run.items() if state[r] == "cold"]
            s = stats(sim["s1.3"])
            w = stats(warm)
            if cold:  # a warm-only row adds nothing when every run was warm
                rows.append({"scenario": "S1", "stage": "s1.3 inference, warm model only",
                             "sim_n": s["n"], "sim_mean_ms": s["mean"] * 1000, "sim_sd_ms": s["sd"] * 1000,
                             "sim_min_ms": s["min"] * 1000, "sim_max_ms": s["max"] * 1000,
                             "meas_n": w["n"], "meas_mean_ms": w["mean"] * 1000, "meas_sd_ms": w["sd"] * 1000,
                             "meas_median_ms": w["median"] * 1000, "meas_p95_ms": w["p95"] * 1000,
                             "meas_min_ms": w["min"] * 1000, "meas_max_ms": w["max"] * 1000,
                             "sim_to_meas_mean_ratio": s["mean"] / w["mean"]})
            cold_note = (f"S1 cold-start inference (model unloaded before run 1): {', '.join(ms(c) for c in cold)} ms."
                         if cold else "S1 had no cold start: the product loads the model when it starts "
                         "(warm-up), so run 1 was warm.")
        for stage in UNMODELED:
            vals = [v[stage] for v in per_run.values() if stage in v]
            if vals:
                st = stats(vals)
                unmodeled.append((f"S{scenario}", stage, st))

    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "comparison.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: round(v, 3) if isinstance(v, float) else v for k, v in row.items()})

    d1 = next(r for r in rows if r["scenario"] == "S1" and r["stage"].startswith("Window D"))
    d2 = next(r for r in rows if r["scenario"] == "S2" and r["stage"].startswith("Window D"))
    lines = [
        "# Simulated vs measured UC.1 stage times", "",
        f"Simulation: Innoslate Monte Carlo, 100 runs per scenario, X2 V0.3 ({args.sim.name}). "
        f"Measurement: 50 runs per scenario through web_app POST endpoints "
        f"({args.s1.name}, {args.s2.name}). All times in milliseconds.", "",
        "| Scen. | Stage | Sim mean | Sim SD | Sim min-max | Meas. n | Meas. mean | Meas. SD | Meas. median | Meas. p95 | Meas. min-max | Sim / meas. |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['scenario']} | {r['stage']} | {ms(r['sim_mean_ms'] / 1000)} | {ms(r['sim_sd_ms'] / 1000)} | "
            f"{ms(r['sim_min_ms'] / 1000)}-{ms(r['sim_max_ms'] / 1000)} | {r['meas_n']} | "
            f"{ms(r['meas_mean_ms'] / 1000)} | {ms(r['meas_sd_ms'] / 1000)} | {ms(r['meas_median_ms'] / 1000)} | "
            f"{ms(r['meas_p95_ms'] / 1000)} | {ms(r['meas_min_ms'] / 1000)}-{ms(r['meas_max_ms'] / 1000)} | "
            f"{r['sim_to_meas_mean_ratio']:.1f}x |")
    lines += ["", cold_note, "",
              "Measured stages with no modeled action:", "",
              "| Scen. | Stage | n | mean ms | max ms |", "|---|---|---|---|---|"]
    for scen, stage, st in unmodeled:
        lines.append(f"| {scen} | {stage} | {st['n']} | {ms(st['mean'])} | {ms(st['max'])} |")
    options = []
    for run_dir in (args.s1, args.s2):
        with open(run_dir / "runs.csv") as f:
            options += [int(r["ranked_options"]) for r in csv.DictReader(f)]
    two = "every run returned two options" if all(o == 2 for o in options) else \
        f"{sum(o == 2 for o in options)} of {len(options)} runs returned two options"
    lines += ["", f"SR-13 check (window D, {SR13_LIMIT_S:.0f} s limit, {two}): "
              f"S1 max {ms(d1['meas_max_ms'] / 1000)} ms over {d1['meas_n']} runs; "
              f"S2 max {ms(d2['meas_max_ms'] / 1000)} ms over {d2['meas_n']} runs. "
              "Page rendering is not included.", ""]
    (args.out / "comparison.md").write_text("\n".join(lines))

    # Figure 1: per-stage distributions on a log axis (stages span 0.01 ms to 4 s).
    stage_keys = [k for k in plot_data if not k[1].startswith("Window")]
    fig, ax = plt.subplots(figsize=(10, 0.45 * len(stage_keys) + 1.5))
    positions = list(range(len(stage_keys)))
    floor = 1e-3  # 1 microsecond in ms, so zero-length stages show on the log axis
    sim_data = [[max(v * 1000, floor) for v in plot_data[k][0]] for k in stage_keys]
    meas_data = [[max(v * 1000, floor) for v in plot_data[k][1]] for k in stage_keys]
    b1 = ax.boxplot(sim_data, positions=[p + 0.2 for p in positions], vert=False, widths=0.32,
                    patch_artist=True, showfliers=False)
    b2 = ax.boxplot(meas_data, positions=[p - 0.2 for p in positions], vert=False, widths=0.32,
                    patch_artist=True, showfliers=False)
    for patch in b1["boxes"]:
        patch.set_facecolor("#9db8d9")
    for patch in b2["boxes"]:
        patch.set_facecolor("#e8a87c")
    ax.set_yticks(positions)
    ax.set_yticklabels([f"{'S1' if k[0] == 1 else 'S2'}  {k[1]}" for k in stage_keys], fontsize=8)
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("Stage duration (ms, log scale)")
    ax.legend([b1["boxes"][0], b2["boxes"][0]], ["Simulated (Innoslate, n=100)", "Measured (product, n=50)"],
              loc="lower right", fontsize=8)
    ax.set_title("UC.1 per-stage duration: simulated vs measured")
    ax.grid(axis="x", which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.out / "fig_stage_comparison.png", dpi=200)
    plt.close(fig)

    # Figure 2: windows C and D with the SR-13 limit.
    windows = [k for k in plot_data if k[1].startswith("Window")]
    fig, axes = plt.subplots(1, len(windows), figsize=(4 * len(windows), 3.4))
    for ax, key in zip(axes, windows):
        simulated, measured = plot_data[key]
        ax.boxplot([[v for v in simulated], [v for v in measured]], tick_labels=["Simulated", "Measured"],
                   patch_artist=True, showfliers=True)
        if key[1].startswith("Window D"):
            ax.axhline(SR13_LIMIT_S, color="#c0392b", linestyle="--", linewidth=1)
            ax.text(1.5, SR13_LIMIT_S * 0.97, "SR-13: 5 s", color="#c0392b", ha="center", va="top", fontsize=8)
            ax.set_yscale("log")
        ax.set_title(f"{'S1' if key[0] == 1 else 'S2'} {key[1].split(':')[0]}", fontsize=9)
        ax.set_ylabel("seconds")
        ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(args.out / "fig_windows.png", dpi=200)
    plt.close(fig)
    print(f"wrote comparison.csv, comparison.md, fig_stage_comparison.png, fig_windows.png to {args.out}")


if __name__ == "__main__":
    main()
