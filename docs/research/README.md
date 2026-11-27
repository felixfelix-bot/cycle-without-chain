# Consolidated research — candidate design only

The controller and machine research is preserved here, including fetched evidence,
CSV candidate BOM and executed allocation model. No schematic or routed PCB is
complete. This is NOT a manufacturing release or procurement approval.

- [Controller design envelope](controller/design-envelope.md)
- [Candidate BOM](controller/candidate-bom.csv)
- [Machine candidates](machines/candidates.md)
- [Allocation model](controller/efficiency_model.py)

## Evidence boundaries

Manufacturer PDFs and extracted text are retained for traceability. The zero-byte
Infineon files record failed fetches, not verified datasheets. The ST proxy text is
secondary retrieval, not a verified package pinout. Machine research used search
excerpts and needs direct datasheet verification. Stock and bicycle fit are not
verified. Freewheeling geared wheel candidates do not satisfy regen as-is.

Current assumptions are not approved ratings: the controller report introduces
300W/500W bursts and current limits for research only. Storage is not selected;
the battery-buffered example does not close the battery-versus-capacitor decision.

## Historical separate repository

`archive/chainless-ebike-tradeoff/` preserves the earlier separate repository's
analysis and uncommitted edits so work is not lost. It is historical, NOT the
current specification. It contains known unsupported efficiency claims, model
simplifications and stale absolute renderer paths. Passing its arithmetic tests
does not validate its physical assumptions. Use the current evaluation plan and
illustrated guide, not historical prose, for agreed requirements.

The separate repository remains accessible at
https://github.com/felixfelix-bot/chainless-ebike-tradeoff .
No other worker's in-progress branch is included or approved by this consolidation.
