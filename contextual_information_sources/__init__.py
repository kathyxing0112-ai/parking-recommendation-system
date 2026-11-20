"""Contextual Information Sources (X.C.3).

Walking-skeleton participant for UC.1.6 Request / UC.1.7 Provide Context
Information. Walking times come from walking_times.csv: one row per building
and pilot lot, in whole minutes, with the source, the date checked and who
checked it. The buildings in the file are also the supported destinations.

The same source also gives the forecast context: the fall 2026 academic
calendar (Registrar dates), a draft list of major campus events, and a
seeded simulated daily weather forecast.
"""

import csv
import random
from datetime import date
from functools import lru_cache
from pathlib import Path

WALKING_TIMES_PATH = Path(__file__).with_name("walking_times.csv")
CALENDAR_PATH = Path(__file__).with_name("academic_calendar_fall2026.csv")
EVENTS_PATH = Path(__file__).with_name("campus_events_fall2026.csv")

WEATHER_SEED = 5151
# Simulated weather assumptions: daily mean temperature falls linearly from
# late August to early December (Ithaca-like, not observed data).
WEATHER_FIRST_DAY, WEATHER_FIRST_TEMP_C = date(2026, 8, 24), 21.0
WEATHER_LAST_DAY, WEATHER_LAST_TEMP_C = date(2026, 12, 6), 1.0


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


@lru_cache(maxsize=1)
def _no_class_days() -> frozenset:
    with CALENDAR_PATH.open(newline="", encoding="utf-8") as file:
        return frozenset(date.fromisoformat(row["date"]) for row in csv.DictReader(file)
                         if row["day_type"] == "no_classes")


def get_calendar_day(day: date) -> dict:
    """Calendar context for one local date, from the Registrar fall 2026 dates.

    is_class_day is true on a weekday that is not a listed no-class day.
    is_break is true on a weekday listed as a no-class day (holiday or break).
    """
    is_weekend = day.weekday() >= 5
    is_break = not is_weekend and day in _no_class_days()
    return {"is_class_day": not is_weekend and not is_break, "is_break": is_break, "is_weekend": is_weekend}


@lru_cache(maxsize=1)
def _event_rows() -> tuple:
    with EVENTS_PATH.open(newline="", encoding="utf-8") as file:
        return tuple(
            {"date": date.fromisoformat(row["date"]), "start_hour": int(row["start_hour"]),
             "end_hour": int(row["end_hour"]), "lot_ids": tuple(row["lot_ids"].split(";")),
             "occupancy_increase": float(row["occupancy_increase"]), "name": row["name"]}
            for row in csv.DictReader(file))


def get_events(day: date) -> list[dict]:
    """Major campus events on one local date (simulated draft list, maintained by the team)."""
    return [dict(event) for event in _event_rows() if event["date"] == day]


def get_weather_forecast(day: date) -> dict:
    """Simulated daily weather forecast: mean temperature and chance of precipitation.

    The same seed and date always give the same forecast. snow_flag marks a
    day cold enough that any precipitation falls as snow.
    """
    rng = random.Random(f"{WEATHER_SEED}|weather|{day.isoformat()}")
    span = (WEATHER_LAST_DAY - WEATHER_FIRST_DAY).days
    progress = min(max((day - WEATHER_FIRST_DAY).days / span, 0.0), 1.0)
    temp_c = WEATHER_FIRST_TEMP_C + (WEATHER_LAST_TEMP_C - WEATHER_FIRST_TEMP_C) * progress + rng.gauss(0, 3)
    precipitation_probability = round(min(rng.betavariate(0.7, 1.1), 1.0), 1)
    return {"temp_c": round(temp_c, 1), "precipitation_probability": precipitation_probability,
            "snow_flag": temp_c <= 0.0}
