# Export verifier hardening milestone

2026-11-10. Base: `16b19d1d082e2c0e98894190b1f7ea5b1cfd1813`.
Branch: `pr/verifier-hardening`. **Consistency checking only; not electrical,
package/datasheet, manufacturing or energization approval.**

## Changes and ownership

Only `hardware/powerboard-reva/verify_exports.py`, its new
`tests/test_verify_exports.py`, and this report change. No generator changes,
schematic geometry/circuit changes, or generated artifacts. The checker no
longer imports `generate_schematic`; it owns a small strict S-expression reader.
It reads existing CSV expectations and exported evidence without rewriting
anything (including `exports/verification.json`). JSON results go to stdout.
The existing verification.json is historical, not refreshed by this command.

Explicit exceptions and a nonzero CLI exit replace optimization-sensitive
assertions. Missing, empty, malformed or inconsistent required inputs fail.
The tests compare every fixture file's bytes before/after success and failure.
The generation/export script still deliberately generates artifacts; validation
alone does not. Its normal ERC invocation remains report-only, not an ERC gate.

## Boundaries

- Exactly 84 unique component references, including 12 Q references and 2 U
  references. Exact reference/value/footprint agreement with `review-bom.csv`.
  A Q prefix is a count check, not independent MOSFET identity qualification.
- Exactly 308 unique ref/pin endpoints, no overwritten duplicate assignments,
  exact endpoint-to-net equality with `pin-net-map.csv`.
- Exactly 80 distinct net names; exact manifest net-name set, unique net codes,
  no empty/extra nets. Net codes need not have particular numeric identities.
- CSV columns/row counts, uniqueness and mutual reference sets are checked.
  Empty BOM footprints remain permitted because this partial circuit has them.
- ERC must contain exactly the documented three error identities: U1.3 VM on
  AUX12V_EXT, U1.24 VREF on LOGIC3V3_EXT, U1.25 AGND on PGND; totals 3 errors,
  zero warnings. Three repeated errors of one identity cannot pass. This is a
  version-specific partial milestone signature, **not an approved waiver**.
  A future circuit or KiCad report-format change needs reviewed expectations.
- Existing CSVs remain generator-derived claims. Coordinated modifications of
  both expectation and export are not independently detected; no datasheet
  qualification, golden trust root or protection functionality is claimed.
- SVG page count is descriptive only. PDF/SVG correctness, unlisted netlist
  metadata, symbol-library pin semantics, footprint geometry, and electrical
  adequacy are outside this checker.

## Executed evidence

RED was captured before implementation in scratch `verifier-red.txt`: 30 failing
subtests, including corrupted GEN_INHA passing under `-O`, altered parts passing,
and missing/malformed CSVs being silently regenerated. The initial root-level
suite invocation also had an unrelated calculations import error; running from
`hardware/powerboard-reva` resolves that invocation issue.

Final `python3 -m unittest discover -s tests -v` (from that directory): **8 tests
passed**, including 50 CLI subprocess runs across normal Python and `python -O`.
Controls cover all four required input files missing/empty/malformed; renamed
nets, altered endpoints/parts/references, duplicate nodes, missing endpoints,
extra empty nets, duplicate expected rows, altered ERC identities and totals.

Coverage 7.17.2, subprocess parallel coverage combined with path aliases for
scratch fixture copies: **108 statements, zero missed, 22 branches, one partial,
99% combined coverage**, `coverage report --fail-under=80` exit 0. The unexecuted
branch is importing rather than executing the CLI main guard. Reproduce using
`VERIFIER_COVERAGE=1 python3 -m unittest discover -s tests -v`, a coverage config
with `[run] branch = True` and `[paths]` mapping `*/board` to this directory,
then `python3 -m coverage combine` and `python3 -m coverage report -m`.

Real KiCad **9.0.9** was run against a scratch copy of the committed schematic,
without regeneration, at
`/home/c08r4d0r/.hermes/profiles/manager/cache/scratch/cycle-verifier-real`:

```
kicad-cli sch export netlist -o <scratch>/exports/powerboard-reva.net <scratch>/powerboard-reva.kicad_sch
kicad-cli sch erc --exit-code-violations -o <scratch>/exports/erc.rpt <scratch>/powerboard-reva.kicad_sch
```

Netlist export succeeded. ERC reported **3 violations, exit 5**. The checker
accepted the resulting evidence as `PARTIAL_NOT_SAFE_TO_ENERGIZE` with 84
components, 80 nets, 308 pin assignments and 3 ERC errors. This is the expected
failure of incomplete ERC, **not a passing release gate**. No error was fixed,
suppressed or approved here. `git diff --check` passed; generated circuit
artifacts remain unchanged. Parent review required before any default merge.
