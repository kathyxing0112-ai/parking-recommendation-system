"""Stage timing for Lab Manual §10.4 (instrumentation and measured behavior).

Not a subsystem: this package performs no IDEF0 function and has no asset in
the model. It records how long each participant in the UC.1 sequence diagram
holds the request, so the measured durations can be set against the
Innoslate simulation.

Timing is off unless a caller turns it on with start(). While it is off,
stage() does nothing but yield, so the product and the test suite behave
exactly as before. Recording is per thread, so a measurement run is not mixed
with requests the web app serves on other threads.

Only stage names and times are recorded. Driver messages, trip fields and
model output are never recorded (SR-04).

Stage names are listed in STAGES. Each name starts with the asset or external
system whose boundary it measures, so it can be mapped to the action numbers
(s1.x / s2.x) in the Innoslate action diagrams once those are fixed
(docs/measured-behavior.md).
"""

import threading
import time
from contextlib import contextmanager

# stage name -> (participant, what the stage covers)
STAGES = {
    "UC1.interpret_request": ("X.C.1 -> C.0", "Driver submits a message until the interpreted request comes back (UC.1.1-UC.1.2)"),
    "C.1.1.model_call": ("C.1.1 -> Ollama qwen3:4b", "One chat request to the local model and its reply"),
    "C.1.1.contract_check": ("C.1.1", "Adapter checks the reply against the Model Response Contract"),
    "UC1.find_parking": ("X.C.1 -> C.0", "Driver confirms the request until ranked options come back (UC.1.3-UC.1.14)"),
    "X.C.2.availability": ("C.0 -> X.C.2 (SQLite data store)", "Read simulated availability through the data access component"),
    "X.C.3.context": ("C.0 -> X.C.3", "Read contextual information (walking times)"),
    "X.C.4.rules": ("C.0 -> X.C.4", "Read parking rules and closures"),
    "C.1.prepare": ("C.1", "A1 Prepare Eligible Parking Information, all four modules"),
    "C.1.1.confirm": ("C.1.1", "A1.1 checks the confirmed request"),
    "C.1.2.requests": ("C.1.2", "A1.2 builds the availability, context and policy requests"),
    "C.1.3.validate": ("C.1.3", "A1.3 validates parking and context data"),
    "C.1.4.eligibility": ("C.1.4", "A1.4 determines eligible parking areas"),
    "C.3.rank": ("C.3", "A3 ranks the eligible options"),
    "C.0.assemble_result": ("C.0 (stands in for C.4)", "Builds the driver-facing result; A4 has no body yet"),
    # Measured by the client in scripts/measure_uc1.py --http, not with stage():
    "HTTP.interpret_round_trip": ("X.C.1 browser -> web_app (loopback HTTP)", "POST /api/interpret, request sent until the JSON reply is read"),
    "HTTP.confirm_round_trip": ("X.C.1 browser -> web_app (loopback HTTP)", "POST /api/confirm, request sent until the JSON reply is read (SR-13 window without page rendering)"),
}

_local = threading.local()


def start() -> None:
    """Start recording stages on this thread. Clears anything recorded before."""
    _local.records = []
    _local.stack = []


def stop() -> list[dict]:
    """Stop recording on this thread and return the records, in exit order."""
    records = getattr(_local, "records", None) or []
    _local.records = None
    _local.stack = []
    return records


def is_recording() -> bool:
    return getattr(_local, "records", None) is not None


@contextmanager
def stage(name: str):
    """Record entry and exit of one stage while recording is on.

    Each record: stage, parent (the enclosing stage or None), entry_ns,
    exit_ns (time.perf_counter_ns) and duration_ms. The exit is recorded even
    if the stage raises, so a failure path still shows how long it took.
    """
    records = getattr(_local, "records", None)
    if records is None:
        yield
        return
    if name not in STAGES:
        raise ValueError(f"unknown stage {name!r}; add it to stage_timing.STAGES")
    parent = _local.stack[-1] if _local.stack else None
    _local.stack.append(name)
    entry = time.perf_counter_ns()
    try:
        yield
    finally:
        exit_ = time.perf_counter_ns()
        _local.stack.pop()
        records.append({
            "stage": name,
            "parent": parent,
            "entry_ns": entry,
            "exit_ns": exit_,
            "duration_ms": (exit_ - entry) / 1e6,
        })
