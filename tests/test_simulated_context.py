"""Forecast context (X.C.3) and the simulated occupancy it drives (X.C.2).

Checks the fall 2026 calendar days, the event list, the seeded weather
forecast, the effect of each on simulated occupancy, and the modeling-table
split by simulated week.
"""

import itertools
from datetime import date, datetime

import contextual_information_sources as context
import parking_availability_data_sources as source
from scripts.build_modeling_table import COLUMNS, build_rows, split_for

LOCAL = source.LOCAL_TIME


def occupied(lot_id: str, at: datetime) -> int:
    return sum(e["status"] == "occupied" for e in source.get_current_parking_availability([lot_id], at))


def test_calendar_marks_class_days_breaks_and_weekends():
    assert context.get_calendar_day(date(2026, 9, 8)) == {"is_class_day": True, "is_break": False, "is_weekend": False}
    assert context.get_calendar_day(date(2026, 9, 7))["is_break"]          # Labor Day
    assert context.get_calendar_day(date(2026, 10, 13))["is_break"]        # fall break, Tuesday
    assert context.get_calendar_day(date(2026, 11, 27))["is_break"]        # Thanksgiving break, Friday
    weekend = context.get_calendar_day(date(2026, 10, 10))                  # fall break, but a Saturday
    assert weekend["is_weekend"] and not weekend["is_break"] and not weekend["is_class_day"]


def test_events_are_listed_by_date():
    [homecoming] = context.get_events(date(2026, 10, 17))
    assert homecoming["lot_ids"] == ("LOT-1", "LOT-2", "LOT-3")
    assert context.get_events(date(2026, 10, 18)) == []


def test_weather_forecast_is_seeded_and_in_range():
    day = date(2026, 10, 1)
    forecast = context.get_weather_forecast(day)
    assert forecast == context.get_weather_forecast(day)
    assert 0.0 <= forecast["precipitation_probability"] <= 1.0
    assert set(forecast) == {"temp_c", "precipitation_probability", "snow_flag"}


def test_no_class_weekday_is_emptier_than_a_class_day():
    labor_day = datetime(2026, 9, 7, 11, 0, tzinfo=LOCAL)
    next_monday = datetime(2026, 9, 14, 11, 0, tzinfo=LOCAL)
    assert occupied("LOT-1", labor_day) < 0.75 * occupied("LOT-1", next_monday)


def test_event_fills_the_lot_it_affects():
    homecoming = datetime(2026, 10, 17, 13, 0, tzinfo=LOCAL)
    next_saturday = datetime(2026, 10, 24, 13, 0, tzinfo=LOCAL)
    assert occupied("LOT-3", homecoming) > occupied("LOT-3", next_saturday) + 30


def test_drift_does_not_depend_on_the_order_of_requests():
    early = datetime(2026, 9, 1, 9, 0, tzinfo=LOCAL)
    late = datetime(2026, 10, 1, 9, 0, tzinfo=LOCAL)
    source._drift_paths.clear()
    in_order = source._drift("LOT-2", early), source._drift("LOT-2", late)
    source._drift_paths.clear()
    late_first = source._drift("LOT-2", late)
    assert (source._drift("LOT-2", early), late_first) == in_order
    assert source._drift("LOT-2", datetime(2026, 8, 1, tzinfo=LOCAL)) == 0.0


def test_modeling_table_rows_and_split():
    rows = list(itertools.islice(build_rows(), 3))
    assert [row["lot_id"] for row in rows] == ["LOT-1", "LOT-2", "LOT-3"]
    assert all(list(row) == COLUMNS for row in rows)
    assert rows[0]["as_of_timestamp"] == "2026-08-24T00:00:00-04:00"
    assert 0 <= rows[0]["occupied"] <= rows[0]["capacity"]
    assert [split_for(w) for w in (1, 10, 11, 12, 13, 15)] == [
        "train", "train", "validation", "validation", "holdout", "holdout"]
