"""Build the simulated 15-minute lot occupancy series for forecasting (SPEC Data Contract section 2).

Runs the seeded X.C.2 simulator over the 15 simulated weeks (Monday
2026-08-24 to Sunday 2026-12-06, local time) and writes one row per lot
and 15-minute as_of_timestamp, with the occupancy observed at that time and
the context known for that date. Forecast features that look back in time
(lags, rolling means) and labels at each lead time are built from this
series by the forecasting code, so they never use later rows.

occupied is counted from the simulated per-space sensor events, so the
series agrees with what the live feed reports at the same time. All values
are simulated, not observed Cornell data.

Split by simulated week: 1-10 train, 11-12 validation, 13-15 holdout. The
holdout weeks are kept for the single final SR-14 evaluation.

Usage:
  python scripts/build_modeling_table.py [--out data/simulated/occupancy_15min.csv]
"""

import argparse
import csv
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import contextual_information_sources as context  # noqa: E402
import parking_availability_data_sources as source  # noqa: E402

LOCAL = source.LOCAL_TIME
FIRST_DAY = datetime(2026, 8, 24, tzinfo=LOCAL)
END = datetime(2026, 12, 7, tzinfo=LOCAL)   # exclusive: the series ends Sunday 2026-12-06 23:45
STEP = timedelta(minutes=15)
SPLITS = {range(1, 11): "train", range(11, 13): "validation", range(13, 16): "holdout"}
COLUMNS = ["lot_id", "as_of_timestamp", "sim_week", "split", "occupied", "capacity", "occupancy_rate",
           "day_of_week", "time_of_day", "is_class_day", "is_break", "is_weekend", "event_flag",
           "temp_c", "precipitation_probability", "snow_flag"]


def split_for(week: int) -> str:
    return next(name for weeks, name in SPLITS.items() if week in weeks)


def build_rows():
    lots = source.get_lot_inventory()
    capacity = {lot["lot_id"]: sum(lot["capacity_by_zone"].values()) for lot in lots}
    lot_ids = list(capacity)
    # Step in UTC so the repeated hour when daylight saving time ends is kept, not skipped.
    at = FIRST_DAY.astimezone(timezone.utc)
    while at < END:
        local = at.astimezone(LOCAL)
        day = local.date()
        week = (day - FIRST_DAY.date()).days // 7 + 1
        calendar = context.get_calendar_day(day)
        weather = context.get_weather_forecast(day)
        events = context.get_events(day)
        occupied = Counter(event["lot_id"] for event in source.get_current_parking_availability(lot_ids, local)
                           if event["status"] == "occupied")
        for lot_id in lot_ids:
            in_event = any(lot_id in e["lot_ids"] and e["start_hour"] <= local.hour < e["end_hour"] for e in events)
            yield {
                "lot_id": lot_id,
                "as_of_timestamp": local.isoformat(),
                "sim_week": week,
                "split": split_for(week),
                "occupied": occupied[lot_id],
                "capacity": capacity[lot_id],
                "occupancy_rate": round(occupied[lot_id] / capacity[lot_id], 4),
                "day_of_week": local.weekday(),          # 0 = Monday
                "time_of_day": local.strftime("%H:%M"),
                "is_class_day": int(calendar["is_class_day"]),
                "is_break": int(calendar["is_break"]),
                "is_weekend": int(calendar["is_weekend"]),
                "event_flag": int(in_event),
                "temp_c": weather["temp_c"],
                "precipitation_probability": weather["precipitation_probability"],
                "snow_flag": int(weather["snow_flag"]),
            }
        at += STEP


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("data/simulated/occupancy_15min.csv"))
    args = parser.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.out.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        for row in build_rows():
            writer.writerow(row)
            count += 1
    print(f"wrote {count} rows to {args.out}")


if __name__ == "__main__":
    main()
