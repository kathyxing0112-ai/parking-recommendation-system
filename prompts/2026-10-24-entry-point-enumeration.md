# Entry-Point Enumeration — Lab 6 Product Build

Context: SYSEN 5151 Team 26, Lab 6 Product Build (Lab Manual §6.4, p.109–111).
Branch: lab6-lab7-architecture-definition. Read SPEC.md, docs/traceability.md and
docs/walking-skeleton.md first.

Task: READ ONLY. Enumerate every function in this repository that is callable as a
top-level entry point — something the Cornell Driver (or any external actor) triggers
directly, not something only our own code calls. Include app.py and every public function
in cornell_driver_interface/, and anything else reachable from __main__ or an external
actor. For each, list: file, function, what calls it, and what it calls.
Also list any function that nothing calls at all.
Do NOT map them to use cases and do NOT change any file. I will do the mapping.
Save this prompt as prompts/2026-10-24-entry-point-enumeration.md.
