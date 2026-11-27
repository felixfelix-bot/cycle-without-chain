# Bounded tooling audit: balloon-fresh → cycle-without-chain

Audit date: 2026-11-10. **Outcome: useful generator/CLI patterns, but no verified end-to-end PCB release gate to transplant.** This audit does not approve either project's hardware.

## Scope and provenance

- Read-only source: `/home/c08r4d0r/repos/balloon-fresh`, HEAD `2c05171da269862018f906f5aa0fde2648d76d8f`.
- Source tree was already dirty: deleted graphify cache/log/backup files and unrelated modified/untracked work. All inspected code and test inputs were read from `git show HEAD:<path>`, not the mutable working tree. No source files changed; no generators or routing loops were run there.
- Destination branch `pr/pcb-gates-audit`, worktree `/home/c08r4d0r/worktrees/cycle-pcb-gates-audit`, based on fetched `github/master` `c967d5b6c716c08b4f38f656493e9c5a2661fdcf`. Remote is named `github`, not `origin` (initial origin fetch failed harmlessly). Only this report and `pcb-quality-gates.md` are deliverables.
- KiCad CLI actually executed: **9.0.9**. Probe outputs are outside both repositories at `/home/c08r4d0r/.tmp/cycle-gates-audit` (the tool process's exported TMPDIR). They are diagnostic outputs, not a release package.
- Bounded inspection covered tracked hardware generators, relevant hardware filenames, the two root CI workflows and native export probes. No full firmware suite, exhaustive hardware revision audit, live CI status, fabrication order, visual review or independent design review was performed.

## What the actual code provides

Paths in this table are relative to the pinned balloon source revision, not to this destination repository.

| Area | Exact source | Observed implementation versus claim |
|---|---|---|
| SKiDL connectivity generation | `tracker/hardware/hub_board/hub_schematic.py`, lines 416–449; siblings `hub_schematic_f33.py`, `tracker/hardware/wing_board/wing_schematic.py` | Hub calls `generate_netlist(file_=...)`, writes `hub_board.net`. Header says “0 ERC errors (verified)” but the inspected hub file contains no executed `ERC()` call. A netlist generator is not a readable schematic or an ERC release gate. Existing `.erc` files are historical artifacts. |
| Native schematic generation | `tracker/hardware/schematics/v_c3_rp2040/build_sch.py`, `schematic_lib.py` | Native S-expression construction, explicit wires/labels/NC and pin-number mapping. `schematic_lib.py:9–10` uses deterministic UUID5; library paths at line 264 and build script line 16 contain `/home/c03rad0r/...`. Port path resolution, not absolute paths. Native generated file failed the fresh load probe below; no successful ERC proof. |
| PCB generation/routing | `tracker/hardware/gen_pcb.py`; `tracker/hardware/full_pipeline.py` | `gen_pcb.py:1059–1060` replaces placeholder UUIDs with UUID4, defeating byte reproducibility. Full pipeline builds board variants independently; no demonstrated schematic/PCB parity or BOM identity gate. Do not equate duplicated net definitions with independent verification. |
| DRC | `tracker/hardware/full_pipeline.py:1192–1215`, caller around 1340–1348 | Runs native JSON DRC, but missing output returns empty violation/unconnected arrays. Caller can announce “DRC CLEAN! Board is ready for fabrication.” Controlled failing subprocess reproduced those empty arrays. This is a fail-open defect; never port unchanged. Fixed default report path also admits stale-report reuse. |
| Pin/footprint inspection | `tracker/hardware/inspect_footprints.py` | Prints reference/value/XY/pad count and net-name sets; hardcoded board path. Does not prove pad-number-to-datasheet identity or equality with schematic. Useful inventory pattern only. |
| Manufacturing export | `tracker/hardware/full_pipeline.py:1220–1243` | Calls Gerber/drill CLI and prints stdout without enforcing return codes or expected file inventory. Layer list includes only outer copper; unsafe to copy to a multilayer design. |
| Misleading filename | `tracker/hardware/assembly/generate_gerbers.py` | 21-line assembly-text placeholder. It generates **no Gerbers**. |
| CI | `.github/workflows/test.yml`, `.github/workflows/ci-host-tests.yml` | First installs pytest/pyserial and runs `python -m pytest tests/ -v --tb=short`; second compiles firmware host suites. Neither explicitly runs KiCad ERC/DRC, PCB parity, BOM checks or manufacturing validation. No root hardware release workflow found. This is inspected workflow content, not a claim that CI currently passes. |
| Independent review, visual checks, BOM consistency | No dedicated enforced implementation established in bounded inspection | Historical reports/images/position CSVs are not proof of a frozen reviewed release. Keep these as explicit missing gates, not inferred successes. |

## Fresh execution results

Input copies came directly from pinned Git blobs:

| Input | SHA-256 |
|---|---|
| `tracker/hardware/output/v2_adc_fab_candidate.kicad_pcb` → `board.kicad_pcb` | `8c164dbaad80d3fa89860c60707b2e1dd2abb3bcb2a22d56ebe796e96acf4fa2` |
| `tracker/hardware/schematics/v_c3_rp2040/v_c3_rp2040.kicad_sch` → `schematic.kicad_sch` | `a7c5785fb0bb3363640ae9a7a62c764c80094c307d81848e033132e5aff83088` |

These are **different board variants**, selected to exercise tooling, not claimed to be a matched schematic/PCB pair or the current canonical balloon release. Project rules and local library tables were not copied: the DRC is an isolated parser/default-context probe, **not the authoritative board DRC score**. Zones were not refilled. No comparison with historical scores is warranted.

Commands actually run, with `OUT=/home/c08r4d0r/.tmp/cycle-gates-audit`:

```sh
kicad-cli version
kicad-cli sch erc --format json --exit-code-violations \
  -o "$OUT/erc.json" "$OUT/schematic.kicad_sch"
kicad-cli sch export netlist --format kicadxml \
  -o "$OUT/schematic.xml" "$OUT/schematic.kicad_sch"
kicad-cli pcb drc --format json --exit-code-violations \
  -o "$OUT/drc.json" "$OUT/board.kicad_pcb"
kicad-cli pcb export gerbers \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts \
  -o "$OUT/gerbers/" "$OUT/board.kicad_pcb"
kicad-cli pcb export drill --format excellon \
  -o "$OUT/gerbers/" "$OUT/board.kicad_pcb"
kicad-cli pcb export pos --format csv --units mm \
  -o "$OUT/positions.csv" "$OUT/board.kicad_pcb"
```

| Probe | Actual result |
|---|---|
| Native ERC | Exit **3**, “Failed to load schematic”; no ERC report. **NOT RUN**, not ERC-clean. Root cause not diagnosed within audit. |
| Native XML netlist export | Exit **3**, same load failure. Parity therefore **NOT RUN**. |
| Native DRC | Exit **5**; 100 violations and 3 unconnected items. JSON has an empty `schematic_parity` array but no paired schematic was loaded, so it proves no parity. |
| Gerbers | Exit **0**; nine layer files: `.gtl`, `.gbl`, `.gtp`, `.gbp`, `.gto`, `.gbo`, `.gts`, `.gbs`, `.gm1`, plus `.gbrjob`. Requested inner copper emitted no inner files. The input is not established as a four-layer release: inspect actual stackup and require the matching manifest. |
| Drill | Exit **0**, `board.drl`; this does not prove plated/nonplated classification or hole inventory. |
| Positions | Exit **0**, `positions.csv`; BOM/rotation parity not tested. |
| Fail-closed negative control | Extracted only `run_drc` AST from pinned code; substituted a subprocess returning exit 1 and a nonexistent output path. Function printed failure, then returned `{'violations': [], 'unconnected_items': []}`. This isolates a real code defect without running its router or touching source. |

The audit harness initially tried to read nonexistent `erc.json` and raised FileNotFoundError; remaining report inspection was rerun with the actual DRC file. That missing ERC report is precisely a blocked gate, not evidence of zero errors.

## Commands/patterns worth retaining, and gaps

**Proven to execute:** native KiCad version, DRC, Gerber, Excellon and position exports above. **Proven to fail on this input:** schematic ERC and XML export. **Not executed:** `python3 tracker/hardware/hub_board/hub_schematic.py` and `python3 tracker/hardware/schematics/v_c3_rp2040/build_sch.py` (write into source / absolute dependencies); full pipeline (mutating and unnecessary); graphical review; two-build reproduction.

There is no proven single command in this bounded source snapshot for schematic/PCB netlist equality, datasheet pin-map validation, BOM consistency, manufacturing inventory verification or independent review. Do not invent one. Add the three small fail-closed checkers described in [pcb-quality-gates.md](pcb-quality-gates.md), with red/green controls, after the project's canonical artifact names are fixed. Keep the generator, native schematic, PCB, rules, libraries and manufacturing outputs tied by hashes.

## Porting verdict

Retain explicit connectivity definitions, deterministic identifiers, native CLI exports and pad inventory. Reject hardcoded host paths, fail-open report handling, random UUID replacement, inner-layer-blind export lists and “fab-ready” labels derived solely from zero DRC counts. The motor board additionally needs hardware fail-safe proof, PM/body-diode generation paths, full-storage overvoltage/energy handling, phase-current sizing, switching-loop/Kelvin placement, DC interrupt ratings and tolerance/thermal validation. Sources and acceptance requirements are in the companion checklist. No framework was implemented and no default-branch merge is authorized by this audit.
