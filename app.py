"""Entry point for the Cornell Smart Parking walking skeleton.

Plays the Cornell Driver (X.C.1) through UC.1 Find Suitable Parking, one
message at a time, in the order of the updated UC.1 sequence diagram
(docs/walking-skeleton.md). Every participant is a stub returning synthetic,
hard-coded values.
"""

import cornell_driver_interface as driver_interface


def show(step: str, payload) -> None:
    print(f"\n[{step}]")
    print(payload)


def main() -> None:
    message = "I need to park near Duffield Hall from 10 to 12 tomorrow with my O permit."

    interpreted = driver_interface.submit_trip_request(message)
    show("UC.1.1 Submit Trip Request -> UC.1.2 Interpret and Confirm Trip Request", interpreted)

    # The driver confirms the interpreted six-field request unchanged.
    confirmed = interpreted["trip_request"]
    recommendations = driver_interface.confirm_trip_requirements(confirmed)
    show("UC.1.3 Confirm Trip Requirements -> UC.1.4-UC.1.9 -> UC.1.14 Present Ranked Parking Recommendations",
         recommendations["ranked_options"])

    selected = driver_interface.select_parking_option(recommendations, "LOT-1")
    show("UC.1.16 Select Parking Option -> UC.1.17 Present Selected Parking Information", selected)

    status = driver_interface.request_pre_arrival_recheck(selected["lot_id"])
    show("UC.1.18 Request Pre-Arrival Status Recheck -> UC.1.19/UC.1.20 -> UC.1.21 Present Updated Parking Status",
         status)


if __name__ == "__main__":
    main()
