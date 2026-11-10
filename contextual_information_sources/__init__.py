"""Contextual Information Sources (X.C.3).

Walking-skeleton participant for UC.1.6 Request / UC.1.7 Provide Context
Information. Walking times come from walking_times.csv: one row per building
and pilot lot, in whole minutes, with the source, the date checked and who
checked it. The buildings in the file are also the supported destinations.
"""

import csv
from pathlib import Path

WALKING_TIMES_PATH = Path(__file__).with_name("walking_times.csv")


def _walking_time_rows() -> list[dict]:
    with WALKING_TIMES_PATH.open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def get_destinations() -> list[str]:
    """The buildings that have walking times, in file order."""
    return list(dict.fromkeys(row["destination"] for row in _walking_time_rows()))


def get_contextual_information(destination: str) -> list:
    """Walking time from each pilot lot to the destination; empty for an unknown building."""
    return [
        {"lot_id": row["lot_id"], "walking_time_minutes": int(row["walking_time_minutes"])}
        for row in _walking_time_rows()
        if row["destination"] == destination
    ]
