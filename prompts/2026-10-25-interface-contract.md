# Internal Interface Contract — Lab 7 Product Build

Context: SYSEN 5151 Team 26, Lab 7 Product Build (Lab Manual §7.4, p.126–129).
Branch: lab6-lab7-architecture-definition.

Task: Write contracts/api-v1.yaml from the model's internal-flow list, not from the
existing code. The flow list is I-01 to I-12 in B2_Trace_Mapping.xlsx (sheet 02 I-O
Coverage, Innoslate V2), with field shapes from the SPEC.md Data Contract and the
record shapes the team accepted in Chapter 5 (prompt-log 2026-10-18, finding 4).

Team decisions given to the assistant:
- One operation per receiving first-level function (A1–A6); the twelve flows are
  component schemas labeled with flow ID and trace numbers.
- Validated Parking Data is lot-level (occupied, capacity, observed_at).
- Keep caller_session_id and record_session_id in Protected Data Operation Request.
- Ranked Parking Recommendations carries trip_summary (six confirmed fields, from
  flow 9.13) in place of the removed "inputs" payload.
- Generate stubs with a small script (contracts/generate_stubs.py) and add a
  conformance test that each A1–A6 signature matches its stub.
- Refactor depth: make A1–A6 conform to the contract; do not wire
  smart_parking_service to A1–A4 in this increment.

Then generate the stubs from the contract, change the code to match, and record
every divergence the contract exposed in docs/adr/0003-internal-interface-contract.md,
naming the model entities affected. Do not resolve a divergence silently in either
direction.
