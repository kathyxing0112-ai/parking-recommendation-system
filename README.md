# Cornell Smart Parking Availability and Recommendation System

## Operational Concept

The Operational Concept describes a typical parking-recommendation scenario. A Cornell driver enters the destination, expected arrival and departure times, vehicle category, declared parking eligibility, and whether accessible parking is needed. The system obtains current parking availability, contextual information, and applicable parking policy constraints from external sources.

The system uses these inputs to evaluate eligible parking options, estimate their availability, and rank the most suitable alternatives. It then provides the recommended locations, expected availability, and supporting information to the driver. The driver reviews the results and chooses an option based on the trip needs.

The system provides decision support only. It does not reserve parking spaces or control physical parking operations.

## Running the Application

```bash
python app.py
```

At this increment, the command walks the Cornell Driver through UC.1 Find
Suitable Parking, following the updated UC.1 sequence diagram: submitting and
confirming a trip request, receiving ranked primary and backup recommendations,
selecting an option, and requesting a pre-arrival status recheck. Each step is
printed with its UC.1 message identifier. Parking availability comes from a
seeded, simulated sensor feed through the data access component, and the
driver's message is interpreted by the local Qwen3 4B model through its
adapter (`docs/deployment.md`). The ranking and the X.C.3/X.C.4 sources are
still hard-coded stubs; see `docs/walking-skeleton.md` for the
message-to-code mapping.

To use the language model, install [Ollama](https://ollama.com) and run:

```bash
ollama pull qwen3:4b
```

Without a running model, the app falls back to the six-field form, as
`SPEC.md` specifies.

## Running the Acceptance Tests

```bash
python -m pytest tests/ -v
```

`tests/test_spec_acceptance.py` contains 19 acceptance-test placeholders, one
for each need-to-requirement trace in `SPEC.md`. They fail on purpose until
later increments implement the corresponding behavior.

`tests/test_functional_requirements.py` contains one test per system
functional requirement (1.4.1–1.4.6). The tests for A3, A5, and A6 pass; the
tests for A1, A2, and A4 fail until those modules are implemented. See
`docs/traceability.md` for the function-to-module-to-test map.

`tests/test_data_access.py` and `tests/test_model_adapter.py` cover the
Chapter 8 data access component and model adapter, including every
schema-violation fallback. They need no running model.
`tests/test_rule_table.py` checks that the draft parking-rule table has the
SPEC Data Contract section 4 shape. The rules themselves are unconfirmed.
`tests/test_eligibility_filter.py` runs the DO-04 scenarios against the C.1.4
Eligibility Filter Module (Lab 9.4; see `docs/deviation-log.md`).

To see what the real model returns, run the manual live check. It needs
Ollama running with `qwen3:4b` pulled, and CI does not run it:

```bash
python scripts/live_model_check.py
```

For each simulated driver message it prints the model's raw reply, the
adapter result, and whether that result is the expected one. Use
`--message "..."` to try a message of your own.

`tests/test_interface_contract.py` checks that each A1–A6 module matches the
internal interface contract in `contracts/api-v1.yaml`. After changing the
contract, regenerate the stubs with:

```bash
python contracts/generate_stubs.py
```
