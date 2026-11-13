# Pad-level audit of the power semiconductors (PCB-02)

STATUS: `PARTIAL_NOT_SAFE_TO_ENERGIZE`. This document audits pin-to-pad truth and
gate-drive sizing for the power parts that can be verified from primary
datasheets. It does not make the board safe to power, and it does not close
PCB-02 for the parts listed as unaudited in §4.

Register gate: **PCB-02 — Pin and pad truth.** Previously OPEN with the note
"only DRV8353 and CSD19532Q5B were audited so far".

## 1. Method

For each part: read the manufacturer datasheet's pin assignment, compare it to
the pin map in the circuit module, and compare the declared land pattern to the
footprint that actually exists in the KiCad library. Where the part drives another
part, the gate-drive numbers are checked in both directions.

A pin map is only "audited" here if the datasheet pin table was read in this
session. Parts whose datasheet could not be retrieved are listed in §4 and stay
unaudited — they are not inferred from series family resemblance, because a pin
map is exactly the kind of claim that family resemblance gets wrong.

## 2. Verified in this audit

### 2.1 IRFP4568PbF — the dump/entry MOSFETs (6 devices: Q400–Q405)

Read from Infineon PD‑96175 (8 pages, retrieved and parsed).

| Property | Datasheet value | Source |
|---|---|---|
| Package | TO‑247AC | PD‑96175 p1 |
| Pin assignment | **G = 1, D = 2, S = 3** | PD‑96175 pin drawing |
| V_DSS | 150 V | p1 |
| R_DS(on) | 4.8 mΩ typ, 5.9 mΩ max | p1 |
| I_D (silicon limited) | 171 A @ 25 °C | p1 |
| Q_g total | **151 nC typ, 227 nC max** @ I_D 103 A, V_DS 75 V | p1 characteristics |
| Q_gs / Q_gd | 52 nC / 55 nC | p1 |
| C_iss | **10.47 nF** | p1 |

The circuit module's pin map (`{'1':gate,'2':drain,'3':src}`) **matches** the
datasheet. The symbol used is `Q_NMOS_GDS`, whose pin order is gate-drain-source,
so symbol pin numbers and package pins agree — this is the check that would
otherwise silently swap drain and source on a 150 V part.

Land pattern: `Package_TO_SOT_THT:TO-247-3_Vertical` exists in the KiCad library
and is a 3-lead TO-247 vertical. Verified present, not verified against
Infineon's own recommended land (the datasheet does not publish one for
TO-247AC; it publishes a mounting-hole and torque spec instead — 6-32 or M3 screw,
mounting torque per p1). **This is a real gap**: the land is a library default,
not a vendor drawing. TO-247 is a through-hole package with a single row of
2.54 mm-spaced leads, so the risk is low, but it is not the same standard as the
L501 land in `bom-identity-and-gate-sizing.md`, which was transcribed from the
vendor catalogue.

### 2.2 TPSI3052DWZR — the isolated gate drivers (2 devices: U400, U401)

Read from TI SLVSGS3B (Rev. B).

| Property | Datasheet value |
|---|---|
| Pin 1 | EN |
| Pin 2 | PXFR |
| Pin 3 | VDDP |
| Pin 4 | VSSP (primary-side return) |
| Pin 5 | VSSS (secondary-side return) |
| Pin 6 | VDDM |
| Pin 7 | VDDH |
| Pin 8 | VDRV |

The circuit module maps pins 1–8 as
`[EN, PXFR, CTRL3V3, PGND, src, mid, hi, out]`, i.e. **pin 4 VSSP → PGND** and
**pin 5 VSSS → the FET source node**. That is correct in intent: VSSP is the
primary-side ground and VSSS is the secondary-side reference, which must sit at
the common-source node of the back-to-back pair (the module's own note says the
"Common-source node floats: NEVER PGND", which this mapping respects).

**Pin map matches.** The one thing not verified is whether the two `CDIV`
capacitors meet the datasheet's stated requirement, see §3.2.

Declared footprint `Package_SO:SOIC-8_5.3x5.3mm_P1.27mm`: this name exists in the
KiCad library. It was previously written as `5.23x5.23mm`, which does **not**
exist and raised an ERC `footprint_link_issues` warning. Corrected.

**Open:** the DWZ package designation should be checked against TI's package
outline drawing for the exact body width (5.3 mm is a library assumption, not a
reading of the TI drawing). A 0.07 mm error is inside the land tolerance but it
is not verified.

### 2.3 CSD19532Q5B and DRV8353S — previously audited

Both were audited before this document; their records stand and are not
re-audited here. The gate-resistor sizing for that pair is in
`bom-identity-and-gate-sizing.md` §3.

## 3. Gate-drive sizing — two different pairs, two different answers

This is the substantive finding of the audit. The same resistor value `3R3` sits
on twelve gate resistors, but they belong to **two electrically different
circuits**, and I had derived 3.3 Ω for only one of them.

### 3.1 The bridge pair: CSD19532Q5B driven by DRV8353S

See `bom-identity-and-gate-sizing.md` §3. Summary: Qg 48 nC, Ciss 4.7 nF, driver
1 A source with 1.5 Ω internal; 3.3 Ω gives a 60 ns edge, RC-dominated by 1.25×,
0.87 V/ns, 0.94 W per device.

### 3.2 The entry pair: IRFP4568PbF driven by TPSI3052

Completely different numbers. Qg is **3.1×** larger and Ciss is **2.2×** larger,
against a driver with 1.5 A source (vs 1 A) but **2.5 Ω** internal resistance
(vs 1.5 Ω) and a 15 V gate drive (vs 10 V).

Using TI's own formula from SLVSGS3B §9.2.2.6:

```
I_O+ = min(1.5 A, V_VDDH / (R_DSON_VDRV + R_GSRC + R_GFET_INT))
     = min(1.5 A, 15.1 V / (2.5 + 3.3 + 0))
     = min(1.5 A, 2.60 A) = 1.5 A          (driver is the limiter)
t_limit = Qg / I_O+     = 151 nC / 1.5 A  = 100.7 ns
t_RC    = 2.2 * R_total * Ciss
        = 2.2 * 5.8 Ω * 10.47 nF          = 133.6 ns
t_sw    = max(t_limit, t_RC)              = 133.6 ns   (RC-dominated)
```

Worst case with Qg at its 227 nC maximum: t_limit = 151 ns, still below t_RC, so
the edge remains RC-dominated and the resistor is doing real work. **3.3 Ω is
therefore valid for this pair as well** — but by coincidence of the trade, not
because it was derived for it. That distinction is recorded rather than smoothed
over.

The value was already `3R3` on these four resistors before the audit; the audit
changed the *justification*, not the number.

### 3.3 CDIV and bypass — CORRECTION: the design meets both, my earlier claim was wrong

Earlier revisions of this section recorded two "requirements the design does not
meet". **Both claims were wrong.** They are corrected here, with the arithmetic
in `size_cdiv_bypass.py` and 17 tests.

**(a) The CDIV ratio — I misread a minimum as a target.**

SLVSGS3B §6.3 note 2 states `CDIV2 >= 3 × CDIV1`. That is a **floor**, not a
setpoint. The design's 470 nF / 100 nF = **4.7×** therefore *complies*; I had
written it down as a violation by treating "should be at least three times" as
"should be three times". Both absolute windows are also satisfied:

| | design | datasheet window | result |
|---|---|---|---|
| CDIV1 (VDDH–VDDM) | 100 nF | 4 nF … 15 µF | in range, 25× above min |
| CDIV2 (VDDM–VSSS) | 470 nF | 12 nF … 40 µF | in range, 39× above min |
| CDIV2/CDIV1 | 4.70 | ≥ 3.0 | **met** |

The structural reason the ratio is a floor: CDIV1 spans the full 15 V VDDH rail
while CDIV2 sits across VDDM, so a ≥3:1 split keeps one node from sagging first.

**(b) The bypass — I compared against the wrong capacitance.**

TI recommends bypass of "20 times the equivalent gate capacitance". Ciss for the
IRFP4568PbF is 10.47 nF, so **≈ 209 nF** is wanted. The design has CDIV1 + CDIV2
= **570 nF** across the secondary rails, which meets it. My error was comparing
the 209 nF requirement against CDIV1 (100 nF) alone, which made the finding look
real — the node has both capacitors across it.

**(c) The charge budget, which neither of the above addressed.**

Two things actually needed checking and had not been:

```
droop per edge = Qg / C
  Qg 151 nC typ, both caps : 0.265 V
  Qg 227 nC max, both caps : 0.398 V
  Qg 151 nC, CDIV1 alone   : 1.510 V   (conservative case)
headroom to VDDH UVLO (15.0 V -> 10.9 V worst case) : 4.1 V
```

Even the conservative CDIV1-only case leaves ~2.7 edges of margin, and the
design uses **RPXFR = 20 kΩ, the 93.3 % duty setting** — the highest of the seven
power-transfer levels in Table 8‑1 — so the converter replaces each edge's charge
long before the next. A bike power switch toggles at human rates (a few Hz at
most), not at the kilohertz this would matter at.

**Verdict: no change to CDIV1 or CDIV2 is required.** The values were correct; the
audit that said otherwise was not.

## 4. Still unaudited — and why that is not a formality

- **LM5164DDAR** (buck) — declared footprint `HSOP-8-1EP_..._EP2.3x2.3mm` was a
  name I invented (`..._EP3.9x4.9mm_P1.27mm` without the EP suffix). Corrected
  to an existing library footprint, but the **pin map has not been read** from
  the TI datasheet, and the exposed-pad dimensions have not been matched to the
  device.
- **STPS30100ST** (reverse clamp) — footprint corrected to `Diode_SMD:TO-277A`,
  pin map unread.
- **UCC27511DBVR**, **TLV1701AIDBVR**, **TPS3823**, **LM339B**, **SN74LVC1G\***,
  **TMUX1511PWR**, **OPA333**, **AP63203WU**, **R-78HB12-0.5** — logic-level and
  housekeeping parts. Their *logic* levels were audited in PROT-03 and PROT-07,
  but that is a different question from pin-to-pad truth. **None of them has had
  a pin-level audit.**
- **STM32G474VET6** — the register notes that the full datasheet was only
  reachable through a text proxy. LQFP-100 pin map unverified.
- **S1J-E3/61T**, **BAT54S**, **PESD3V3U1UL**, **2N7002** — small-signal and
  clamp parts, MPN and package plausible, pin maps unread.

## 5. What this closes and what it does not

**Improved, not closed.** Two of the three parts that actually switch power
(IRFP4568PbF, TPSI3052DWZR) now have a datasheet-read pin map, and the gate-drive
sizing for the entry pair is derived rather than inherited. PCB-02 stays **OPEN**
because:

- TO-247 land pattern is a library default, not a vendor drawing
- the DWZ body width is a library assumption
- eleven housekeeping devices have no pin-level audit
- ~~two TPSI3052 datasheet requirements are not met~~ — **withdrawn**: both
  claims were wrong, see §3.3. The CDIV values and bypass meet the datasheet.

Claiming PCB-02 closed on this evidence would repeat the error recorded in
`bom-identity-and-gate-sizing.md` §4.5, where a gate was declared closed on a
check that did not examine the thing it claimed to verify.

## 6. Reproducing

Datasheets were retrieved and parsed locally; the hashes belong in
`datasheet-sources.json` alongside the existing entries:

- IRFP4568PbF — Infineon PD‑96175, 8 pages
- TPSI3052 — TI SLVSGS3B Rev. B

Gate-drive arithmetic for both pairs is in `size_gate_resistors.py` (bridge pair)
and §3.2 above (entry pair, TI's formula quoted).

```
cd hardware/powerboard-reva
python3 size_gate_resistors.py
python3 -m pytest tests/ -q
```
