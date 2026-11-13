> **STATUS: VERIFICATION RECORD — READ-ONLY MEASUREMENT OF THE SCHEMATIC.**
> This document reports what the generator and KiCad actually produce. It does not
> approve the design, and a matching count is not an engineering proof.
>
> **Baseline note:** every figure below was measured at `ae42054` and is retained
> as the *pre-change* baseline. Branch `pr/rail-ovp-pgood` adds the DRIVE12 OVP
> comparator, its divider and a new L501, so the current figures there are
> 387 components / 220 nets / 1142 pin assignments / 49 tests. The README quotes
> both sets and says which is which.

# Schematic figure verification

| Provenance | Value |
|---|---|
| Date | 2026-11-10 |
| Verified at | `master` `ae42054` (README figures introduced by `0f973ef`) |
| Method | Fresh clone, regenerate, then measure |
| Reproduce | see §4 |

## 0. Result

**Every figure in the README's schematic section reproduces.** This record exists
because the figures were quoted in a document written by a different worker at a
different commit, and a count that nobody re-measured is a claim, not a fact.

| README claim | Measured | Verdict |
|---|---|---|
| 32 pages | 32 | ✅ |
| 382 components | 382 | ✅ |
| 218 nets | 218 (nets with ≥2 component pins) | ✅ |
| 1129 connected pins | 1129 pin assignments | ✅ |
| 51 explicit NCs | 51 (single-pin nets) | ✅ |
| 45 hardware tests pass, also under `-O` | 45 pass, 45 pass | ✅ |
| Strict ERC 0 errors, 0 warnings, exit 0 | 0 errors, 0 warnings, exit 0 | ✅ |
| gate tests pass | 237 pass | ✅ (README said 198; the suite was 233 before the documented-command guard was added) |
| No `.kicad_pcb`, no routing, no Gerbers | none present | ✅ |

## 1. How each figure was measured

The numbers are not all the same kind of quantity, and two of them need care:

- **32 pages / 382 components / 1129 pin assignments** — printed by
  `generate_schematic.py` itself.
- **218 nets** — the netlist contains **269** nets in total, but **51** of those
  carry only one component pin. Counting only nets with two or more pins gives
  **218**. The README's "218 nets" and "51 explicit NCs" are therefore the same
  partition seen from both sides: 269 = 218 + 51. This is a self-consistent,
  non-arbitrary split, not a coincidence.
- **51 explicit NCs** — the single-pin nets, as above.
- **0 ERC errors / 0 warnings / exit 0** — `kicad-cli sch erc` reports none; the
  ten former undriven-supply findings were resolved by justified `PWR_FLAG`s
  violations, all severity `error`, all type `power_pin_not_driven` ("Input Power
  pin not driven by any Output Power pins") across 8 of the 32 sheets. `0 warnings`
  is accurate; it is not a hidden success.

## 2. What the ERC errors mean

All ten are the same class: a supply input pin with no driving power output. That
is characteristically what an unfitted or deliberately-inhibited supply net looks
like partway through a build, and this schematic is explicitly inhibited by design
— fitted 0 Ω ties hold every switch off without firmware. It does **not** mean the
board is nearly done.

They are recorded as **unresolved and unwaived**, which is the correct handling:
the export manifest itself stamps the design `PARTIAL_NOT_SAFE_TO_ENERGIZE` and
says "Ten known undriven supply errors remain unresolved, NOT waived."

A green ERC count is not the goal. A truthful one is.

## 3. Scope — what this does not verify

- **Not a DRC result.** There is no PCB, so there is nothing to DRC.
- **Not electrical safety, road legality or buildability.** Ten undriven supply
  pins and a schematic-only tree cannot be any of those.
- **Not the machine selection, storage or braking numbers.** Those live in
  `docs/design/` and the open-gates register.
- **Not stability over time.** These counts will drift as sheets are added. The
  README should be re-measured whenever the schematic changes; this record is a
  snapshot at `ae42054`.

## 4. Reproduce

```sh
git clone https://github.com/felixfelix-bot/cycle-without-chain.git
cd cycle-without-chain/hardware/powerboard-reva

# page, component and pin counts
python3 generate_schematic.py

# ERC — expect "Found 10 violations" and exit 5
kicad-cli sch erc --format json -o /tmp/erc.json powerboard-reva.kicad_sch
python3 -c "import json;d=json.load(open('/tmp/erc.json'));\
print(sum(len(s['violations']) for s in d['sheets']))"

# netlist, for the net and NC split
python3 export_artifacts.py
python3 - <<'EOF'
import re
t = open('exports/powerboard-reva.net', encoding='utf-8', errors='ignore').read()
blocks = re.split(r'\(net \(code', t)[1:]
nets = []
for b in blocks:
    refs = [r for r, _ in re.findall(r'\(node \(ref \"([^\"]+)\"\) \(pin \"([^\"]+)\"\)', b)]
    nets.append(len([r for r in refs if not r.startswith('#')]))
print("nets total:", len(nets))
print("nets with >=2 pins:", sum(1 for n in nets if n >= 2))
print("single-pin (NC) nets:", sum(1 for n in nets if n == 1))
EOF

# test suites
python3 -m unittest discover -s tests          # 45 baseline; 49 on pr/rail-ovp-pgood
python3 -O -m unittest discover -s tests       # same count, must not go vacuous
cd ../.. && python3 -m pytest tests/gates -q   # 237 tests
```

Observed timings: schematic generation a few minutes, the 45-test suite about
157 s normally and 190 s under `-O`, the gate suite about 14 s.

## 5. Why the gate suite has only one valid runner

`tests/gates` contains **221 test functions and zero `unittest.TestCase`
classes** — every test is a bare module-level function taking pytest fixtures
such as `tmp_path`. Consequently:

- `python3 -m pytest tests/gates -q` → **237 passed** (233 before the
  documented-command guard was added). This is the only valid route, and the
  only source for a gate count.
- `python3 -m unittest discover -s tests/gates` → **exit 0, `Ran 0 tests … OK`**.
  It reports success while grading nothing.

**The missing `__init__.py` is not the cause.** Adding
`tests/gates/__init__.py` leaves the count at zero, because unittest collects
`TestCase` subclasses, not bare functions. The earlier note in this repository
that attributed the no-op to a missing `__init__.py` was wrong about the
mechanism, though right that the command is vacuous.

This is also why the **198** figure survived: it was reproduced by a command that
could not have contradicted it. The correct count at `ae42054` and at master
`b31ba7e` is **233**.

The hardware suite is the opposite case: `hardware/powerboard-reva/tests` is
`unittest` throughout, so `python3 -m unittest discover -s tests` is correct
there — 45 at baseline, 49 on `pr/rail-ovp-pgood`.

**Rule:** quote gate counts from pytest and hardware counts from unittest. Never
infer one runner's coverage from the other's.
