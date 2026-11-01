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
Current local date and time: {YYYY-MM-DD HH:MM} (UTC{±HH:MM})
Supported destinations: {destinations}
Supported vehicle categories: {vehicle_categories}
Supported eligibility values: {eligibility_values}
Meaning of eligibility values: permit_O = the driver holds an O permit; visitor = visitor or hourly parking
Driver message: {message}
```

The system prompt tells the model to do the following:

- Reply with one JSON object that has exactly the six field names.
- Use `null` for any field the driver did not state, and never guess.
- For destination, vehicle category and eligibility, write the supported
  value only when the driver clearly names it. Otherwise copy the driver's
  own words. A permit counts only if the driver names that exact permit.
- Write times as 24-hour `HH:MM`. Convert am/pm. When the driver gives no
  am/pm or time-of-day word, write the hour as given ("3:40" becomes
  `03:40`). Turn a length of stay into a departure time.
- Set `access_needs` to true or false only when the driver says so.

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
| `format` | JSON schema: the six fields, all required, each a string or null (`access_needs` a boolean or null). No enum | Ollama constrains decoding to this schema. An enum was tried and dropped: it forced unsupported values onto supported ones (prompt log 2026-10-28, live run) |
| `stream` | false | One reply object |
| `num_predict` (output token limit) | 512 | A reply is about 60 tokens |
| `num_ctx` (context limit) | 4096 | Fits the prompt plus the longest allowed message |
| Input limit | 2000 characters | A longer message is not sent. The adapter returns a fallback |
| Timeout | 60 s | Covers loading the model the first time on a laptop CPU. SR-13's 5 s budget starts after the request is confirmed, so it does not include this call |

## Model reply format

The model does not return the Model Response Contract object itself. It
returns the six fields, and the adapter builds the contract object from them
(SPEC.md Model Response Contract, Output schema):

```json
{
  "destination": "Upson Hall",
  "arrival_time": "11:20",
  "departure_time": null,
  "vehicle_category": "SUV",
  "declared_eligibility": "faculty CU permit",
  "access_needs": null
}
```

## How the adapter assembles the contract

Each field is checked on its own. A value that fails its check is listed in
`missing_fields`, and the driver supplies it on the confirmation step. The
adapter never replaces it with another value.

| Field | Kept when | Otherwise |
|---|---|---|
| `destination`, `vehicle_category`, `declared_eligibility` | It matches a supported value, ignoring case. The approved spelling is kept | Missing |
| `arrival_time` | It is `HH:MM`, and that time on the submission date, with the submission's UTC offset, is no earlier than the submission minute and at most 60 minutes later (Data Contract §5) | Missing |
| `departure_time` | `arrival_time` is kept, and this `HH:MM` on the same date is later than the arrival | Missing |
| `access_needs` | It is true or false | `null` (not stated) is set to `false` (SPEC.md Model Response Contract); the confirmation step shows the value, and the driver can change it. Any other value, such as `"yes"` or `1`, is listed as missing |

If no field is missing, the result is
`{"status": "complete", "trip_request": {...six fields...}}`, with offset-aware
ISO 8601 times. Otherwise it is
`{"status": "incomplete", "missing_fields": [...]}`, in the six-field order.

Known limits:

- A time with no am/pm is taken as written. "3:20" sent at 15:00 becomes
  03:20, which is outside the arrival window, so `arrival_time` is listed as
  missing.
- Times are not carried past midnight. An arrival after midnight sent before
  midnight, or a departure on the next day, is listed as missing.
- The 60-minute arrival window is under team review (meeting planned for
  the week of 2026-11-02).

## When the reply is discarded

The adapter does not raise an error. When the reply cannot be used at all, it
returns `{"status": "fallback", "reason": <code>}`. The application then
discards the model output and shows the empty six-field form. The reason code
is for tests and diagnostics only. The driver never sees it, the raw model
output, or an internal error.

| Reason | Trigger |
|---|---|
| `malformed_json` | The reply is not JSON, is not an object, or the Ollama envelope has no `message` |
| `wrong_fields` | The object does not have exactly the six field names |
| `output_truncated` | Ollama reports `done_reason: "length"` |
| `model_unavailable` | Connection refused, timeout, or another transport error |
| `message_too_long` | The message is longer than 2000 characters. The model is not called |

A `complete` result still goes to the driver for confirmation, and the
confirmed or edited values are validated again before prediction (SPEC.md).
An `incomplete` result asks the driver for the missing fields. It never
triggers a prediction.

## Checking the real model

The pytest suite uses a fake transport. To see what the real model returns,
run `python scripts/live_model_check.py` with Ollama running (README). It
sends four ordinary and two non-standard messages and prints each raw reply
and adapter result.
