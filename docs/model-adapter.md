# Language Model Adapter Specification

Lab Manual §8.5.2 asks for these to be specified before the adapter is
generated: the prompt template, the parameters, the timeout, the token limits,
the required response schema, and the behavior when the model does not
return that schema. Implemented in `language_model/__init__.py`. Tested in
`tests/test_model_adapter.py`.

- **Asset:** C.1.1 Trip Request Interpretation Module
- **Function:** A1.1 Interpret and Confirm Parking Requests
- **Governing documents:**
  - SPEC.md Model Response Contract and Data Contract §5
  - ADR-0002, which limits the model to interpretation only
  - SR-12, which requires the six-field request
  - SR-04, which forbids retaining raw chatbot messages

## Model and endpoint

| Item | Value |
|---|---|
| Runner / model | Ollama, `qwen3:4b` (docs/environment.md) |
| Endpoint | `POST http://127.0.0.1:11434/api/chat`. Loopback only, so no data leaves the machine |
| Calls per driver message | One. No retries |

## Prompt template

There are two messages: a fixed system prompt and a user prompt. The
application fills in the user prompt. As the Model Response Contract
requires, the application supplies the message, the current date and time,
and the supported values.

```
Current date and time: {submitted_at}
Supported destinations: {destinations}
Supported vehicle categories: {vehicle_categories}
Supported eligibility values: {eligibility_values}
Driver message: {message}
```

The system prompt tells the model to do the following:

- Return exactly one of the two contract objects.
- Copy destination, vehicle category and eligibility from the supported
  values.
- Write times as offset-aware ISO 8601.
- List `access_needs` as missing when the message does not say whether
  accessible parking is needed.
- Never guess a value.

The full text is `SYSTEM_PROMPT` in the adapter.

The supported values are still provisional. They are listed in
`smart_parking_service.PROVISIONAL_SUPPORTED_VALUES` until the team approves
the lists (prompt log 2026-10-04, deferred item 3).

## Parameters and limits

| Parameter | Value | Why |
|---|---|---|
| `temperature` | 0 | Interpretation should be repeatable |
| `seed` | 5151 | Repeatable runs for testing |
| `think` | false | Qwen3's reasoning text would break the JSON-only reply |
| `format` | JSON schema with `status` ∈ {complete, incomplete}, `trip_request`, `missing_fields` | Ollama constrains decoding to this schema. The adapter still validates the reply, because the constraint is not trusted |
| `stream` | false | One reply object |
| `num_predict` (output token limit) | 512 | A complete reply is about 120 tokens |
| `num_ctx` (context limit) | 4096 | Fits the prompt plus the longest allowed message |
| Input limit | 2000 characters | A longer message is not sent. The adapter returns a fallback |
| Timeout | 60 s | Covers loading the model the first time on a laptop CPU. SR-13's 5 s budget starts after the request is confirmed, so it does not include this call |

## Required response schema

The schema is the SPEC.md Model Response Contract, applied strictly:

- **`complete`.** The keys are exactly `status` and `trip_request`.
  `trip_request` has exactly the six fields, and each field must pass these
  checks:
  - `destination`, `vehicle_category` and `declared_eligibility` are in the
    supported values.
  - `access_needs` is a boolean.
  - Both times are offset-aware ISO 8601.
  - `submitted_at ≤ arrival_time ≤ submitted_at + 60 min`.
  - `departure_time > arrival_time` (Data Contract §5).
- **`incomplete`.** The keys are exactly `status` and `missing_fields`.
  `missing_fields` is a non-empty list of distinct names, all taken from the
  six fields.

## Behavior when the model does not return that schema

The adapter does not raise an error. It returns
`{"status": "fallback", "reason": <code>}`, and the application discards the
model output and shows the six-field form. The reason code is for tests and
diagnostics only. The driver never sees it, the raw model output, or an
internal error.

| Reason | Trigger |
|---|---|
| `malformed_json` | The reply is not JSON, is not an object, or the Ollama envelope has no `message` |
| `unsupported_status` | `status` is missing or is not `complete` or `incomplete` |
| `invalid_fields` | Any of the field checks above fails, including extra keys |
| `output_truncated` | Ollama reports `done_reason: "length"` |
| `model_unavailable` | Connection refused, timeout, or another transport error |
| `message_too_long` | The message is longer than 2000 characters. The model is not called |

A `complete` result still goes to the driver for confirmation, and the
confirmed or edited values are validated again before prediction (SPEC.md).
An `incomplete` result asks the driver for the missing fields. It never
triggers a prediction.
