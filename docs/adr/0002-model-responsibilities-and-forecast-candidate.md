# ADR-0002: Model Responsibilities and Forecast Candidate

## Status

Accepted

## Context

ADR-0001 selected a local Ollama-hosted Qwen3 4B model and initially assigned it the task of explaining parking recommendations. The current six-field trip request and `SPEC.md` model response contract require a different role: the language model interprets chatbot input, while the application validates the request, checks parking rules, forecasts availability, ranks eligible areas, and presents the results.

The pilot uses explicitly labeled simulated occupancy data for three parking areas. It needs an arrival-time occupancy forecast that can be evaluated against a simple historical time-slot baseline. A forecasting candidate is needed now, but its performance has not yet been established.

## Decision

- Keep Qwen3 4B, hosted locally through Ollama, as the initial language model. Use it only to interpret a user's chatbot message into the structured six-field trip request specified in `SPEC.md`, or to identify missing fields. The application validates the output and obtains user confirmation before prediction. If the output is malformed or invalid, the application falls back to the six-field form.
- Qwen3 does not generate explanations of recommendations, predict parking availability, determine eligibility, or rank parking areas. The application displays explanations derived from the verified rules, walking time, data age, forecast, uncertainty, and ranking factors actually used.
- Use LightGBM as the **candidate** arrival-time occupancy forecasting model. Its input features and output are governed by the `SPEC.md` data contract. LightGBM produces forecasts for eligible evaluation horizons; it does not directly produce the ranked list of lots. The application applies confirmed parking rules and the specified scoring and tie-break rules to create that ranking.
- Compare LightGBM with the historical time-slot baseline using validation MAE on simulated weeks 11–12 after training on weeks 1–10. Select the lower-validation-MAE approach, then evaluate the selected approach once on held-out weeks 13–15. If valid forecasting inputs are unavailable, do not present an unsupported forecast.

## Rationale

Separating language interpretation from forecasting keeps the chatbot output checkable against the six required fields and prevents unverified model text from becoming parking facts. Deriving displayed reasons from the application's verified results keeps those reasons aligned with the actual eligibility and ranking decisions.

LightGBM is a candidate for the structured, time-dependent occupancy features in the data contract. Comparing it with a historical baseline on validation data lets the team choose an approach using measured error rather than assuming that the more complex model is better. The held-out period then provides a separate evaluation of the selected approach. This ADR does not claim that LightGBM has been trained, selected, or shown to improve performance.

This ADR changes the Qwen3 responsibility stated in ADR-0001. ADR-0001's Python, virtual environment, local hosting, Ollama, and containerization decisions remain as recorded there.

## What Would Change This Decision

The team may replace Qwen3 4B if tests show that it cannot reliably produce the required six-field interpretation within acceptable local performance limits. Any replacement must satisfy the same response contract and validation flow.

The team may select the historical time-slot baseline instead of LightGBM if it has lower validation MAE, or revisit both approaches if neither provides a usable forecast under the agreed conditions. A change to the forecast features, horizons, selection procedure, or ranking rules requires a corresponding review of `SPEC.md` and the acceptance tests.
