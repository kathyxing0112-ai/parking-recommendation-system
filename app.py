"""Entry point for the Cornell Smart Parking walking skeleton.

Plays the Cornell Driver (X.C.1) through UC.1 Find Suitable Parking, one
message at a time, in the order of the updated UC.1 sequence diagram
(docs/walking-skeleton.md). Parking availability comes from the simulated
X.C.2 feed through the data access component, and the message is interpreted
by the local Qwen3 model through its adapter; if the model is not running or
its output violates the Model Response Contract, the driver fills in the
six-field form instead. A1 filters the areas and A3 ranks them by walking time,
because A2 has no forecast yet.
"""

from datetime import datetime, timedelta

import cornell_driver_interface as driver_interface


def show(step: str, payload) -> None:
    print(f"\n[{step}]")
    print(payload)


def main() -> None:
    message = ("I need to park near Duffield Hall in 30 minutes and stay two hours. "
               "I drive a sedan, have an O permit, and don't need an accessible space.")

    interpreted = driver_interface.submit_trip_request(message)
    show("UC.1.1 Submit Trip Request -> UC.1.2 Interpret and Confirm Trip Request", interpreted)

    if interpreted["status"] == "complete":
        # The driver confirms the interpreted six-field request unchanged.
        confirmed = interpreted["trip_request"]
    else:
        # The six-field form: the driver types the values in directly.
        now = datetime.now().astimezone().replace(microsecond=0)
        confirmed = {
            "destination": "Duffield Hall",
            "arrival_time": (now + timedelta(minutes=30)).isoformat(),
            "departure_time": (now + timedelta(minutes=150)).isoformat(),
            "vehicle_category": "sedan",
            "declared_eligibility": "permit_O",
            "access_needs": False,
        }
        show("Six-field form completed by the driver", confirmed)
    recommendations = driver_interface.confirm_trip_requirements(confirmed)
    show("UC.1.3 Confirm Trip Requirements -> UC.1.4-UC.1.9 -> UC.1.14 Present Ranked Parking Recommendations",
         recommendations["ranked_options"])

    if not recommendations["ranked_options"]:
        return  # SR-13: no confirmed eligible option is available for this trip.

    selected = driver_interface.select_parking_option(
        recommendations, recommendations["ranked_options"][0]["lot_id"])
    show("UC.1.16 Select Parking Option -> UC.1.17 Present Selected Parking Information", selected)

    status = driver_interface.request_pre_arrival_recheck(selected["lot_id"])
    show("UC.1.18 Request Pre-Arrival Status Recheck -> UC.1.19/UC.1.20 -> UC.1.21 Present Updated Parking Status",
         {"lot_id": status["lot_id"], "data_mode": status["data_mode"],
          "space_observations": len(status["observations"]),
          "observed_at": max((o["timestamp"] for o in status["observations"]), default=None)})


if __name__ == "__main__":
    main()
