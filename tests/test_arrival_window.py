"""SR-12 arrival window in the product: 0-72 hours after submission, inclusive.

The adapter (language_model) and A1.1 (interpret_and_confirm_parking_requests)
must use the same window, and A1.1 must apply it with the product's own rules.
Lead times from SR-12's verification criteria: 0 min, 60 min, 24 h, 72 h,
and 72 h 1 min.
"""

from datetime import datetime, timedelta

import pytest

import language_model
import smart_parking_service
from prepare_eligible_parking_information.interpret_and_confirm_parking_requests import (
    InvalidTripRequest,
    interpret_and_confirm_parking_requests,
)

SUBMITTED = datetime.fromisoformat("2026-11-20T10:30:00-05:00")
RULES = {**smart_parking_service.TRIP_REQUEST_VALIDATION_RULES}
RULES.pop("supported_values")


def confirm(arrival):
    trip = {
        "destination": "Upson Hall",
        "arrival_time": arrival.isoformat(),
        "departure_time": (arrival + timedelta(hours=2)).isoformat(),
        "vehicle_category": "sedan",
        "declared_eligibility": "permit_O",
        "access_needs": False,
    }
    return interpret_and_confirm_parking_requests(
        {"message": "", "submitted_at": SUBMITTED.isoformat()}, trip, trip_request_validation_rules=RULES)


def test_adapter_and_a11_use_the_same_72_hour_window():
    assert language_model.ARRIVAL_WINDOW == timedelta(hours=72)
    assert timedelta(minutes=RULES["arrival_window_minutes"]) == language_model.ARRIVAL_WINDOW


@pytest.mark.parametrize("lead", [timedelta(0), timedelta(minutes=60), timedelta(hours=24), timedelta(hours=72)],
                         ids=["0-min", "60-min", "24-h", "72-h"])
def test_a11_accepts_arrivals_up_to_72_hours(lead):
    assert "normalized_trip_requirements" in confirm(SUBMITTED + lead)


@pytest.mark.parametrize("lead", [timedelta(hours=72, minutes=1), timedelta(minutes=-1)],
                         ids=["72-h-1-min", "before-submission"])
def test_a11_rejects_arrivals_outside_the_window(lead):
    with pytest.raises(InvalidTripRequest):
        confirm(SUBMITTED + lead)
