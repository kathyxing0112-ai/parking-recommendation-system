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
Current local date and time: {Weekday YYYY-MM-DD HH:MM} (UTC{±HH:MM})
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
  `03:40`). Put a day word before the time, copied from the driver's words:
  `today`, `tomorrow`, `day after tomorrow`, a weekday name, or a month and
  day such as `Nov 24`; `today` when no day is named. The adapter, not the
  model, turns the day word into a date. Turn a length of stay into a departure time.
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
| `keep_alive` | 30 minutes | Ollama unloads an idle model after 5 minutes by default, and reloading took 4-6 s on the first request (Chapter 10 measurements). 30 minutes keeps the model ready through a quiet spell. It holds about 2.5 GB of memory while loaded |
| Warm-up at start | One full request with the message "warm up", reply discarded | `web_app` sends it in the background when it starts (`smart_parking_service.warm_up_language_model`). Loading the weights alone left the first request at about 3.5 s; a full request brought it to about 2.1 s (2026-11-15). If the model is not running, nothing changes: the first request falls back as before |
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
| `arrival_time` | It is `[day word] HH:MM` and, with the submission's UTC offset, is no earlier than the submission minute and at most 72 hours later, inclusive (Data Contract §5, SR-12). The day word is counted from the submission date: `today`/`tonight` 0, `tomorrow` +1, `day after tomorrow` +2; a weekday name is the next date with that weekday (today's weekday is today); `Nov 24` is that date, this year or next. Any other day word, or a date that does not exist, is unusable. `HH:MM` with no day word is placed on the submission date, or on the next date if it is earlier than the submission minute (sent 23:40, arrive 00:15) | Missing |
| `departure_time` | `arrival_time` is kept, and this time is later than the arrival. With no day word it is on the arrival date. On the arrival date but earlier than the arrival, it is the next date (arrive 23:30, leave `today 01:00`). On an earlier date it is unusable | Missing |
| `access_needs` | It is true or false | `null` (not stated) is set to `false` (SPEC.md Model Response Contract); the confirmation step shows the value, and the driver can change it. Any other value, such as `"yes"` or `1`, is listed as missing |

If no field is missing, the result is
`{"status": "complete", "trip_request": {...six fields...}}`, with offset-aware
ISO 8601 times. Otherwise it is
`{"status": "incomplete", "trip_request": {...}, "missing_fields": [...]}`.
`trip_request` holds only the fields that passed, for the confirmation step to
show filled in. `missing_fields` is in the six-field order.

Known limits:

- A time with no am/pm is taken as written. "3:20" sent at 15:00 becomes
  03:20 tomorrow. The confirmation step shows the date and time, so the
  driver can correct it.
- The UTC offset is the submission's. Within 72 hours that is the local
  offset except across a daylight-saving change (the next one after the pilot
  term is 2027-03-14).
- Times are carried past midnight by the rule above, not by the model: the
  model writes clock times only. Until 2026-11-11 a time past midnight was
  listed as missing, which sent evening requests to the form (found in the
  Chapter 10 measurement trial, docs/measured-behavior.md). A departure the
  driver meant as earlier than the arrival therefore reads as the next day;
  the confirmation step shows the full date and time so the driver can catch it.
- Relative times are unreliable. On 2026-11-03, messages saying "in 30 minutes"
  often kept the current time, or came back as missing, so the driver must check
  them on the confirmation step. Clock times such as "3:45 PM" gave the right
  result in 9 of 10 runs, and the other run came back incomplete. `web/index.html`
  offers a sample message with clock times.
- A trip more than 72 hours ahead is outside this version. The team agreed
  the 72-hour window on 2026-11-17; it replaced the 60-minute limit.
- Named days were added with the 72-hour window. A trial on 2026-11-21
  (local Qwen3 4B, submitted Saturday 15:00) first asked the model to copy
  `YYYY-MM-DD` dates from a list of upcoming dates: 4 of 10 messages got the
  right date, because the model mostly wrote the time only. With day words,
  10 of 10 got the right arrival and departure after "day after tomorrow"
  was added to the examples. On the 40 Chapter 10 requests (times only), the
  old and new prompts read the same 35 times correctly. The driver still
  checks the date on the confirmation step.

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
