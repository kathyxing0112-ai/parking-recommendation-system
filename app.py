"""Entry point for the Cornell Smart Parking walking skeleton.

Runs one Cornell Driver action end to end through every participant listed in
docs/walking-skeleton.md and prints the stubbed response.
"""

from cornell_driver_interface import submit_trip_request


def main() -> None:
    trip_request = {
        "destination": "Duffield Hall",
        "arrival_time": "2026-10-01T10:00:00",
        "departure_time": "2026-10-01T12:00:00",
        "vehicle_type": "standard",
        "group_size": 1,
        "parking_eligibility": "student",
    }
    print(submit_trip_request(trip_request))


if __name__ == "__main__":
    main()
