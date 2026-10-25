"""GENERATED from contracts/api-v1.yaml -- do not hand-edit.
Regenerate after changing the contract, never the other way around."""


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
    """operationId: rankParkingOptions. A1, A2 -> A3 (FR 1.4.3), flows 9.6, 9.7, 9.9-9.12."""
    raise NotImplementedError
