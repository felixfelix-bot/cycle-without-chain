# `tools/gates` — fail-closed PCB release checks

Three small checkers plus a runner. They exist because the tooling audit
([`docs/design/tooling-audit-report.md`](../../docs/design/tooling-audit-report.md))
found the upstream pipeline reporting **success for work it had not done**:

* DRC returned `{'violations': [], 'unconnected_items': []}` even when the
  `kicad-cli` subprocess failed or the report file never appeared, and the
  caller then printed "DRC CLEAN! Board is ready for fabrication";
* the DRC report path was fixed, so a report from an earlier run could be
  graded as this one;
* `assembly/generate_gerbers.py` was a 21-line placeholder that produced no
  Gerbers, and the export wrapper ignored return codes and never compared
  requested layers with files on disk;
* a requested four-layer export emitted only outer copper with exit code 0.

`docs/design/pcb-quality-gates.md` proposes these three checkers. This package
implements them.

## Status contract

Every tool prints **one JSON object on stdout** and human-readable detail on
stderr, and exits with:

| exit | verdict     | meaning |
|------|-------------|---------|
| 0    | `PASS`      | every check the gate knows how to make was made, and passed |
| 1    | `FAIL`      | the gate ran and the artifact did not survive it |
| 2    | `NOT RUN`   | the gate could not grade anything: bad arguments, missing/unreadable input, unusable manifest, missing tool |

`NOT RUN` is a failure for a release decision. It is a separate code only so
that "we did not check" never gets confused with "we checked and it failed" —
never so that it can be ignored.

Everything is driven through the real CLI surface, so `argparse` never calls
`sys.exit` behind the JSON: a usage error is raised, caught and reported as
`NOT RUN`. No module uses `assert`, so the suite behaves identically under
`python3 -O`.

## The gates

### 1. `native_reports` — fail-closed KiCad export/DRC/ERC runner

```sh
python3 -m tools.gates.native_reports \
    --kind drc --input board.kicad_pcb --outdir /tmp/gates --kicad-cli kicad-cli

python3 -m tools.gates.native_reports \
    --kind erc --input root.kicad_sch --outdir /tmp/gates --kicad-cli kicad-cli

python3 -m tools.gates.native_reports \
    --kind netlist --input root.kicad_sch --outdir /tmp/gates --kicad-cli kicad-cli
```

`--severity-all` widens DRC/ERC to warnings; the default is errors only.
`--timeout` (default 900 s) and `--min-objects` (default 1) are explicit so a
caller has to *say* it wants something unusual.

Reported as `FAIL`, never as a pass:

| condition | check name |
|---|---|
| nonzero subprocess exit, even with an empty violation list | `subprocess_exit` |
| timeout | `subprocess_completed` |
| report file absent, empty, or written to a different path | `report_present` |
| report is not JSON / XML, or truncated | `report_parseable` |
| required keys missing, or wrong types | `report_structure` |
| report names a different source file than the input | `report_source_matches_input` |
| zero pads / symbols / netlist nodes graded | `objects_scanned` |
| any violation | `no_violations` |
| any unconnected item (DRC) | `no_unconnected` |
| an ERC report covering no sheet | `report_covers_sheets` |

**No stale report can be graded.** Each run allocates a fresh directory
`<outdir>/<UTC>-<pid>-<random>/` with `exist_ok=False` and writes the report
there, so a leftover `drc.json` at the legacy fixed path is neither read nor
overwritten. Object counts come from the input artifact itself (`(pad `,
`(symbol (lib_id "`, netlist nodes), not from the report: a zero-violation
report over zero objects is a pass over nothing.

For `--kind erc` on a hierarchical schematic, symbols are counted across every
`*.kicad_sch` beside the root sheet, because a hierarchical root file holds
sheet instances and no symbols of its own.

### 2. `netlist_parity` — exact schematic-to-netlist set comparison

```sh
python3 -m tools.gates.netlist_parity \
    --netlist out/schematic.xml --expected docs/expected-connectivity.json
```

Expected map, either spelling:

```json
{"nets": {"VIN": [["J1", "1"], ["C1", "1"]], "GND": [["J1", "2"]]},
 "nc":   [["U1", "3"]]}
```

```json
{"endpoints": [["J1", "1", "VIN"], ["C1", "1", "VIN"]], "nc": [["U1", "3"]]}
```

Semantics are set equality over normalised `(reference, pin, net)` triples —
never counts, because a gate/source swap keeps the count identical. A net
declared with `[]` must still exist, which catches a net that vanished while
its endpoints moved elsewhere. The gate also fails on:

* any pin on more than one net (`duplicate_free`, printed as `SHORT:`);
* any `(ref, pin)` listed twice inside one net;
* a pin listed in `nc` that is in fact connected (`nc_respected`);
* an empty netlist (`non_empty`), unless `--allow-empty` is passed.

A malformed or self-contradictory expected map (not JSON, no `nets`/
`endpoints`, duplicate rows, a pin both connected and `nc`) is `NOT RUN`,
because the gate cannot tell which side is wrong. The `diffs` object in the
JSON lists every missing and extra endpoint and every missing/extra net name;
stderr prints the same as `missing:` / `extra:` lines.

KiCad's auto-generated `unconnected-(REF-PadN)` nets are ignored by default —
no expected map can enumerate them. `--include-unconnected` compares them too.
`--require-net NAME` (repeatable) pins a specific net's existence.

### 3. `release_manifest` — manufacturing artifact inventory

```sh
python3 -m tools.gates.release_manifest \
    --manifest docs/release-manifest.json --artifacts out/gerbers/
```

Manifest:

```json
{"board": "board.kicad_pcb",
 "copper_layers": 4,
 "artifacts": [
   {"name": "F.Cu",   "kind": "copper",  "match": "*-F_Cu.gtl"},
   {"name": "In1.Cu", "kind": "copper",  "match": "*-In1_Cu.gbr"},
   {"name": "In2.Cu", "kind": "copper",  "match": "*-In2_Cu.gbr"},
   {"name": "B.Cu",   "kind": "copper",  "match": "*-B_Cu.gbl"},
   {"name": "Edge.Cuts", "kind": "outline", "match": "*-Edge_Cuts.gm1"},
   {"name": "drill",  "kind": "drill",   "match": "*.drl"},
   {"name": "job",    "kind": "job",     "match": "*.gbrjob"},
   {"name": "schematic", "kind": "document", "match": "*.pdf"}
 ]}
```

`kind` is one of `copper`, `mask`, `silk`, `paste`, `outline`, `drill`, `job`,
`document`, `other`. The manifest must declare at least one `copper`, one
`outline` and one `drill` entry, and `copper_layers` (if present) must equal
the number of copper entries — a self-contradictory manifest is `NOT RUN`, not
a verdict. Per-entry `min_bytes` overrides the per-kind floor.

Fails on: a declared artifact with no matching file (`missing`); more than one
file matching one entry (`ambiguous`); zero-byte (`empty`); a file below the
size floor (`suspiciously_small`); placeholder text (`TODO`, `placeholder`,
`not implemented`, …) or missing structural markers — Gerber needs `%FSL…%`,
`%MO…%`, an aperture and a final `M02*`; Excellon needs `M48`, `METRIC`/`INCH`,
a tool definition, coordinates and `M30`; a PDF needs `%PDF-` and `%%EOF`
(`placeholder_or_invalid`); a file no entry claims (`unexpected`, unless
`--allow-unexpected`). **A requested inner copper layer with no file is a hard
failure** — `copper_layers_complete` and `copper_layer_manifest` — which is
exactly the defect the audit found in the four-layer export.

Every matched artifact's SHA-256 is recorded in `evidence.hashes`.

### 4. `run_all_gates.py`

```sh
python3 tools/gates/run_all_gates.py --list

python3 tools/gates/run_all_gates.py \
  --gate native_reports --native-kind drc \
  --native-input out/board.kicad_pcb --native-outdir /tmp/gates --kicad-cli kicad-cli \
  --gate netlist_parity --netlist out/schematic.xml --expected out/expected.json \
  --gate release_manifest --manifest out/manifest.json --artifacts out/gerbers \
  --json-out /tmp/gates/aggregate.json
```

Runs each gate as a subprocess (a crash or hang in one cannot affect the
others) and returns `0` only if every selected gate returned `PASS` with exit
code 0. A gate that self-reports `PASS` while exiting nonzero is downgraded to
`FAIL`. `--skip GATE` removes a gate. Selecting a gate without its inputs is
`NOT RUN`, so a half-configured invocation cannot look like a pass.

## Tests

```sh
python3 -m pytest tests/gates -q
python3 -O -m pytest tests/gates -q      # must be identical
```

`tests/gates/gate_support.py` builds structurally real fixtures and a **real
executable fake `kicad-cli`** driven by a JSON spec, so every failure mode
(exit code, no file, truncated report, wrong output path, timeout, second
run) is exercised across a genuine subprocess boundary rather than by mocking
the gate's internals.

Negative controls, one per failure class — each asserts a nonzero exit *and*
the specific failing check:

* nonzero exit with an empty violation list (the audit's exact defect);
* nonzero exit with no report at all; zero exit with no report;
* report written to the wrong path; report left over from an earlier run;
* truncated report, wrong-typed report, missing keys, report for another board;
* zero objects scanned (empty board, pad-less board, symbol-less schematic,
  netless netlist, ERC covering no sheet);
* mutated expected endpoint (a swap that keeps the endpoint count identical);
  missing and extra endpoints; renamed, missing and extra nets; a pin shorted
  across two nets; the same pin twice in one net; an `nc` pin that is connected;
* placeholder Gerber, truncated Gerber, missing format spec, tiny-but-valid
  Gerber, empty drill, truncated drill, non-PDF and truncated PDF, deleted
  artifact, four-layer manifest with only two copper files, duplicate match,
  unclaimed file;
* invocation errors: zero arguments, wrong argument count, extra positional,
  missing input, unreadable input, input-is-a-directory, missing tool,
  non-executable tool, outdir-is-a-file, `--min-objects 0`, non-positive
  timeout, unknown gate, unparsable flag.

## What a PASS proves, and what it does not

**A PASS proves, for the exact bytes hashed in the run's `evidence` block:**

* `native_reports`: the tool existed, ran, exited 0 within the timeout, wrote
  a fresh report that parses, has the expected shape, names this input, and
  reported zero violations over a nonzero number of objects counted from the
  artifact itself.
* `netlist_parity`: the netlist's `(ref, pin, net)` set is *exactly* the
  expected set, with no duplicates, no pin on two nets, and every declared net
  present.
* `release_manifest`: every declared layer/artifact exists, is a single
  unambiguous match, is above the size floor, and has the structural markers of
  its format; every file in the directory is accounted for; every copper layer
  the manifest claims has a file.

**A PASS does not prove:**

* that the copper is electrically correct, that clearances are adequate for
  58.4 V, or that the stackup and copper weight are what you ordered;
* that the schematic is right — `netlist_parity` proves the netlist matches the
  *expected map*, which is only as good as that map. A wrong generator and a
  matching wrong expectation pass together;
* that pad numbers match manufacturer pin tables, that footprint pad geometry
  is correct, or that a footprint's pin 1 orientation is right;
* that the outline is closed, that drill holes are correctly plated, that drill
  registration is right, or that vias are the size you think;
* that the Gerber is one a CAM tool will accept as-is, or that a fab will build
  it — the structural checks are a floor, not a CAM review;
* that the BOM, CPL, side/orientation or DNP population match (not implemented
  here; gate G2 in `pcb-quality-gates.md`);
* anything about inductance, current capacity, thermal behaviour, EMI, fault
  response or safety. DRC cannot certify any of that;
* that the run is reproducible — two clean builds have not been compared;
* the *current* state of a board if the artifact was not rebuilt from the
  schematic under review. Hash the schematic, rules, libraries and outputs and
  tie them together (`pcb-quality-gates.md`, G0/G7/G8).

Nothing here authorises fabrication, energising, or riding. The design
documents' own verdict stands: this board is a partial engineering review, not
a release design.

## Real-tool evidence

The probe below was run **outside both repositories**, on copies, with KiCad
CLI 9.0.9 — and it changed the code, which is the point of running it:

```
# copied hardware/powerboard-reva/*.kicad_sch + .kicad_pro to a scratch dir outside the repo
python3 -m tools.gates.native_reports --kind erc \
    --input <scratch>/powerboard-reva.kicad_sch --outdir <scratch>/gates --kicad-cli kicad-cli
```

Result: `FAIL`, `violations: 9`, `exit_code: 5`, 30 sheets covered,
354 symbols counted. The first version of this gate counted symbols only in
the file named on the command line, which is a hierarchical root sheet holding
no symbols of its own — so it reported `0 graded objects` for a populated
design. The probe caught it; the hierarchy-wide count and the
`report_covers_sheets` check are the fix. A DRC probe on the audit's balloon
board copy likewise returned `FAIL` with 100 violations and 3 unconnected
items over 65 pads, matching the audit's own numbers.

Neither probe approves the board: the schematic ERC has 9 violations and the
DRC input is a balloon variant, not this project's release candidate.

## Adding a fourth gate

1. Write the failing test in `tests/gates/` first, including a negative
   control that *must* fail.
2. Import `Checks`, `StrictParser`, `guard`, `finish`, `UsageError` and
   `require_inputs` from `tools/gates/_common.py`; wrap `main` with `guard`.
3. Count the objects you graded from the artifact, not from the tool's report.
4. Add it to `GATES` in `run_all_gates.py` and to its argument group.
5. Keep it under ~350 lines and keep the exit-code contract.
