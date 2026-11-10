# Independent precharge review — 2026-11-10

> Numerical budgets superseded by [budget revision](precharge-budget-revision.md); original values below retained as review history.

**Verdict: publishable screening proposal, NOT ready for a released pin-level schematic specification. NO ENERGIZE / NO FAB / NO qualified SOA claim.** Reviewed feature `37751668474e5e425e1ebf27d0bdab6dc4827783`, merged onto fetched default `aebd795`. No circuit files changed; FSR owner retains circuit ownership. This review supersedes stronger readiness/price language in the original proposal.

## Electrical architecture

Common-source N-channel pairs with drains at the two external endpoints are correctly oriented: body diodes run from the shared sources toward their respective drains. Off-state opposing diodes block either endpoint polarity; enhanced channels allow both traction and regeneration. With pack −58.4 V and bus +58.4 V, one device can see nearly **116.8 V**, not half that voltage. A 150 V rating leaves only **33.2 V static headroom**; this is not evidence against inductive overshoot, unequal switching, avalanche or Miller turn-on. Device clamps, gate protection, driver floating-node stress, creepage, measured loop R/L and current remain required. Opening the pack does not stop a spinning PM machine rectifying through bridge diodes.

Three power domains are a reasonable candidate, not a closed architecture. **0.10 W sink standby is a blocking hypothesis:** existing R39 alone consumes 12²/1000 = **0.144 W output**, before reference/comparator/driver and conversion losses. Reusing the unmodified AUX12V rail fails this allocation. Moving R39 is not enough: budget every bias/load/startup charge and preserve the autonomous overvoltage reference. At Vbus=57.4 V, 100 ohm ideal branch provides 0.574 W; bleed consumes 0.329476 W, leaving 0.244524 W. Including 0.15 ohm source resistance reduces the surplus to about 0.243664 W. This ceiling is not a measured auxiliary budget.

Before pack closure the bus sink must handle PM generation independently of the pack controller. After closure it must handle source charge refusal; after isolation or CTRL loss it must still handle uncontrolled PM generation. Missing CHARGE_ALLOWED/DISCHARGE_ALLOWED must default false, but no real implementation or latency is proved. An enhanced pair cannot enforce discharge-only current. At 940 uF, 15→60 V gives only **42.3 ms at 1 A / 2.82 ms at 15 A**. Converter soft-start alone does not bound total comparator/reference/gate-driver readiness. Sink power loss is an unmitigated hazard until an independent protective path and mechanical operating envelope are specified.

## TPSI3052 pin-level constraints from primary documentation

[TI SLVSGS3B](https://www.ti.com/lit/ds/symlink/tpsi3052.pdf), Table 5-1, §§8.3, 9.2–9.3:

| DWZ pin | Required assignment/constraint |
|---|---|
| 1 EN | MAIN_CMD or PRE_CMD; hardware pull-down; inhibit until primary supply valid; prevent independent EN back-powering VDDP |
| 2 PXFR | Selected 1% resistor to VSSP; sampled at power-up, not a dynamic power-control input |
| 3 VDDP | CTRL3V3; three-wire operating range 3–5.5 V; local 1 uF parallel 100 nF to VSSP |
| 4 VSSP | PGND, primary reference |
| 5 VSSS | Corresponding pair's common-source node, NEVER PGND |
| 6 VDDM | Midpoint of secondary capacitor divider |
| 7 VDDH | CDIV1 to VDDM; secondary supply rail |
| 8 VDRV | Separate gate-series resistors to both gates; loads referenced to VSSS |

CDIV2 connects VDDM–VSSS and must be at least 3×CDIV1, same capacitor type/tolerance, using effective capacitance under bias/temperature. Size for **both** MOSFET gate charges: CDIV1=(n+1)/n × QLOAD/allowable droop, CDIV2=n×CDIV1, n≥3. Larger caps increase cold-start time. Select PXFR using continuous bleeder/leakage and gate-charge recovery; two 100k gate resistors consume about 4.5 mW per driven pair at 15 V. Seven PXFR resistor settings span 7.32k–20k. Two drivers at the 20k setting's **26 mA typical each** consume **0.624 W from a 12 V-fed LDO**, already above the proposed 0.5 W pack-controller allocation before buck losses or sequencer load. Lower settings may work but require actual sizing and worst-case budget; typical figures are not limits.

Use **TPSI3052**, not TPSI3052S (2.5 us typical one-shot). Normal EN propagation assumes secondary rails established, not cold start. Supply-loss timeout is **300 us typical**, not an established worst-case kill latency. Qualify startup, brownout and stored gate-charge removal. Commercial device provides **basic isolation** (3000 Vrms/60 s; 1000 Vrms working), not reinforced insulation or traction galvanic disconnect. Preserve PCB isolation boundaries. Driver isolation does not protect every sense/GPIO path.

## Independent model verification

Original 13 tests executed: normal **13 OK, 5.355 s**, `-O` **13 OK, 9.850 s**. Regenerated model stdout agrees with recorded cases. Added three independent controls in `analysis/precharge/tests/test_review_controls.py`; final normal **16 OK, 14.759 s**, optimized **16 OK, 9.778 s**. Commands from `analysis/precharge`: `python3 -m unittest discover -s tests`, repeated with `python3 -O`.

| dt | ideal close s | normal resistor J | 1 ohm fault resistor J |
|---|---:|---:|---:|
| 50 us | 0.852450 | 2.602694828 | 49.336145643 |
| 25 us | 0.852525 | 2.602495103 | 49.336145622 |
| 12.5 us | 0.852575 | 2.602391692 | 49.336145612 |

Parameters verified: 58.4 V, 1500 uF, Rpre=100 ohm, Rsource=0.15 ohm, Rbleed=10k, allocated sink=0.1 W above 15 V, main R=0.012 ohm, external assumed source/charge clips 15/2 A, controller allocation 0.5 W. PRE starts at 20 ms; timeout is absolute 1.5 s, hence **1.48 s energized**, not 1.5 s after PRE starts. Short bus stays below 15 V, disabling modeled sink standby. Real worst timeout/component tolerance still requires the separate conservative 1.7 s envelope (~57.98 J at ideal 58.4²/100 W). These energies do not qualify RH050 mounting, repetition or pulse survival.

Independent controls remove sink/bleed for a pre-MAIN unloaded RC case: V=Vs(1−exp(−t/RC)), Eseries=CVs²(1−exp(−2t/RC))/2, and source energy Vs×C×V must equal capacitor energy plus both resistor losses within 0.3 mJ at 12.5 us. A separate closed-form short calculation uses Rload=1 ohm || 10k, tau=C/(1/Rseries+1/Rload), I=a+b exp(−t/tau), integrated I²Rpre for 1.48 s; agreement within 10 uJ. These controls validate limited solver math/energy accounting, not every switched trajectory. Three-step sensitivity also covers PM no-pack peak voltage; dump hysteresis gives timestep-dependent ripple, not a guaranteed 60 V clamp.

**0.852 s is an ideal state transition, not switching proof.** The model immediately replaces PRE by MAIN, has no real gate dynamics, no overlap until MAIN_PROVEN, and no failed-open diagnostic stimulus. The proposed circuit demands those features but the model does not implement them. `welded=True` is an oracle. Reverse-pack cases suppress current by software `valid`, rather than solving body diodes and pin clamps; they cannot verify reverse electrical safety. Charge refusal has ideal instantaneous opening, with no actual overcharge impulse or gate-delay calculation. No vendor transistor/converter model or transient SOA proof exists.

## Price evidence correction

Historical quotes dated **2026-11-10**, currency claimed **USD**, quantities: 4 MOSFETs ×6.864 +2 drivers ×5.24 +2 buck ICs ×4.97 = **47.876 USD**. Arithmetic is correct; this is a **partial historical quote subtotal, not a verified purchasable basket or complete system cost**. Live direct distributor retrieval was blocked/timeout or did not expose tiers. Indexed corroboration is not checkout verification.

Original driver URL was for automotive **S** variant; original buck URL was automotive Q1 rather than stated DDAR. BOM URLs corrected to exact [TPSI3052DWZR](https://www.digikey.com/en/products/detail/texas-instruments/TPSI3052DWZR/19236307) and [LM5164DDAR](https://digikey.com/en/products/detail/texas-instruments/LM5164DDAR/10434708). $5.24 appeared only in a related-item card with quantity unresolved; $4.97 is indexed qty1 DDAR (not Q1). [Arrow IRFP4568](https://arrow.com/en/products/irfp4568pbf/infineon-technologies-ag) did not expose $6.864 or quantity tier and labelled the product obsolete: lifecycle/availability must be resolved. Relay $108.11 is indexed, exact quantity/currency table unconfirmed. No guaranteed stock, taxes, shipping or assembly. Third supply, magnetics, capacitors, sensing, protection, thermal cutoff and optional independent disconnect remain outside subtotal. Do not order from these observations.

## Blocking deliverables for the next schematic owner

1. Freeze input/bus extrema, battery/source R/L and fault current, PM current/speed envelope, capacitance tolerance, charge acceptance and allowable turnoff impulse.
2. Close three-domain steady/startup/worst-temperature budgets. Either prove ≤0.10 W sink and controller allocation or reselect precharge R/time/threshold/supply architecture. Choose driver PXFR/CDIV and verify cold-start/UVLO/power-loss timings.
3. Produce complete pin-numbered analog state logic, reset/latch truth table, protected bipolar pack/bus sensing and worst-case divider/reference/offset drift budget. A 40 mV scaled 1 V window is not already accurate enough.
4. Specify real MAIN_PROVEN and off-state diagnostics with injected electrical test stimulus and discrimination from independently PM-driven/precharged bus. Enumerate false-ready/stuck-input/failed-open/short cases; no oracle or voltage-match-only assurance.
5. Specify precharge overlap, timeout maximum, independent thermal interrupt and hot-retry prevention; select rated fuse/clamp components. Qualify resistor mounted fault energy and hot repetition. Qualify MOSFET switching/interrupt SOA at measured minimum R and maximum L/temperature.
6. Prove autonomous sink startup and power-loss strategy before and after pack isolation, including missing-pack PM cold start; complete dump thermal envelope and physical disconnect assumptions.

Until these parameters and circuits exist, the next artifact may be a **draft pin-level design for review**, not a release-ready schematic or hardware authorization.
