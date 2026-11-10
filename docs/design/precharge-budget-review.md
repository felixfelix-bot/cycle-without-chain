# Independent precharge-budget review and circuit-writer handoff

**Decision: accept as a bounded next-draft design input, not hardware approval. NO ENERGIZE / NO FAB / NO ROAD.** Reviewed feature `342221da4e40e386d99ce4a1cc672cf4690b730a` merged onto default `22ae0f4`, 2026-11-10. No hardware generator, schematic, netlist or keys were modified. Legibility work must finish before the circuit writer edits its generators.

## Independent checks

Read the budget revision, power-source ledger, MAIN_PROVEN candidate, model and all tests. The current exported netlist hash is `8ef35725e7109ad0a5a2cb25153137c878b2afcf9a946f5e3f1342cc9cb1ef88` (FSR export 14:42:23), newer than the consultant's recorded export. Rechecked AUX12V, SAFETY3V3 and DC_LINK connectivity: U1/U2 VM remain on AUX12V; J5.1 remains on SAFETY3V3; R39/R40/R46 and U4/U6/U10 still consume early power. U1/U2 VDRAIN, bridge drains and multiple capacitors remain bus-connected. The proposed partition is **not in this netlist**. The FSR/nav additions do not authorize early-rail external loading.

Re-downloaded TI [TPSI3052](https://www.ti.com/lit/ds/symlink/tpsi3052.pdf), [TLV760](https://www.ti.com/lit/ds/symlink/tlv760.pdf), and [LM339](https://www.ti.com/lit/ds/symlink/lm339.pdf) primary PDFs and extracted their tables. Confirmed TPSI3052 26 mA **typical** at 3.3 V/20k (not maximum), TLV760 ground current 2 mA typical/5 mA maximum under the specified no-load conditions, LM339B 0.8 mA typical at 5 V and 1.6 mA maximum at 36 V over the stated temperature range. These test conditions do not manufacture guarantees at other supplies or loads.

Recomputed `power_budget.py`: CTRL rail allowance **0.36102 W**; `/0.60 + 0.10 = 0.70170 W`, rounded upward to **0.8 W** input. SINK rail allowance including proof analog **0.435055 W**; `/0.60 + 0.30 = 1.025092 W`, rounded to **1.1 W**, plus **0.04 W** direct bus leakage and separately modeled bleed. The old ledger's 1 W recommendation is historical; the integrated 1.1 W controls. R39 alone is 0.144 W at nominal 12 V. Resistor/output tolerance, switching loads and backfeed require closure; nominal sums are not maxima. **60% efficiency, 50 mA per TPSI3052, 6 mA safety output, 0.10 W analog and 2 W/30 ms startup remain acceptance requirements, not measurements.** Direct buck magnetics, ripple and actual input power must establish them.

Independent fault arithmetic: `58.4²/21.78 = 156.591368 W`; for 350 ms, **54.806979 J**. This conservative zero-source-impedance bound does not rely on simulation or a source current clamp. It is valid only for a pulse actually interrupted within 350 ms; a welded PRE requires a different independent interrupt/thermal solution.

MAIN_PROVEN closed form with 36 V pack, initial bus 37 V, 1.5 mF, 334.5 ohm stimulus, 21.78 ohm stuck PRE, 10 mA injection gives **1.128216 V** mismatch at 38 ms. Subtract 0.10 V pack movement and compare against the 0.70 V worst rejection edge: **0.328216 V** margin. At 33 ms (start of the final 5 ms for the shortest pulse), mismatch is **0.974530 V**, still 0.174530 V beyond that edge after excursion allowance. This is conditional discrimination, not a completed tolerance proof: ±0.01% effective networks, reference, clamps, common-mode, saturation recovery, drift and total ≤0.20 V uncertainty are still unclosed. Healthy-path bound is about 0.117 V at 0.50 ohm and specified test load, below the 0.30 V guaranteed-pass region.

## Executed numerical evidence

Commands, from repository root:

```sh
PYTHONPATH=analysis/precharge python3 -m unittest discover -s analysis/precharge/tests -v
PYTHONPATH=analysis/precharge python3 -O -m unittest discover -s analysis/precharge/tests -v
```

**24/24 passed**, normal 12.754 s and optimized 13.289 s. Six independently rerun high-R (22.22 ohm), 3 A-source, 1.5 mF corners:

| Pack | dt µs | MAIN command s | PRE J | source − series − bleed − load − capacitor, J |
|---|---:|---:|---:|---:|
| 36 | 50 | .218900 | 1.019655 | −.00056810 |
| 36 | 25 | .218950 | 1.019279 | −.00021366 |
| 36 | 12.5 | .2190125 | 1.019147 | −.00003642 |
| 58.4 | 50 | .206150 | 2.626295 | −.00178675 |
| 58.4 | 25 | .206225 | 2.625261 | −.00085319 |
| 58.4 | 12.5 | .2062625 | 2.624868 | −.00038685 |

Timing and PRE energy converge; residuals are below 4 mJ in these fixtures. Do not generalize this residual to short/regen/dump fixtures: their energy channels are not all included in this expression, and the ideal current clip can absorb unreported power. Tests include 16 historical controls against `legacy_model.py`, not 24 new-circuit behavioral proofs. Current model assumes gate establishment, instantaneous PRE-off and static prerequisite flags; it checks final voltage, not continuous comparator/current-edge logic, and has no post-proof AUX settle. The six runs do not verify those missing mechanisms.

## Required next sheet, after legibility handoff

1. Implement direct pack CTRL3V3 buck and autonomous bus SINK12 buck from the pin contracts in [power sources](precharge-power-sources.md). Retain independent sink safety loads. Physically gate bridge VM, MCU and external loads; audit every signal/VDRAIN backfeed path. Count all input capacitors, including disabled converters. Preserve FSR/navigation interfaces without letting them defeat early-power limits.
2. Implement 22 ohm PRE with independently bounded 300 ms nominal/350 ms maximum timer, reset-dominant fault latch, no automatic hot retry, and a physical response to welded PRE. Select actual hot-pulse-qualified resistor and interrupt hardware; headline wattage is insufficient.
3. Implement [MAIN_PROVEN](main-proven-candidate.md) Kelvin voltage sensing, protected precision network, reference, 330 ohm diagnostic branch, 1 ohm current sense and LOW→HIGH→LOW current-valid test. Select exact parts/pins for reference, current window, floating gate/secondary monitors, clamps and diagnostic switch/protection. A TPSI3052 EN command is not feedback.
4. Establish bounded MAIN gate-settle, PRE turnoff and 38–42 ms stimulus; require final 5 ms continuous valid window, then **20 ms post-proof AUX settle**. Global timeout covers all qualification intervals. Reset/brownout/fault wins over every state transition. Supply-valid and comparator startup states cannot be trusted by default.
5. Replace `PM_QUIET_VALID` with a physically justified interlock or independent measurement. For initial isolated fixtures, physically disconnect both PM sources and external bus sources. For an integrated machine, specify independent motion/source-current evidence and its fault detection to establish **total injection ≤10 mA throughout proof**. Gate-off/PWM-off does not stop PM body-diode rectification. If the bound cannot be established, status is INDETERMINATE and drive stays disabled; do not wire this input permanently true.

## Exact release blockers (all remain open)

- **Actual source and capacitance:** identify source/BMS and assembled capacitance; verify 36–58.4 V, ≥3 A available startup, ≤0.15 ohm demonstrated-source impedance, ≤1.5 mF actual total with tolerances. These are model input requirements, not user-granted facts. A source stronger than 3 A is not a 3 A limiter: qualify actual MAIN closing current/SOA or implement a characterized limit. Confirm proof-time ≤0.10 V excursion and ≤0.50 ohm total path.
- **Supply/load realization:** complete buck design, output tolerances, minimum-load/UVLO/startup/temperature tests and measured end-to-end 0.8/1.1 W limits; prove 2 W/30 ms startup bound, leakage and load isolation. Additional sensors/monitors consume budget too. Active braking/chopper gate-charge demand and loss-of-sink behavior are separate gates.
- **Observable proof:** exact precision BOM and error corners; independent gate/current/PM validity, stuck-sensor detection, current-edge and continuous-window tests. No boolean input or voltage-match oracle is hardware evidence. Forward proof cannot establish both-polarity isolation or rated-current capacity.
- **Timing and faults:** implement and test reset-dominant truth table and all supply-loss timings, absolute timeout, AUX settle, failed-open MAIN, stuck PRE, full/single-FET shorts, missing diagnostic load, stuck comparators and external injection. Bound diagnostic stuck-on (~11 W at 60 V), not merely its 0.463 J normal pulse.
- **Physical energy safety:** mounted hot ≥54.807 J fault pulse/repetition qualification, independent interrupt, actual MOSFET SOA and clamp transients, PM energy envelope and independent loss-of-sink mitigation. A schematic/document/model pass cannot close these gates.

No numerical defect requiring a model change was found within this bounded review. Integration means the documented candidate and its explicit limits are available on default, never that hardware is proven safe.
