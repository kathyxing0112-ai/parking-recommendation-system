"""Chapter 7 conformance suite for contracts/api-v1.yaml.

The contract is the authority on what crosses a first-level function
boundary. These tests check that the generated stubs are current with the
contract and that each A1-A6 module has exactly the stub's signature, and that
the implemented functions (A3, A5, A6) return the properties the contract
requires.
"""

import importlib
import inspect
from pathlib import Path

import pytest
import yaml

from contracts import generate_stubs

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = yaml.safe_load((ROOT / "contracts" / "api-v1.yaml").read_text())
OPERATIONS = list(generate_stubs.operations(CONTRACT))


def _required(operation_id: str) -> list[str]:
    for path in CONTRACT["paths"].values():
        op = path["post"]
        if op["operationId"] == operation_id:
            schema = op["responses"]["200"]["content"]["application/json"]["schema"]
            return generate_stubs._resolve(schema, CONTRACT).get("required", [])
    raise KeyError(operation_id)


@pytest.mark.parametrize("module, function, operation_id, summary, inputs, controls, returns",
                         OPERATIONS, ids=[op[2] for op in OPERATIONS])
def test_generated_stub_is_current(module, function, operation_id, summary, inputs, controls, returns):
    stub = ROOT / "contracts" / "generated" / f"{module}_stub.py"
    assert stub.read_text() == generate_stubs.render(function, operation_id, summary, inputs, controls, returns)


@pytest.mark.parametrize("module, function, operation_id, summary, inputs, controls, returns",
                         OPERATIONS, ids=[op[2] for op in OPERATIONS])
def test_module_signature_matches_contract(module, function, operation_id, summary, inputs, controls, returns):
    stub = getattr(importlib.import_module(f"contracts.generated.{module}_stub"), function)
    implementation = getattr(importlib.import_module(module), function)
    assert inspect.signature(implementation) == inspect.signature(stub)


def test_rank_parking_options_returns_contract_items():
    from rank_parking_options import rank_parking_options

    options = rank_parking_options(
        {}, [{"lot_id": "LOT-1", "walking_time_minutes": 5}], [{"lot_id": "LOT-1"}],
        {"LOT-1": "current"}, [], {"LOT-1": "unsupported"},
        ranking_and_fallback_rules={"weights": {"walking_time": 0.4, "availability": 0.4, "uncertainty": 0.2}},
    )
    item_schema = generate_stubs._resolve(
        CONTRACT["components"]["schemas"]["RankedParkingOptions"]["items"], CONTRACT)
    assert options
    for option in options:
        assert set(item_schema["required"]) <= set(option)
        assert option["ranking_basis"] in item_schema["properties"]["ranking_basis"]["enum"]


def test_authorize_protected_data_operations_returns_contract_properties():
    from authorize_protected_data_operations import authorize_protected_data_operations

    decision = authorize_protected_data_operations(
        {"role": "retention_service", "operation": "delete_expired_trip_record"},
        approved_role_permission_matrix={"retention_service": {"delete_expired_trip_record": "any"}},
    )
    assert set(_required("authorizeProtectedDataOperations")) <= set(decision)


def test_apply_personal_data_retention_rules_returns_contract_properties():
    from apply_personal_data_retention_rules import apply_personal_data_retention_rules

    result = apply_personal_data_retention_rules(
        [], authorization_decision={"permitted": True},
        approved_data_retention_schedule={"retention_hours": 24},
    )
    assert set(_required("applyPersonalDataRetentionRules")) <= set(result)
    request = result["protected_data_operation_request"]
    assert {"role", "operation"} <= set(request)
