# Precharge budget revision — next draft sheet contract

**NO ENERGIZE / NO FAB / NO ROAD.** This revision removes two quantitatively impossible allocations; it does not qualify the unbuilt power supplies or claim complete single-fault protection. Shared hardware generators/netlist were not edited.

## Adopted bounded candidate

- **22 Ω ±1% PRE**, not 100 Ω. Independently enforced timer 300 ms nominal, 350 ms maximum including startup/proof; latch and no automatic hot retry. Hard-short bound is **54.807 J / 156.591 W** at 58.4 V and 21.78 Ω. The named RH050 candidate still needs mounted hot-pulse/repetition qualification, thermal interrupt and exact orderability verification. A stuck PRE can dissipate this power continuously; logic cannot interrupt a welded pair.
- **Pack → LM5164 → CTRL3V3**, no 12 V→3.3 V LDO cascade. Both TPSI3052 remain powered, 20k PXFR. 26 mA each is typical, **50 mA each is an acceptance requirement, not a guaranteed maximum**. Component ledger derives **0.8 W** pack input ceiling with assumed ≥60% efficiency. No relay coil.
- **Bus → LM5164 → SINK12**, retain R39 and independent safety chain. Physically gate bridge VM, external J5 and MCU/drive loads; reset alone is insufficient. Component ledger derives **1.1 W** early input ceiling, plus **0.04 W** direct HV/leakage load, and **2 W for at most 30 ms** startup. This replaces the consultant's preliminary 1.0 W with a reconciled total including **0.10 W low-voltage MAIN_PROVEN analog allowance** and 0.30 W input reserve. The OPA4197 candidate is powered by SINK12, not a nonexistent CTRL12.
- These are **testable envelopes**, not proven datasheet maxima. `analysis/precharge/power_budget.py` holds component terms and rounding. Source ledger, typical/max distinctions, minimum/preload load and pin connections: [power sources](precharge-power-sources.md). Its preliminary recommendation is superseded by this integrated total.
- Require source ≥3 A, source resistance ≤0.15 Ω for the demonstrated startup, assembled Cbus ≤1.5 mF, and 36–58.4 V. More impedance/capacitance or a source current clamp needs rerun and requalification. At 1 V mismatch, high-tolerance PRE and 10k bleed leave **1.442 W at 36 V / 2.236 W at 58.4 V**. Against 1.14 W total early load this leaves **0.302 / 1.096 W** steady headroom. No allocation increase was made without changing R and fault timeout.

## Startup/sequence actually exercised

Sink UVLO corner used: 17.36 V on / 16.13 V off; source-backed intervals and CTRL 30 V nominal UVLO divider are in the ledger. At 36 V, even maximum CTRL rise threshold 31.59 V leaves about 4.4 V before diode/wiring allowance. Converter PGOOD, output tolerance and TPSI startup still must be qualified. Early sink startup is explicitly loaded in the simulation, not omitted. No guaranteed chopper readiness time follows from converter soft-start alone.

Model sequence: 20 ms check → PRE → 20 ms stable <1 V mismatch → MAIN commanded with 20 ms PRE overlap → PRE off, 40 ms diagnostic pulse → RUN if measurement prerequisites valid and mismatch <0.30 V. Global timeout covers PRE and proof. Gate-establishment and PRE turnoff are modeled as bounded contracts, not transistor switching simulation. A real sheet must establish those maxima and add the specified post-proof settle before drive enable; model currently enables drive immediately after proof, conservatively stressing supply startup but not validating that settle logic.

Executed high-R corner, source limit 3 A, C=1.5 mF:

| Pack | dt µs | MAIN command s | PRE resistor J |
|---|---:|---:|---:|
| 36 V | 50 / 25 / 12.5 | .218900 / .218950 / .2190125 | 1.019655 / 1.019279 / 1.019147 |
| 58.4 V | 50 / 25 / 12.5 | .206150 / .206225 / .2062625 | 2.626295 / 2.625261 / 2.624868 |

All six reach RUN and have exactly one sink start. Proof ends about 60 ms after MAIN command, before the 300 ms nominal timeout. MAIN closing peak is source-clipped near 3 A in this fixture: the physical system must provide that limit or qualify unclipped closing current/SOA. This model does not create a current limiter. Full figures: `analysis/precharge/budget-corners.json`.

## Real MAIN_PROVEN rather than an oracle

[MAIN_PROVEN candidate](main-proven-candidate.md) specifies 330 Ω/40 ms known switched load, current-valid LOW→HIGH→LOW observation, pack/bus difference amplifier and ±0.5 V comparator window, with ≤0.20 V bus-referred uncertainty. Exact OPA4197/TLV1702 pins and existing entry-net anchors are listed there. With revised **21.78 Ω stuck PRE**, worst modeled failed-open MAIN mismatch is **1.128 V**; subtract 0.10 V source excursion leaves 0.328 V above the 0.70 V rejection edge. This is an analytical discrimination bound, not implemented circuitry.

External/PM injection must independently be bounded ≤10 mA; otherwise status is **indeterminate**. Pulse missing, current feedback stuck, missing gate validity, sensor disagreement or power invalid cannot qualify. Floating gate monitor, reference/network, current-window implementation and bipolar clamps still need exact selected parts. An off-state bypass response is not uniquely a weld, and a forward test cannot establish both-polarity isolation of a single-short FET.

`welded` now controls only the physical bypass fixture; `off_path_alarm` is an explicit external measured input. `gate_valid`, `pm_quiet_valid` and `diagnostic_load_valid` are also explicit **unimplemented interface inputs**, not claims of detection. A failed-open main is exercised electrically by removing its conduction and observing diagnostic droop. Model checks final mismatch only; 5 ms continuous-window/current-edge hardware behavior remains to implement/test. The old 16 tests and exact original model remain as `legacy_model.py` regression controls, clearly separate from eight new candidate tests.

## Evidence and next actual sheet

`budget-red.log`: observed old 0.1 W assertion failure; two new-interface errors also recorded, not represented as behavioral RED. `budget-green.log`: **24 tests OK, 10.528 s**; optimized **24 OK, 13.390 s**. New tests cover both voltage/R corners, energy balance (<4 mJ residual), timestep convergence, short timeout, inadequate source/excess load, failed-open MAIN, invalid measurement prerequisites and stuck-PRE analytical separation. Historical controls are not evidence for all new state logic. No vendor electrical transient, complete sensor fault injection or bench validation exists.

**Sufficient to start the next draft power/measurement sheet; not sufficient to release it.** Use exact LM5164/TPSI3052 connections in power-sources §2 and analog pin map/entry attachments in MAIN_PROVEN §§1–2. Before sheet acceptance: close buck magnetics/RON/ripple and capacitor bias/tolerance; source/UVLO/min-load tests; enforce load-domain segregation and signal backfeed protection; select protected bipolar sensing and reference networks; implement gate/current monitors and reset-dominant state/timer truth table; prove 350 ms maximum; reject stuck sensors, weak source, PM ambiguity and PRE failure; qualify resistor pulses, MOSFET SOA and actual clamp transients. BOM new prices remain blank; inherited quotes remain historical unverified observations.

**Sink availability is conditional:** bus/supply wiring, converter or safety rail can fail. It is not an independent energy source. Full single-fault qualification, independent protective path/mechanical PM envelope and loss-of-sink mitigation remain open. No 1 Wh gyro or other feature expansion is included.
