> **STATUS: DC SCREENING BUDGET — NOT A LOGIC-INTEGRITY RELEASE.**
> This closes the arithmetic the register said was missing. It does not qualify
> behaviour with a rail absent or ramping, edge rates, metastability, or noise.
> Nothing here was measured.

# PROT-03: per-path logic-level budget

## 1. What the gate asked for, and what changed

The register's PROT-03 evidence is a list of driver limits plus two complaints:

> LM339B VOL 400 mV at 25 °C and 550 mV over −40…85 °C at 4 mA, BAT54WS 0.32 V at
> 1 mA, DRV nFAULT 0.125 V, TPS382x 0.4 V, HC thresholds specified only at 2/4.5/6 V
> … else a Schmitt or interface stage

Both complaints are **stale against the schematic now in the tree**:

1. **The series diodes are gone from the fault bus.** The sheet is named
   `fault-interfaces` and its on-sheet text reads *"LVC Schmitt fault inputs
   without series diode offsets."* The BAT54WS parts that remain are in
   `brake_intent_circuit.py` and `fsr_circuit.py` as analog clamps, not in the
   fault path. So the previously quoted **0.445 V** (nFAULT + diode) and
   **0.72 V** (supervisor + diode) sums do not describe this design.
2. **The logic is LVC, not HC.** Fitted parts are SN74LVC1G74, SN74LVC3G17
   (Schmitt buffer), SN74LVC1G11, SN74LVC1G04. *"HC thresholds specified only at
   2/4.5/6 V"* no longer applies to anything on the fault bus.

The gate offered a choice — *per-path budget, else a Schmitt or interface stage* —
and the design already took the second option. What had never been done is the
arithmetic showing the chosen interface holds at the corner. That is this
document.

## 2. Per-path low-level budget

Receiver limits use the **pessimistic** column: an LVC Schmitt input is only
guaranteed to read low below **VT− minimum**, and a non-Schmitt input below
**VIL/VIN_L minimum**. Budget run at SAFETY3V3 minimum of **3.168 V** (nominal
3.3 V less an assumed 4 % tolerance — an assumption, not a regulator datasheet
limit).

| Path | Driver VOL max | Receiver low limit | Sink | Margin |
|---|---:|---:|---:|---:|
| `ANALOG_OK` → U11 1A (Schmitt) | 0.550 V | 0.84 V | 0.67 mA | **290 mV** |
| `GEN_nFAULT` → U11 2A (Schmitt) | 0.125 V | 0.84 V | 0.32 mA | 715 mV |
| `HUB_nFAULT` → U12 1A (Schmitt) | 0.125 V | 0.84 V | 0.32 mA | 715 mV |
| `WD_RESET_N` → U11 3A (Schmitt) | 0.400 V | 0.84 V | 0.32 mA | 440 mV |
| `OV_CMD` → U10 IN+ (not Schmitt) | 0.550 V | 1.00 V | 3.17 mA | 450 mV |

**All five paths pass on DC low level at the cold corner.** The tightest is
`ANALOG_OK` at **290 mV**.

That path is the tightest for a specific reason worth naming: `ANALOG_OK` and
`OV_CMD` share the same 550 mV LM339B driver limit, and `ANALOG_OK` loses only
because its receiver limit (0.84 V LVC VT− min) is *lower* than the UCC27511's
1.00 V. It is not a weaker driver; it is a stricter receiver.

**`OV_CMD` matters most** even though it is not the tightest: it drives the brake
chopper, and it is the only path whose receiver is not a Schmitt input.

## 3. High-level budget

Open drain released; the pullup must lift the node above the receiver's
high-threshold *maximum*, with only leakage drop across the pullup
(LM339B IOH leakage 50 nA max):

| Path | Receiver high limit | Margin |
|---|---:|---:|
| `ANALOG_OK` → LVC3G17 | 1.87 V (VT+ max) | 1298 mV |
| `OV_CMD` → UCC27511 | 2.40 V (VIN_H max) | 768 mV |

## 4. Datasheet limits used, and one attribution trap

Every limit was fetched as a primary PDF for this audit:

- **LM339B VOL max 550 mV**, ISINK ≤ 4 mA, VID = −1 V, TA = −40…+85 °C
  (TI `lm339b`, §6.7 "Electrical Characteristics for LM339B").
- **DRV8353 nFAULT VOL max 125 mV at IO = 5 mA** (SLVSDY6A, open-drain outputs).
- **TPS3823-33 RESET VOL max 0.4 V at IOL = 1.2 mA**.
- **SN74LVC3G17**, VCC = 3 V: VT− **0.84–1.14 V**, VT+ 1.5–1.87 V (SCES470F),
  identical over −40…85 °C and −40…125 °C columns.
- **UCC27511**: VIN_L **1.0–1.2 V**, VIN_H **2.2–2.4 V**.
- **SN74LVC1G11**, VCC = 3–3.6 V: VIH min 2 V, VIL max 0.8 V (SCES487I).

**Attribution trap, recorded because it nearly produced a wrong conclusion:** the
same LM339B datasheet contains a **700 mV** full-range VOL row in §6.10, which is
the table for the legacy **LMx39/LMx39A**, *not* the LM339B. Reading 700 mV as the
LM339B limit would have overstated the pessimistic bound and misattributed the
part. 550 mV is correct for U6. A test asserts this so the confusion cannot
silently return.

## 5. What this does not close

1. **Supply-absent and ramping behaviour.** PROT-04 remains open. An LVC input
   with its rail missing is a different problem from a DC level on a live rail,
   and `Ioff` covers some paths but not all.
2. **Edge rate and metastability.** An LVC Schmitt has hysteresis but no
   guaranteed outcome for arbitrarily slow edges crossing the threshold. The
   fault bus has off-board capacitance, so this is a real timing question.
3. **The 4 % rail tolerance is assumed.** No SAFETY3V3 regulator tolerance is
   established here; if it is worse, every margin above shrinks proportionally.
4. **290 mV is a DC number at 25 °C.** Aging, contamination, injected noise and
   ground bounce all erode it, and none is quantified. It is not "290 mV of
   comfort".
5. **Nothing measured.** Every figure is a datasheet limit applied to a
   schematic; no board exists.

## 6. Consequence for the gate

The gate's stated bar was *"per-path budget with temperature, sink current and
leakage, else a Schmitt or interface stage."* Both halves are now satisfied for
the fault bus: the Schmitt stage is fitted, and the per-path budget exists and
passes at the corner.

That is still not a closure, because the gate's risk statement is *"VOL-plus-diode
sums above the logic low threshold at a cold or low-supply corner"* — and while
the diode sums are gone, "low-supply corner" is only covered to an **assumed** 4 %
and no edge-rate or absent-rail case is examined. PROT-03 therefore stays **OPEN**
with the DC arithmetic complete, and the remaining exposure narrowed to the four
items in §5.

## 7. Reproduce

```sh
python3 analysis/cx/logic_margins.py
python3 -m unittest analysis.cx.test_logic_margins   # 18 tests
```
