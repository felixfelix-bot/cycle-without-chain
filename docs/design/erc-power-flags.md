# ERC power provenance: the ten PWR_FLAGs

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE`. This document records why ERC reports
**0 errors and 0 warnings** for the first time, and — more importantly — what
would make each flag wrong. It does not make the board safe to power.

Register effect: the ten `power_pin_not_driven` errors that had been carried
since the schematic was first generated are resolved, and the export verifier now
requires ERC to be **empty** rather than pinning those ten as an accepted state.

## 1. What the error actually meant

ERC raised `power_pin_not_driven` on ten nets. Each held only power-IN pins and
contained nothing KiCad counts as a power-OUT. That is not a statement that the
net is unsupplied — it is a statement that the *schematic* contains no symbol
asserting where the power comes from. For a net fed from a connector, through a
rectifier, through a 0 Ω link, or off a buck's switch pin, there is no such
symbol, which is exactly the case PWR_FLAG exists for.

The distinction matters because the two failure modes look identical in the
report:

- **Benign:** the rail is genuinely supplied, but by something that is not a
  power-OUT symbol. A flag is the correct annotation.
- **Real defect:** nothing supplies the rail. A flag would hide a dead circuit.

So each of the ten was traced to a source *before* a flag was placed. The
trace is recorded below, and a reviewer should be able to re-derive it from
`exports/powerboard-reva.net` alone.

## 2. The ten nets, traced

| Net | Traced source | Why ERC cannot see a driver | Flag justified? |
|---|---|---|---|
| `DC_LINK` | External pack via `J43` / `R116` / the inhibit FETs `Q400–Q403` | Enters at a connector; the pass elements are FETs, whose terminals are passive | yes |
| `CTRL_RAW` | `DC_LINK` → `D500` (S1J) → `CTRL_RAW` | A rectifier is a passive device, not a power-OUT | yes |
| `CTRL3V3` | `U500` (LM5164) SW → `L500` → `CTRL3V3` | The buck's SW pin is a switching output, not a power-OUT pin | yes |
| `DRIVE12` | `U501` (LM5164) SW → `L501` → `DRIVE12` | Same as above | yes |
| `LOGIC3V3_EXT` | `U502` (AP63203) — feedback tap on pin 1 | Pin 1 is FB, an input; the 3V3 arrives from the buck's own SW/L path and at the boundary connector `J2` | yes |
| `MCU_VDDA` | `LOGIC3V3_EXT` → `R67` (0 Ω analog link) | A 0 Ω resistor is passive; ERC does not propagate power provenance through it | yes |
| `MCU_VREF` | `U17` pin 36 (`VREF+`), plus `R68` 0 Ω | The MCU's internal reference output is not modelled as a power-OUT on the stock symbol | yes |
| `MAIN_SOURCE` | Floating common-source node of `Q400`/`Q401` | A FET source terminal is passive; this node deliberately floats and must never be PGND | yes |
| `PRE_SOURCE` | Floating common-source node of `Q402`/`Q403` | Same | yes |
| `PGND` | Single-point return / ground plane | A plane is not a symbol; every converter and connector returns here | yes |

Two of these deserve emphasis because they are the ones most likely to be
misflagged:

**`MAIN_SOURCE` and `PRE_SOURCE` are not supplies.** They are the floating
common-source nodes of back-to-back FET pairs. The schematic carries the note
"Common-source node floats: NEVER PGND". A PWR_FLAG here asserts *provenance* —
that the node is energised from the entry side through the FET bodies — and it
does **not** assert that the node is a safe reference. Anything reading these as
"this is a 3V3-style rail" would be badly wrong.

**`LOGIC3V3_EXT` is fed by `U502` in a way that looks like a backwards
connection.** `U502` pin 1 is on `LOGIC3V3_EXT`, and pin 1 is the AP63203's
**FB** pin (datasheet: 1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST). FB is an input to
the feedback divider, so this is correct — the divider taps the 3V3 rail. It was
checked against the datasheet specifically because a power net on an input pin
looks like a wiring error.

## 3. How the flags were added, and two defects met on the way

They are emitted by `generate_schematic.py` as real `power:PWR_FLAG` symbols with
`#FLGnnn` references, so they are non-physical and stay out of the BOM. Three
things went wrong before they landed, each worth recording:

1. **The flags were added to in-memory `Sheet` objects after those sheets had
   already written their files.** Each module's `populate()` calls `s.save()`, so
   a post-pass has to re-save every sheet it touches. The first attempt produced
   no flags on disk at all while reporting success.
2. **Duplicate references.** Numbering from a per-sheet item count produced
   `#FLG1` twice once flags spanned several sheets. Now a module-level counter.
3. **Off-grid endpoints.** Placing the symbol at a "nice" y coordinate such as
   268.0 mm is 0.84 mm off KiCad's 1.27 mm connection grid, which turned the ten
   errors into twenty `endpoint_off_grid` warnings. `pwr_flag()` now snaps its
   coordinates itself, so a caller cannot reintroduce this.

The sequence was: 10 errors → 0 errors / 20 warnings → 0 / 0.

## 4. What the verifier asserts now

`verify_exports.py` previously pinned the exact set of ten errors, with the note
"NOT waived". That was the right shape of guard: it prevented the findings from
quietly changing. It has been replaced with something stricter:

- ERC totals must be exactly `0 Errors 0 Warnings`.
- The issue-chunk list must be **empty** — no issue class may appear at all.
- Exactly **10** `#FLGnnn` symbols must exist. If a flag vanishes, the undriven
  errors return, so its presence is asserted rather than assumed.
- No `#` reference may appear in the BOM.

This keeps the original intent (findings cannot silently disappear) while
raising the bar (nothing may appear).

## 5. What this does NOT mean

- **Not a safety argument.** ERC is a connectivity and consistency check. A
  schematic with zero ERC findings can still be functionally wrong, and this one
  still has open functional gates: PROT-09 (dump resistor pulse rating), PROT-11
  (`f_chop` unchosen), RAIL-03 (L500 hot Isat), RAIL-16/17, PCB-02/04/05.
- **Not a layout argument.** No PCB exists. Nothing here says anything about
  copper, clearance, creepage or thermal performance.
- **Not a substitute for the bench.** The PWR_FLAGs assert where power is
  *intended* to come from. Whether it arrives, at what impedance, and whether
  the rails survive their loads are measurements that have not been made.
- **`MAIN_SOURCE` / `PRE_SOURCE` being flagged does not make them safe to
  touch.** They float at bus potential.
