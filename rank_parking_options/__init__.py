"""A3 -- Rank Parking Options.

Implements first-level IDEF0 function A3 of A0 Provide Parking Decision
Support.

Mechanism: C.0 Cornell Smart Parking Availability & Recommendation System
(the system itself), so no dependency is injected.

Signature from the ICOMs only; the body arrives in Chapter 5.
"""


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
    raise NotImplementedError
