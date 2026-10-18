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
printed with its UC.1 message identifier. All data sources, the language model,
and the ranking are hard-coded stubs returning synthetic values; see
`docs/walking-skeleton.md` for the message-to-code mapping.

## Running the Acceptance Tests

```bash
python -m pytest tests/ -v
```

`tests/test_spec_acceptance.py` contains 19 acceptance-test placeholders, one
for each need-to-requirement trace in `SPEC.md`. They fail on purpose until
later increments implement the corresponding behavior.