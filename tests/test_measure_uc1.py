"""scripts/measure_uc1.py --http: the form path through web_app's POST /api/confirm.

Scenario 2 calls no model, so this needs no running Ollama. It checks that the
client round trip is recorded and that the server-side stages arrive with it,
nested under the round trip and inside its time.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import measure_uc1  # noqa: E402

REQUEST = {
    "id": "T01",
    "message_template": "Duffield Hall at {arrive} until {leave}, sedan, O permit, no accessible space",
    "form": {"destination": "Duffield Hall", "arrive_in_minutes": 20, "stay_minutes": 120,
             "vehicle_category": "sedan", "declared_eligibility": "permit_O", "access_needs": False},
}


def test_http_form_run_records_round_trip_and_server_stages():
    http = measure_uc1.HttpProduct()
    try:
        run, records = measure_uc1.one_run(2, REQUEST, http)
    finally:
        http.close()

    assert run["ranked_options"] == 2
    by_stage = {r["stage"]: r for r in records}
    trip = by_stage["HTTP.confirm_round_trip"]
    assert trip["parent"] is None
    assert by_stage["UC1.find_parking"]["parent"] == "HTTP.confirm_round_trip"
    assert {"X.C.2.availability", "C.1.4.eligibility", "C.3.rank"} <= set(by_stage)
    server = by_stage["UC1.find_parking"]
    assert trip["entry_ns"] <= server["entry_ns"] <= server["exit_ns"] <= trip["exit_ns"]
    assert run["system_total_ms"] == round(trip["duration_ms"], 3)
