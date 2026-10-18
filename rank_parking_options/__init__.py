"""A3 -- Rank Parking Options.

Implements first-level IDEF0 function A3 of A0 Provide Parking Decision
Support.

Mechanism: C.0 Cornell Smart Parking Availability & Recommendation System
(the system itself), so no dependency is injected.

Signature from the ICOMs in Chapter 4; body added in Chapter 5.
"""

from decimal import ROUND_HALF_UP, Decimal

_SIX_DECIMALS = Decimal("0.000001")
_MAX_OPTIONS = 2


def rank_parking_options(
    normalized_trip_requirements: dict,
    validated_context_information: list[dict],
    eligible_parking_areas: list[dict],
    data_quality_and_freshness_status: dict,
    arrival_time_availability_estimates: list[dict],
    forecast_validity_status: dict,
    *,
    ranking_and_fallback_rules: dict,
) -> list[dict]:
    """in: normalized_trip_requirements (A1),
    validated_context_information (A1), eligible_parking_areas (A1),
    data_quality_and_freshness_status (A1),
    arrival_time_availability_estimates (A2), forecast_validity_status (A2).
    control: ranking_and_fallback_rules.
    out: ranked_parking_options (A4).
    """
    walking = {
        item["lot_id"]: item["walking_time_minutes"]
        for item in validated_context_information
    }
    estimates = {item["lot_id"]: item for item in arrival_time_availability_estimates}
    candidates = [area["lot_id"] for area in eligible_parking_areas]
    if not candidates:
        return []

    if all(
        forecast_validity_status.get(lot_id) == "supported"
        and _is_valid_estimate(estimates.get(lot_id))
        for lot_id in candidates
    ):
        weights = ranking_and_fallback_rules["weights"]
        w_min = min(walking[lot_id] for lot_id in candidates)
        w_max = max(walking[lot_id] for lot_id in candidates)
        options = []
        for lot_id in candidates:
            e = estimates[lot_id]
            w = walking[lot_id]
            capacity = Decimal(str(e["capacity"]))
            walk_score = (
                Decimal(1)
                if w_max == w_min
                else Decimal(str(w_max - w)) / Decimal(str(w_max - w_min))
            )
            availability = Decimal(str(e["available_spaces"])) / capacity
            certainty = 1 - (
                Decimal(str(e["interval_upper"])) - Decimal(str(e["interval_lower"]))
            ) / capacity
            score = (
                Decimal(str(weights["walking_time"])) * walk_score
                + Decimal(str(weights["availability"])) * availability
                + Decimal(str(weights["uncertainty"])) * certainty
            ).quantize(_SIX_DECIMALS, rounding=ROUND_HALF_UP)
            options.append(
                {
                    "lot_id": lot_id,
                    "walking_time_minutes": w,
                    "score": float(score),
                    "ranking_basis": "score",
                }
            )
        options.sort(
            key=lambda o: (-o["score"], o["walking_time_minutes"], o["lot_id"])
        )
    else:
        options = sorted(
            (
                {
                    "lot_id": lot_id,
                    "walking_time_minutes": walking[lot_id],
                    "score": None,
                    "ranking_basis": "fallback_walking_time",
                }
                for lot_id in candidates
            ),
            key=lambda o: (o["walking_time_minutes"], o["lot_id"]),
        )
    return options[:_MAX_OPTIONS]


def _is_valid_estimate(estimate: dict | None) -> bool:
    """SR-13 input constraints: C > 0, 0 <= F <= C, 0 <= L <= U <= C."""
    if estimate is None:
        return False
    try:
        c = estimate["capacity"]
        f = estimate["available_spaces"]
        lower = estimate["interval_lower"]
        upper = estimate["interval_upper"]
        return c > 0 and 0 <= f <= c and 0 <= lower <= upper <= c
    except (KeyError, TypeError):
        return False
