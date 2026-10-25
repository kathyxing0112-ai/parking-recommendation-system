# SPEC.md

# Needs and Acceptance Criteria

**Product:** Cornell Smart Parking Availability and Recommendation System  
**Specification status:** Draft for team review, based on *Stakeholder Needs Analysis and Requirements Definition*, SYSEN 5151 Team 26, October 2026.  
**Scope:** Three pilot parking areas using explicitly labeled simulated occupancy data. This specification defines intended behavior and evaluation methods; it does not claim that the behavior has been implemented or that simulated outcomes demonstrate real-world parking performance.

The need and requirement identifiers below match the report: eight effective needs (SN-01–SN-08), fifteen distinct stakeholder requirements (SR-01–SR-15), and nineteen need-to-requirement trace relationships. When an SR supports multiple needs, the same underlying behavior and evidence are used for both traces.

## SN-01 — Campus Mobility Value

**Stakeholder:** Administration / Project Sponsor  
**Need:** “We need evidence that the system provides measurable value for campus mobility.”  
**Traces to:** SR-01 — Mobility Value Evidence.

**Acceptance criteria**

- **SR-01:** The team provides a pilot evaluation report comparing median parking-search time with an agreed static-information baseline. Search time begins when the driver starts looking for parking and ends when a permitted available space is found. The evaluation includes at least 20 matched baseline/pilot tasks under comparable routes, times, and conditions; retains observations and calculations; and reports `100 × (baseline median − pilot median) / baseline median`. The preliminary improvement target is **at least 20%**, subject to sponsor review before evaluation. Simulated-task findings are explicitly labeled simulated. If the baseline median is zero, the report does not calculate a percentage improvement and records that limitation.

**Preliminary MOE:** Percentage reduction in median parking-search time against the static-information baseline. **Evidence:** matched-task records, baseline and pilot medians, calculation, and sponsor review.

## SN-02 — Data Governance and Security

**Stakeholder:** Administration / Project Sponsor  
**Need:** “We need data governance, cybersecurity, privacy, and applicable university policy concerns to be addressed.”  
**Traces to:** SR-02 — Approved Data Use; SR-03 — Security and Access Control; SR-04 — Privacy and Data Retention.

**Acceptance criteria**

- **SR-02:** Before first use, every pilot data source has a recorded owner, permitted use, and review date. The inventory covers simulated occupancy, parking rules, calendar, weather, events, and field counts insofar as each is actually used. Permission or licensing evidence covers the actual use; a source without confirmed permission is excluded. The target is **100% permission coverage of used sources**.
- **SR-03:** Under the approved three-role matrix, a driver may submit a trip, view results, and save, read, or update the trip record of the driver's own session; a maintainer may do the same and may also change parking rules, simulator settings, and model versions; the internal Retention Service may only delete trip records past their 24-hour expiry (SR-04). Any other operation, and any operation by an unrecognized role, is denied. Controlled tests exercise permitted and prohibited operations for all three roles. The expected count of successful prohibited operations is **zero**; decisions and test evidence are retained. Protected maintenance endpoints must enforce the matrix, not merely hide controls in the interface.
- **SR-04:** The product retains only the minimum structured trip and recommendation data needed to evaluate the pilot, for **no more than 24 hours after request submission**. Raw chatbot messages are not retained. A scheduled deletion removes each retained trip record by its 24-hour expiry; an inspection of the pilot database, cache, logs, and backups finds zero records past expiry. Tests use records just before and just after expiry and retain timestamped deletion evidence. The team lists retained fields and storage locations in the approved schedule before collecting pilot requests; no retention exceptions are permitted in the initial pilot. A privacy notice states the evaluation purpose and 24-hour retention period without promising zero risk.

**Preliminary MOEs:** Used-source permission coverage (SR-02); count of successful prohibited operations (SR-03); count of trip records retained beyond their 24-hour expiry within the assessed scope, target **zero** (SR-04). **Evidence:** source inventory and permissions, role-matrix test results, and timestamped retention/deletion inspections.

## SN-03 — Clear System Expectations

**Stakeholder:** Project Development & Operations Team  
**Need:** “We need clear system expectations and stakeholder expectations to guide development.”  
**Traces to:** SR-05 — Traceable Requirements Baseline.

**Acceptance criteria**

- **SR-05:** A versioned Innoslate stakeholder-requirements baseline and a versioned `SPEC.md` identify every requirement's source need and verification method. Every pull request that changes a requirement reviews these traces and criteria; ambiguities that block the proposed change are resolved before merge. The team retains the reviewed versions and decisions.

**Preliminary MOE:** Count of development decisions blocked by unresolved requirement ambiguity or missing requirement information during reviews of requirement-changing pull requests; target: **zero** requirement-changing pull requests merged while a blocking ambiguity remains unresolved. **Evidence:** baseline versions, pull-request reviews, and resolution records.
## SN-04 — System Maintainability and Handoff

**Stakeholder:** Project Development & Operations Team  
**Need:** “We need a maintainable system with clear testing, deployment, handoff, and maintenance responsibilities.”  
**Traces to:** SR-06 — Maintenance and Handoff Documentation; SR-07 — Operations Responsibilities.

**Acceptance criteria**

- **SR-06:** By operational handoff, the team provides an approved checklist and documentation covering startup/deployment, configuration, simulated data, parking rules, model or baseline selection, tests, and failure recovery. A receiving teammate who did not author the relevant instructions completes **all five** core tasks without author assistance: (1) start the product from a clean checkout; (2) generate and replay simulated occupancy data; (3) update a pilot-area eligibility rule and confirm its effect; (4) run the documented test command; and (5) switch to the historical baseline and exercise the unavailable-data fallback. Attempts, outcomes, and gaps are recorded.
- **SR-07:** The responsibility matrix assigns exactly one accountable owner to each of seven pilot activities: needs and Innoslate — **Bochao Liang**; data and rules — **Tingyu Huang**; application development and maintenance — **Katherine Xing**; model evaluation — **Katherine Xing**; testing/CI — **Xichen Wang**; deployment demonstration — **Xichen Wang**; final handoff — **Linzi Gong**. One person may own multiple activities. The team confirms assignments and records later changes; the receiving team can identify the owner for each activity.

**Preliminary MOEs:** Percentage of agreed handoff tasks completed independently, target **5/5** (SR-06); count of pilot activities delayed because no responsible owner can be identified, target **zero** (SR-07). **Evidence:** checklist, independent task record, and dated responsibility matrix.

## SN-05 — Reliable and Current Parking Information

**Stakeholder:** Cornell Transportation & Parking Services  
**Need:** “We need parking information used by the system to be reliable and sufficiently current to support parking decisions.”  
**Traces to:** SR-08 — Parking Information Freshness; SR-09 — Stale Data Handling.

**Acceptance criteria**

- **SR-08:** For the simulated pilot feed scheduled to update every **30 seconds**, the product refreshes displayed, timestamped current parking information at intervals of **no more than 60 seconds** under the stated demonstration conditions. Observation age is computed from the source timestamp. In the agreed simulated decision set, **at least 95% of all assessed parking decisions** are supported by an observation no more than **120 seconds** old. Normal updates, delayed events, and feed interruption are exercised. An observation older than 120 seconds is never represented as current.
- **SR-09:** If observation age **exceeds 120 seconds**, the interface displays a prominent stale label and the last-observed time. Controlled cases at **119, 120, and 121 seconds**, plus feed interruption, verify the boundary. In agreed interpretation scenarios, **at least 9 of 10** test users correctly identify stale information. A source with no usable timestamp is treated as unavailable or stale rather than current.

**Preliminary MOEs:** Percentage of simulated decisions supported by observations within the 120-second freshness limit (SR-08); percentage of users correctly identifying stale information (SR-09). **Evidence:** update/observation timestamps, interruption cases, interface captures, and user responses. SR-08 and SR-09 also support SN-07 through the same checks.

## SN-06 — Parking Policy and Operations Compliance

**Stakeholder:** Cornell Transportation & Parking Services  
**Need:** “We need recommendations to remain consistent with Cornell parking rules, permit eligibility, and operating policies.”  
**Traces to:** SR-10 — Eligibility and Policy Compliance.

**Acceptance criteria**

- **SR-10:** For the requested parking interval, every returned option follows the dated, confirmed rule table for the three pilot areas. The agreed cases cover permit and visitor eligibility, accessibility needs, closures, and time restrictions; **100% of evaluated returned options** must match the confirmed rules. An option whose eligibility is not resolved by a confirmed rule produces no assertion that an option is eligible.

**Preliminary MOE:** Percentage of evaluated returned options consistent with confirmed rules and declared eligibility. **Evidence:** rule-table version, scenario inputs, expected outcomes, and returned results. SR-10 also supports SN-08 through the same check.

## SN-07 — Clear and Reliable Parking Information

**Stakeholders:** Students, Faculty, Staff  
**Need:** “We need clear, easy-to-use, and sufficiently current parking information to support our travel decisions.”  
**Traces to:** SR-08 — Parking Information Freshness; SR-09 — Stale Data Handling; SR-11 — Parking Information Usability; SR-15 — Recommendation Explanation.

**Acceptance criteria**

- **SR-08:** The current-status view uses the timestamped feed and the **30-second source / 60-second display / 120-second freshness** conditions specified under SN-05. The same update and decision-age evidence is used for this trace.
- **SR-09:** Information older than **120 seconds** is visibly labeled stale and includes the last-observed time, as verified by the SN-05 boundary and interruption scenarios. At least **9 of 10** test users identify the stale cases correctly.
- **SR-11:** **10 representatives of the pilot user groups** attempt the agreed tasks for interpreting availability, eligibility, freshness, and forecast uncertainty. Compare responses with a prewritten answer key. At least **85% of attempted tasks** are completed correctly; record completion time and apply an initial target of a **median completion time of no more than 60 seconds per task**. Define participant coverage and task wording before the sessions.
- **SR-15:** Each returned parking option shows the eligibility basis, walking time, arrival forecast and uncertainty when a valid forecast exists, and data age. The stated ranking reasons match factors actually used by the ranking logic. Against an agreed answer key, at least **85% of 20 user explanations** correctly identify why an option was recommended. When forecasting is unavailable, the explanation says so and does not present an invented forecast.

**Preliminary MOEs:** Fresh-observation decision rate (SR-08); stale-information recognition (SR-09); correct interpretation-task rate with task time (SR-11); correct explanation rate (SR-15). **Evidence:** the shared SR-08/SR-09 checks, usability responses, recorded times, and comparison of displayed reasons with actual ranking factors.

## SN-08 — Suitable Parking Recommendations

**Stakeholders:** Students, Faculty, Staff  
**Need:** “We need recommendations that consider our destination, arrival time, and parking eligibility.”  
**Traces to:** SR-10 — Eligibility and Policy Compliance; SR-12 — Trip Constraints Input; SR-13 — Primary and Backup Recommendations; SR-14 — Arrival-Time Availability Support; SR-15 — Recommendation Explanation.

**Acceptance criteria**

- **SR-10:** Before ranking, exclude options that violate confirmed permit, accessibility, closure, or time rules for the trip. Every returned option passes the **100% rule-consistency** check specified under SN-06; an option whose eligibility is not resolved by a confirmed rule is not asserted as eligible.
- **SR-12:** The confirmed trip request is represented by **six fields**: destination; arrival time; departure time; vehicle category; declared eligibility; and access needs. For known requests, every recorded field matches the user's confirmation. Missing required fields or invalid values block the recommendation until corrected.
- **SR-13:** Rank only eligible areas. When at least two eligible areas exist, return the approved ranking's first and second options as primary and backup. The initial ranking weights are **40% walking time, 40% arrival-time availability, and 20% forecast uncertainty**, with higher scores for shorter walks, greater availability, and lower uncertainty. If any eligible area lacks a supported forecast, rank all eligible areas by walking time alone, and the explanation states that forecasts are unavailable. Do not imply that spaces are reserved or guaranteed. In **30 valid local demonstration requests** with at least two eligible areas, display the two options within **5 seconds** of receiving the complete confirmed request. With one eligible area, show one option; with none, state that no confirmed eligible option is available. When valid forecasts exist for all candidates, score each area as S = 0.40W + 0.40A + 0.20Q, where W = (w_max − w)/(w_max − w_min) for walking time w (W = 1 when all walking times are equal), A = F/C for forecast available spaces F and capacity C, and Q = 1 − (U − L)/C for the 80% prediction interval [L, U]. Inputs must satisfy C > 0, 0 ≤ F ≤ C, and 0 ≤ L ≤ U ≤ C. Round scores half-up to six decimals and rank by descending S, then ascending walking time, then area ID. If any forecast or interval is invalid, use the labeled fallback ordered by ascending walking time, then area ID. Freeze these scoring and tie-break rules before evaluation.
- **SR-14:** Provide a forecast only for an area with an observation no more than **120 seconds** old, confirmed applicable rules, and all required features. Produce arrival-time estimates for **0–60 minutes ahead in 15-minute steps**; withhold an unsupported forecast. For an arrival time between grid points, linearly interpolate the estimate and its interval bounds between the two adjacent 15-minute horizons, without extrapolating beyond the 0–60-minute range (for example, an arrival 37 minutes after the request interpolates between the 30- and 45-minute forecasts). The captured arrival time is not shifted to a grid point. Train the candidate model on simulated weeks **1–10**. Compare the model with the historical time-slot baseline using mean absolute occupancy error (MAE) on validation weeks **11–12**, and select the approach with the lower validation MAE. Evaluate the selected approach once on held-out simulated weeks **13–15**. On that holdout set, the preliminary target is **at least 85% top-pick availability** among forecast-supported trips. Assess whether the stated **80% prediction interval** covers observations in **75%–85%** of applicable simulated holdout cases. Report any field observations separately. If neither model nor baseline has valid inputs, display no forecast.
- **SR-15:** Every returned option includes the ranking-basis explanation specified under SN-07. Explanations are checked against the factors and data actually used; in the agreed scenarios, at least **85% of 20 assessed user responses** correctly explain the recommendation. No explanation asserts confirmed availability, eligibility, or a forecast when supporting data are absent.

**Preliminary MOEs:** Policy-consistent returned options (SR-10); correctly captured confirmed trip requests (SR-12); percentage of assessed trips with a suitable primary or backup option, preliminary target **at least 90%** with simulated and real-world findings reported separately (SR-13); percentage of simulated forecast-supported trips whose top option has space at arrival, preliminary target **at least 85%** (SR-14); correctly understood ranking explanations (SR-15). **Evidence:** confirmation and structured-request records, rule checks, ranked outputs, timings, holdout results, and explanation responses.

# Data Contract

**Status:** Draft for team review. This contract covers the three pilot parking areas and the initial six-field trip request. Occupancy and training examples below are simulated; example counts and rules do not represent confirmed Cornell inventory or policy.

## Common rules

- Use stable `lot_id`, `zone`, and `space_id` values across the sensor stream, lot metadata, rules, and model inputs. A `space_id` belongs to exactly one lot and one physical zone.
- Store machine-readable times as ISO 8601 timestamps with a UTC offset. Compare times as instants; apply parking-rule hours in the rule's stated local time zone. The example offset `-04:00` is illustrative and must follow the date's actual offset.
- A sensor `timestamp` is the observation time, not the time the application received it. Compute data age from the observation time. Observations older than **120 seconds**, or without a valid timestamp, cannot be shown as current or used for a supported forecast.
- The simulated feed targets one update every **30 seconds**. The displayed current status refreshes within **60 seconds** under the declared demonstration conditions. The 15-minute training series is derived from the event stream; it is not a second live sensor feed.
- Validate source, owner, permitted use, and review date before using each data source. Keep rule versions and provenance with evaluation evidence. An option whose eligibility is not resolved by a confirmed rule must not produce a claim that parking is permitted.

## 1. Simulated parking-space sensor events

One event reports the observed state of one physical space. The initial pilot simulates this stream; the interface does not claim it is a live Cornell sensor API.


```json
{
  "space_id": "L1-A-023",
  "lot_id": "L1",
  "zone": "permit_O",
  "status": "occupied",
  "timestamp": "2026-10-02T10:47:15-04:00"
}
```

| Field       | Type and rule                                                |
| ----------- | ------------------------------------------------------------ |
| `space_id`  | Required stable string; must exist in the pilot space inventory. |
| `lot_id`    | Required stable string; must match the space's configured lot. |
| `zone`      | Required string; must match the space's configured physical zone. |
| `status`    | Required enum: `occupied`, `vacant`, or `unknown`. `unknown` is not counted as an available space. |
| `timestamp` | Required offset-aware ISO 8601 observation time. Reject an invalid or future observation timestamp more than **5 seconds** ahead of the application clock. |

For each space, the latest valid event at or before the decision time determines its observed state. Ignore duplicate events and prevent late arrivals from replacing a newer observation. Record ingestion gaps and stale observations; do not silently convert them to vacant spaces. Space-level availability is derived only from valid, sufficiently fresh observations and applicable confirmed rules.

## 2. Fifteen-minute modeling table

Use one row per `lot_id`, 15-minute `as_of_timestamp`, and forecast horizon. Aggregate the simulated sensor stream into observed lot occupancy; record the aggregation method and missing-space coverage. The following values are illustrative, not observed Cornell data.

| Field                                               | Type / example                    | Meaning                                                      |
| --------------------------------------------------- | --------------------------------- | ------------------------------------------------------------ |
| `lot_id`, `as_of_timestamp`                         | `L1`, `2026-10-02T10:45:00-04:00` | Pilot lot and the feature cutoff time.                       |
| `horizon_minutes`                                   | `15`                              | Forecast horizon; use 15, 30, 45, or 60 minutes for future training labels. The 0-minute value is the current observation. |
| `occupied`, `capacity`, `occupancy_rate`            | `182`, `200`, `0.91`              | Occupancy known at the cutoff; `occupancy_rate = occupied / capacity`. Validate `0 <= occupied <= capacity` and `capacity > 0`. |
| `day_of_week`, `time_of_day`, `semester_week`       | `4`, `10:45`, `6`                 | Calendar features defined from the cutoff time; document weekday numbering and semester calendar. |
| `is_class_day`, `is_break`, `event_flag`            | `1`, `0`, `0`                     | Context known by the cutoff from the approved calendar/event source. |
| `temp_c`, `precipitation_mm`, `snow_flag`           | `12.0`, `0.0`, `0`                | Weather values or forecasts available by the cutoff; record source and issue time. |
| `lag_15`, `lag_30`, `lag_60`, `same_time_last_week` | `0.88`, `0.84`, `0.75`, `0.90`    | Historical occupancy rates measured strictly before the cutoff. |
| `rolling_mean_1h`                                   | `0.85`                            | Mean of available historical occupancy rates in the preceding hour; document the window and missing-value rule. |
| `target_occupancy_rate`                             | `0.93`                            | Actual simulated occupancy rate at `as_of_timestamp + horizon_minutes`; **training/evaluation label only**, never an inference input. |

Feature generation must use only information available at the cutoff. Do not use later sensor events, observed future weather, or future labels as predictors. If required history or a required feature is absent, mark the forecast unsupported rather than inventing input data. Train on simulated weeks **1–10**, select the model or historical time-slot baseline using MAE on weeks **11–12**, and evaluate the selected approach once on held-out weeks **13–15**. Preserve the simulator configuration and split boundaries so results can be reproduced.

## 3. Pilot lot and space metadata

Maintain a dated inventory for exactly the three selected pilot lots. Identifiers, coordinates, capacities, and restrictions below are **schema examples only**; replace them with confirmed values or clearly labeled simulator assumptions before evaluation.

```json
{
  "lot_id": "L1",
  "name": "Example pilot lot",
  "latitude": 42.44,
  "longitude": -76.48,
  "capacity_by_zone": {
    "permit_O": 150,
    "visitor": 40,
    "accessible": 10
  },
  "source_type": "simulated_inventory",
  "reviewed_at": "2026-10-02T09:00:00-04:00"
}
```

`capacity_by_zone` counts **distinct physical spaces**; a space appears in exactly one zone so the sum is the lot's physical capacity. Accessibility and permit eligibility are determined by the rule table and may require more than the zone name. The space inventory maps each `space_id` to one `lot_id` and `zone`; its counts must reconcile with `capacity_by_zone`. Coordinates support walking-distance estimates; state the routing or distance assumption used.

## 4. Versioned parking-rule table

Represent each confirmed rule as a dated record for a lot or zone, eligibility class, and time window. The table decides whether an option may be returned for the **entire requested parking interval**.

| Field                                                | Required meaning                                             |
| ---------------------------------------------------- | ------------------------------------------------------------ |
| `rule_id`, `version`                                 | Stable rule identifier and version used for traceability.    |
| `lot_id`, `zone`                                     | Matching pilot lot and physical zone; an explicit wildcard may represent a lot-wide rule. |
| `eligibility_class`                                  | Declared permit/visitor class or accessibility qualification covered by the rule. |
| `valid_from`, `valid_until`, `time_zone`             | Effective date range and local time zone.                    |
| `days_of_week`, `start_local_time`, `end_local_time` | Applicable days and daily window; define how overnight windows work. |
| `allowed`, `closure`                                 | Whether the class may park and whether the area is closed in that window. A confirmed closure overrides an allowance. |
| `source`, `owner`, `reviewed_at`                     | Policy provenance, responsible owner, and last review time.  |

The team may derive this table from permitted Cornell parking information, but must review and date the interpretation before use. Cover permit, visitor, accessible, closure, and time-restriction cases. If no confirmed rule resolves a trip's eligibility, do not label that option eligible. Do not present example rules as official Cornell policy.

## 5. Confirmed trip request (form and chatbot)

Both interfaces produce the **same six-field structured request**. A chatbot may ask clarifying questions, but only the confirmed structured values enter recommendation logic; `group_size` and `convoy_vehicle_count` are outside this version.

```json
{
  "destination": "Upson Hall",
  "arrival_time": "2026-10-02T11:20:00-04:00",
  "departure_time": "2026-10-02T13:00:00-04:00",
  "vehicle_category": "sedan",
  "declared_eligibility": "permit_O",
  "access_needs": false
}
```

| Field                  | Type and validation                                         |
| ---------------------- | ----------------------------------------------------------- |
| `destination`          | Required supported destination name or identifier; resolve it to a known location for walking-distance calculation. |
| `arrival_time`         | Required offset-aware ISO 8601 timestamp; must be no earlier than the request time and no more than 60 minutes after it. |
| `departure_time`       | Required offset-aware ISO 8601 timestamp; must be later than `arrival_time`. Test rules across the full interval. |
| `vehicle_category`     | Required value from the approved vehicle-category list. A category alone does not establish a vehicle's height. |
| `declared_eligibility` | Required confirmed permit/visitor eligibility value. If unknown, request clarification. |
| `access_needs`         | Required boolean indicating whether accessible parking is requested; any required credential or policy condition must still be confirmed by the rules. |

Missing or invalid required values block recommendations until corrected. The interface shows the six interpreted values for user confirmation. A trip request concerns one vehicle; this version does not allocate multiple vehicles as a group.

## Retention and evaluation boundary

The pilot may retain confirmed structured trip fields, recommendation output, and submission time in the approved application storage for **no more than 24 hours after submission**. Delete each retained trip record by its expiry; the target is **zero identifiable trip records past 24 hours** in the assessed database, cache, logs, and backups. Do not persist raw chatbot messages in application records or logs. No retention exception is permitted in the initial pilot. Document exact retained fields and storage locations before collecting requests, and show users the evaluation purpose and 24-hour period in a privacy notice.

Simulated sensor streams, non-identifying modeling tables, lot metadata, rule versions, and aggregate evaluation results are separate from identifiable trip requests; retain them according to their documented source and project schedules. Do not copy trip details into long-lived training or evaluation files. Keep timestamped deletion-test evidence without retaining the tested personal record itself beyond expiry.


# Model Response Contract

The local language model configured in `docs/environment.md` interprets a user's chatbot message as a trip request. It does not predict parking availability or rank parking areas. The application provides the message, current date and time, and the supported destination, vehicle-category, and eligibility values.

**Output schema:** The model returns exactly one of the following JSON objects.

A complete interpretation contains all six required fields:

```json
{
  "status": "complete",
  "trip_request": {
    "destination": "Upson Hall",
    "arrival_time": "2026-10-02T11:20:00-04:00",
    "departure_time": "2026-10-02T13:00:00-04:00",
    "vehicle_category": "sedan",
    "declared_eligibility": "permit_O",
    "access_needs": false
  }
}
```
If the message does not state whether accessible parking is needed, the model lists access_needs in missing_fields rather than assuming `false`.

If any required field is missing or cannot be determined reliably, the model identifies the missing fields instead of inventing values:

```json
{
  "status": "incomplete",
  "missing_fields": ["arrival_time", "declared_eligibility"]
}
```

The application validates a `complete` trip request against the six-field Data Contract and asks the user to confirm it. The user may edit any field before confirming. The values the user confirms, not the raw model output, enter the parking prediction and ranking pipeline. Edited values are validated again against the Data Contract, and an invalid value blocks the request until it is corrected. Only a confirmed request with all six valid fields may enter the parking prediction and ranking pipeline. An `incomplete` response prompts the user to provide the missing fields; it never triggers a prediction.

**Fallback:** If the model returns malformed JSON, an unsupported status, or invalid fields, the application discards the model response and presents the six-field form for the user to complete. It never sends an incomplete request to the forecasting model or displays raw model output or an internal error to the user.