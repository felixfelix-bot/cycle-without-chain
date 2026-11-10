# Rail partition review: recoverable and honest, not energizable

> **STATUS: ENGINEERING REVIEW OF AN UNSAFE PROTOTYPE.** Reviewed `d944978`
> on `pr/rail-partition` merged with `c8c4d5f`. No bench measurement, no
> fabrication, no authorization to remove inhibits.

## Verdict

The pushed branch is **internally consistent, reproducible and honest**. It does
not fabricate hardware, does not suppress ERC, does not use `PWR_FLAG` to hide an
undriven rail, does not loosen an existing assertion, and its sink rail is
genuinely independent of the delayed drive rail.

It is **not safe to energize**, and four of the gaps below were *unlisted* by the
milestone document rather than owned by it. Two of those are now fixed in this
branch; two remain design work.

## Independently reproduced

| Check | Result |
|---|---|
| Hardware suite | **45 tests OK** normal, **45 OK** under `python3 -O` |
| Fail-closed gates | `pytest tests/gates` → **198 passed**, normal and `-O` |
| Generator fidelity | `generate_schematic.py` reproduces committed `.net` **byte-identical** |
| Native export | `kicad-cli sch export netlist --format kicadxml` reproduces `ctrl-supply.xml` (382 components, 218 nets) |
| Strict ERC | **exit 5, 10 errors, 0 warnings** (master had 9); no waiver, no pin-type falsification |
| Gate on ERC | `tools/gates/native_reports --kind erc` → **exit 1 FAIL** (`subprocess_exit`, `no_violations`) |

The tenth error is `U1 pin 3 [VM]` undriven on `DRIVE12` — `L501` is a passive
inductor between `DRIVE_SW` and `DRIVE12`, so ERC cannot see a power source.
That is an honest artifact of the topology, not a suppressed defect.

## Verified structurally

- **Sink independent of drive.** `U3.1 = DC_LINK`, `U3.3 = SINK12`; SINK12 members
  are `U3.3, U4.2, U6.3, U10.1, R39/R40/R46, C23/C27/C38/C39`. No path from
  `DRIVE12`. Sink startup does not depend on the delayed rail.
- **Inhibits retained.** `R402`/`R412` 0 Ω on `MAIN_EN`/`PRE_EN` are byte-unchanged
  from master; `R519` 0 Ω holds `MAIN_PROVEN_IN` low; `R516`/`R517` keep
  `MCU3V3_EN` low. Default state is off without firmware.
- **No fabricated main-proof hardware.** Zero matches for
  `OPA4197|TLV1702|RDIAG|QDIAG|DIAG_CMD|GATE_VALID|MATCH_OK|PM_QUIET` anywhere in
  the BOM, pin map or netlist. Only the `R518`/`R519` inhibit network exists.
- **Budgets genuinely separate.** `ctrl_separate_pack_input_cap_w = 0.8` is not
  folded into `sink_input_screening_w`; `R520` (1.815 mW at the CTRL input) is
  charged to CTRL only, and `U510` sits on `SAFETY3V3` (sink side).

## Defects found

### 1. DRV8353 `IVDRAIN` was missing from the budget — FIXED here

`U1.4`/`U2.4` remain on `DC_LINK` (always bus-connected) even though their `VM`
pins moved to delayed `DRIVE12`. TI SLVSDV2 gives **`IVDRAIN` 1.9 mA typ / 4 mA
max** per device at `VVM = VVDRAIN = 48 V, ENABLE = 3.3 V, INHx/INLx = 0 V`.

- 2 devices × 4 mA × 58.4 V = **0.467 W** always-on direct-bus load
- versus the entire `SINK12` subtotal of **0.203 W**
- versus the 0.10 W `PROOF_ALLOWANCE` and the small "leakage" allocation it was
  previously filed under

This load bypasses the sink rail completely, so the 1.1 W sink envelope never
bounded it. `rail_budget.py` now carries an explicit `DC_LINK` row derived from
the datasheet, reports `direct_bus_always_w`, and the self-test fails under both
normal and `-O` execution if that row is removed.

### 2. `rail_budget.py --self-test` was vacuous under `-O` — FIXED here

The self-test used bare `assert`. With the `SINK12` expectation corrupted:

```
python3 rail_budget_mut.py --self-test        → rc=1   (correct)
python3 -O rail_budget_mut.py --self-test     → rc=0   "self-test: PASS"  (vacuous)
```

`assert` is stripped under `-O`, so the milestone's "self-test PASS" claim did not
survive the interpreter flag the project also tests under. All checks now raise
`RuntimeError` through a `_check()` helper. Re-proved with the same mutation:
`rc=1` under `-O`, and a second control that zeroes the new VDRAIN row also fails
under `-O`.

### 3. No output OVP on `U501` — OPEN, design work

LM5164 provides UVLO and thermal shutdown only; the cached datasheet has no
output overvoltage protection. If `R512` (FB lower leg) opens, `FB` floats to
`VOUT` and `DRIVE12` rises toward `VIN` — up to **58.4 V** — against:

- `AP63203` absolute maximum **35 V DC / 40 V (400 ms)** — 1.67× over
- `C513`/`C514`/`C517` rated **25 V**
- `U1`/`U2` `VM` absolute maximum 80 V — survive

One resistor open destroys `U502` and over-volts three capacitors. A clamp, a
second FB divider leg, or a converter with integrated OVP is required.

### 4. `L501` unqualified against the converter's own current limit — OPEN

`MSS1246T-683MLC`: `Isat` **2.26 A** (10 % drop), `Irms` **1.30 A** (20 °C rise),
DCR 0.167 Ω. LM5164 peak current limit is **1.25/1.50/1.75 A**, so the top limit
is **1.35× Irms** and 0.77× `Isat`; I²R at that current is 0.51 W. The milestone
flags `L502`'s 2 A part but says nothing about `L501`, which is the more loaded
inductor.

### 5. `ANALOG_OK` is hard-coupled to a delayed rail — OPEN, needs a decision

`U501.6` `PGOOD` (open drain, `R51` 4k7 pullup to `SAFETY3V3`) joins `U6`'s three
open collectors on `ANALOG_OK`, which drives `U11 → ANALOG_CLEAN → U13 →
FAULTS_OK → HEALTHY`. With `DRIVE12` unpowered, `PGOOD` holds `ANALOG_OK` low, so
an *always-on* safety chain is gated by a *delayed* rail's power-good.

The direction is fail-safe, but it contradicts the stated independence of the
safety domain. This must be an explicit recorded decision — either move `PGOOD`
off the always-on chain, or state that a healthy verdict requires the drive
domain and justify why that cannot mask a sink-side fault.

### 6. Documentation self-contradiction on OC supplies — FIXED here

The milestone's Outcome paragraph claimed all independent safety loads remain
downstream of `SINK12`/`SAFETY3V3`. Verified in the netlist: `U18-U23.8`
(TLV3202) and both OC reference ladders sit on **`LOGIC3V3_EXT`** — downstream of
the delayed `DRIVE12` cascade — and only the `OC_OK` pullup is on `SAFETY3V3`.
The later OC-supply note already said this correctly; the Outcome paragraph now
matches it instead of contradicting it.

### 7. `R39` is 71 % of always-on `SINK12` output — OWNED, quantified

12.0 mA of 16.92 mA. It exists to hold `U3` above the `R-78HB` minimum load;
removing it without replacing the load pushes the module to its minimum-load
boundary. The `η = 0.60` assumption is conservative against the datasheet's
89–94 % at full load, but light-load efficiency at ≈4 % of rating is **not** the
93 % headline. Break-even efficiency is **η ≥ 0.5453**:

```
sink_out   = 0.203055 + 0.133210 + 0.10 = 0.436265 W
available  = 1.1 W - 0.30 W reserve      = 0.80 W
break-even = 0.436265 / 0.80             = 0.5453
```

So the 60 % assumption carries only a 5.5-point margin, and it is an assumption.

### 8. Two export artifacts are not cross-checked — OPEN, low risk

`verify_exports.py` reads the s-expression `.net`; `test_rail_partition.py` and
`test_ctrl_supply.py` read `ctrl-supply.xml`. Injecting an intra-rail split
(`L501.1` onto both `DRIVE_SW` and `SINK12`) into the **XML only** leaves
`verify_exports` green, while the same injection into **`.net`** fails correctly
with "duplicate endpoint". Both usually come from one export, so practical risk is
low, but the XML side is not structurally verified. The fail-closed
`netlist_parity` gate now on `master` closes this class if it is run against both.

## What this review does NOT establish

No thermal measurement, no start-up sequencing on hardware, no effective
capacitance under DC bias, no EMI, no hot-plug or reverse-polarity test, no
loss-of-sink behavior, no main-switch conduction proof, no fused coordination
check, no pulse/SOA qualification. Every one of those remains open, and the
present netlist must not be energized on the strength of this document.

## Reproduction

```sh
cd hardware/powerboard-reva
python3 -m unittest discover -s tests              # 45 tests
python3 -O -m unittest discover -s tests           # 45 tests, must also pass

python3 analysis/precharge/rail_budget.py --self-test
python3 -O analysis/precharge/rail_budget.py --self-test   # must not go vacuous

python3 -m pytest tests/gates -q                   # 198 passed
python3 -m tools.gates.native_reports --kind erc ...        # exits 1 on 10 errors
```
