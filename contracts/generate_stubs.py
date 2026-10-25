"""Generate signature-only stubs from contracts/api-v1.yaml.

Run from the repository root:

    python contracts/generate_stubs.py

Writes one module per operation to contracts/generated/. Request properties
marked x-icom input become positional parameters and x-icom control become
keyword-only parameters, in contract order; the 200 response becomes the
return annotation. Never edit the generated files by hand.
"""

from pathlib import Path

import yaml

CONTRACT = Path(__file__).with_name("api-v1.yaml")
OUT_DIR = Path(__file__).with_name("generated")


def _resolve(schema: dict, contract: dict) -> dict:
    while "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        schema = contract["components"]["schemas"][name]
    return schema


def _annotation(schema: dict, contract: dict) -> str:
    kind = _resolve(schema, contract).get("type")
    return {"array": "list[dict]", "object": "dict", "string": "str"}[kind]


def operations(contract: dict):
    """Yield (module, function, operation_id, summary, inputs, controls, returns)."""
    for path in contract["paths"].values():
        op = path["post"]
        module, function = op["x-function"].split(".")
        props = op["requestBody"]["content"]["application/json"]["schema"]["properties"]
        inputs = [(n, _annotation(s, contract)) for n, s in props.items() if s["x-icom"] == "input"]
        controls = [(n, _annotation(s, contract)) for n, s in props.items() if s["x-icom"] == "control"]
        response = op["responses"]["200"]["content"]["application/json"]["schema"]
        yield module, function, op["operationId"], op["summary"], inputs, controls, _annotation(response, contract)


def render(function, operation_id, summary, inputs, controls, returns) -> str:
    params = [f"    {n}: {a}," for n, a in inputs]
    if controls:
        params.append("    *,")
        params += [f"    {n}: {a}," for n, a in controls]
    return (
        f'"""GENERATED from contracts/api-v1.yaml -- do not hand-edit.\n'
        f'Regenerate after changing the contract, never the other way around."""\n'
        f"\n\n"
        f"def {function}(\n" + "\n".join(params) + f"\n) -> {returns}:\n"
        f'    """operationId: {operation_id}. {summary}."""\n'
        f"    raise NotImplementedError\n"
    )


def main() -> None:
    contract = yaml.safe_load(CONTRACT.read_text())
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "__init__.py").write_text('"""GENERATED stubs from contracts/api-v1.yaml."""\n')
    for module, function, *rest in operations(contract):
        (OUT_DIR / f"{module}_stub.py").write_text(render(function, *rest))


if __name__ == "__main__":
    main()
