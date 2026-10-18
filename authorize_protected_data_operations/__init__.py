"""A5 -- Authorize Protected Data Operations.

Implements first-level IDEF0 function A5 of A0 Provide Parking Decision
Support (source: SYS.1).

Mechanism: C.0 Cornell Smart Parking Availability & Recommendation System
(the system itself), so no dependency is injected.

Signature from the ICOMs in Chapter 4; body added in Chapter 5.
"""


def authorize_protected_data_operations(
    protected_data_operation_request: dict,
    *,
    approved_role_permission_matrix: dict,
) -> dict:
    """in: protected_data_operation_request (A1, A4, A6).
    control: approved_role_permission_matrix.
    out: authorization_decision (A1, A4, A6).
    """
    role = protected_data_operation_request["role"]
    operation = protected_data_operation_request["operation"]
    scope = approved_role_permission_matrix.get(role, {}).get(operation)
    if scope == "any":
        return {"permitted": True}
    if scope == "own_session":
        caller_session_id = protected_data_operation_request.get("caller_session_id")
        record_session_id = protected_data_operation_request.get("record_session_id")
        return {
            "permitted": caller_session_id is not None
            and caller_session_id == record_session_id
        }
    return {"permitted": False}
