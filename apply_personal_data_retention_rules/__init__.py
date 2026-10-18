"""A6 -- Apply Personal Data Retention Rules.

Implements first-level IDEF0 function A6 of A0 Provide Parking Decision
Support (source: SYS.2).

Mechanism: C.0 Cornell Smart Parking Availability & Recommendation System
(the system itself), so no dependency is injected.

Signature from the ICOMs in Chapter 4; body added in Chapter 5.
"""

from datetime import datetime, timedelta, timezone


def apply_personal_data_retention_rules(
    personal_records_and_retention_metadata: list[dict],
    *,
    authorization_decision: dict,
    approved_data_retention_schedule: dict,
) -> dict:
    """in: personal_records_and_retention_metadata (A1).
    control: authorization_decision (A5), approved_data_retention_schedule.
    out: protected_data_operation_request (A5),
    personal_record_disposition_result (A1, A4).
    """
    now = datetime.now(timezone.utc)  # C.0 system clock
    retention = timedelta(hours=approved_data_retention_schedule["retention_hours"])
    expired_record_ids = [
        record["record_id"]
        for record in personal_records_and_retention_metadata
        if now >= datetime.fromisoformat(record["submitted_at"]) + retention
    ]
    protected_data_operation_request = {
        "role": "retention_service",
        "operation": "delete_expired_trip_record",
        "record_ids": expired_record_ids,
    }
    deleted = expired_record_ids if authorization_decision["permitted"] else []
    return {
        "protected_data_operation_request": protected_data_operation_request,
        "personal_record_disposition_result": {"deleted": deleted},
    }
