> **STATUS: PRIMARY-DATASHEET REVIEW — IMPLEMENTABLE LOW-VOLTAGE CANDIDATE, NOT HARDWARE QUALIFICATION.**

# FSR electrical evidence and corrected connection proposal

2026-11-10; worktree `cycle-fsr-circuit`, base `1da7575`. Read first: [frontend evaluation](fsr-frontend-evaluation.md). This document supersedes the electrical proposals below where they differ; it does not change the schematic, BOM, brake circuit, or earlier evaluation file. No hardware or SPICE tests performed. Calculations below were exercised with Python; datasheet PDFs were retrieved and TI tables checked with layout-preserving `pdftotext`.

## Decision summary

1. **Interlink 34-00018 is confirmed:** Model 402 **Short Tail**, female contacts **and housing**, 12.70 mm active diameter, nominal thickness 0.46 mm. It is not the solder-tab version (34-00015). The housing's exact mating connector/retention/waterproofing is not established by this evidence; do not invent a compatible connector MPN.
2. **The suspicion that TMUX1511 lacks powered-off protection is refuted.** TI SCDS390B explicitly specifies it. Retain **TMUX1511PWR** for bounded 0–3.6 V off-state signals. This is not battery-fault isolation and does not prove an unpowered MCU receives zero current.
3. **The 1 MΩ ADC bleed is inadequate for a conservative off-state guarantee:** the mux's full-temperature powered-off leakage limit is ±2 µA, not its room-temperature 10 nA limit. `2 µA × 1 MΩ = 2 V` before MCU clamps. Replace the bleed with **10 kΩ**, accept and calibrate about 9.1% attenuation.
4. **Increase excitation resistance to 10 kΩ**. The original 1 kΩ excitation allows 3.3 mA through a highly compressed FSR if its return cable shorts directly to ground, bypassing R_RET and R_MEAS. Even a full 10 mm actuator is only permitted <0.785 mA by the integration guide. 10 kΩ limits this particular low-voltage fault to 0.33 mA nominal.
5. **Add 10 kΩ immediately before OPA333 +IN**, after C_SENSE. This limits discharge of a charged sense capacitor into the OPA input protection when its supply collapses. Shared supplies alone do not prevent that transient.

## Primary sources and exact claims

Sources accessed 2026-11-10:

- **[I1] Interlink PDS-10004-C**, Model 402 Short Tail page and available-part-number list: https://interlinkelectronics.com/downloads/datasheets/fsr-400-series-datasheet.pdf . Manufacturer document text obtained via indexed search. This reconfirms contact style and dimensions, not an independently measured drawing or connector fit.
- **[I2] Interlink EIG-10000 Rev B**, manufacturer-authored Integration Guide, hosted by DigiKey: https://media.digikey.com/pdf/Data%20Sheets/Interlink%20Electronics.PDF/FSR_Integration_Guide.pdf . Full extracted text reviewed. §4 lists 1 mA/cm² of applied force; §6 printed p23 says **less than** 1 mA/square cm; §9 printed p30 explicitly calls this **actuator area** and warns of irreversible damage. Use actual loaded contact area, not total active sensor area.
- **[T1] TI OPA333/OPA2333 SBOS351E**, §§5, 6.1, 6.3, 6.6, 7: https://www.ti.com/lit/ds/symlink/opa333.pdf . PDF directly downloaded and tables inspected.
- **[T2] TI TMUX1511 SCDS390B**, §§4, 5.1, 5.3, 5.5, 7.3.4, 7.4: https://www.ti.com/lit/ds/symlink/tmux1511.pdf . PDF directly downloaded and tables inspected.

### OPA333: input, output and startup

[T1] recommended supply 1.8–5.5 V; specified temperature −40 to +125°C. Common-mode range is V−−0.1 V to V++0.1 V **while powered in its operating range**, not an unpowered-input rating. Input terminals have supply-rail clamps. Absolute-maximum input voltage is −0.3 V to V++0.3 V, and the input-current table says **±1 mA**. The footnote separately says limit excursions beyond the rails to 10 mA or less. These conflict; use the stricter **1 mA** as a stress ceiling, not permission for normal clamp conduction or rail backfeed.

Output swing: at RL=10 kΩ, **30 mV typical, 50 mV maximum at 25°C; 70 mV maximum over −40 to +125°C**. Table default load connection is VS/2. Therefore the previous 0.05–3.25 V design window is not a full-temperature guarantee. Nor can this table prove exact low-end performance with the proposed ground-referenced load. Treat low readings as an unloaded/invalid band and validate the actual load, ADC and temperature range. The proposed short-end voltage is well below the upper rail.

Unity-gain stable does not mean stable with arbitrary direct capacitance. Retain a series ADC resistor outside feedback; do **not** attach the 100 nF ADC reservoir directly to OUT. The table's ±5 mA short-circuit current is typical, not guaranteed available linear output current. Capacitive-load behavior is given by typical curves, not a blanket 100 nF drive guarantee.

**Turn-on time is 100 µs typical at VS=5 V**, not a guaranteed maximum at 3.3 V or during brownout. Do not use it as a safety deadline. Proposed firmware blanking is 20 ms after valid rails/reference and enabling the signal path, followed by settling/plausibility checks; this is a design assumption pending bench verification, not a TI guarantee. No analog sample may override asserted binary braking in the control-model contract; no torque-sign hardware inhibit or firmware is implemented.

### TMUX1511: actual limits, not feature-name inference

[T2] §5.3 allows:

- VDD=1.5–5.5 V in normal operation; S/D from 0 to min(2×VDD, 5.5 V).
- For **VDD<1.5 V**, S/D range **0–3.6 V**. This is the low-supply signal-voltage limit, not a promise of precise transfer during a ramp.
- §7.3.4 explicitly promises high-Z powered-off I/O at VDD=0 V, with datasheet leakage performance. Fail-safe logic is a separate feature; it is not the evidence for analog powered-off isolation.
- §5.5 IPOFF: **±10 nA maximum only at 25°C, VS=0–3 V, VD=0, VDD=0**. The general **VS=0–3.6 V, VDD=0, VD=0** row permits **±2 µA** over the table's −40 to +125°C range. Do not substitute the typical 0.01 value for either maximum.
- RON=2 Ω typical, 4.5 Ω maximum under the stated table test conditions; logic VIH≥1.2 V and VIL≤0.45 V. Internal select pulldown 6 MΩ; use the explicit external 100 kΩ anyway.
- Absolute-maximum S/D=−0.5 to +6 V is a stress rating, not an operating envelope and emphatically not 48 V protection.

**No replacement isolation IC is necessary for this bounded low-voltage use.** Replacing a correctly specified device merely because its protection was suspected false is not a safety improvement. The safer change is a leakage-aware termination and controlled sequencing. If a future requirement includes battery voltage on the analog port, this part is rejected and a separate rated protection design is required; this review does not nominate an unverified drop-in high-voltage substitute.

## Exact recommended nets and package pins

Design assumptions: 3.3 V nominal rail, ≤3.465 V including assumed +5% DC tolerance, nonnegative signals; overshoot must also remain below 3.6 V at unpowered mux pins. `+3V3_ADC` and MCU analog/reference supply use the same switched domain; `AGND` is the common low-voltage ground. Use 1% or better series/bleed resistors, 0.1% R_MEAS. This is a revised divider, not the old evaluation's 2 kΩ series-resistance model.

| Device / terminal | Connect to |
|---|---|
| R_EXC 10.0 kΩ | `+3V3_ADC` → J_FSR.1 `FSR_EXC_CABLE` |
| Interlink 34-00018 | Between J_FSR.1 and J_FSR.2; resistive sensor has no polarity; these connector numbers are our logical harness assignment, not a vendor polarized pin assertion |
| R_RET 1.00 kΩ | J_FSR.2 `FSR_RETURN_CABLE` → `FSR_SENSE` |
| R_MEAS 10.0 kΩ and C_SENSE 100 nF | Each from `FSR_SENSE` to `AGND` |
| R_IN 10.0 kΩ | `FSR_SENSE` → `FSR_OP_IN`; place close to op amp |
| **OPA333AIDBVR**, DBV SOT-23-5 pin **3 +IN** | `FSR_OP_IN` |
| OPA333 pin **1 OUT**, pin **4 −IN** | Both `FSR_BUF`; direct local unity-gain feedback |
| OPA333 pin **5 V+**, pin **2 V−** | `+3V3_ADC`, `AGND`; 100 nF between 5 and 2 close to IC |
| **TMUX1511PWR**, PW TSSOP-14 pin **2 S1** | `FSR_BUF` |
| TMUX pin **3 D1** | `FSR_ISO_OUT` |
| TMUX pin **1 SEL1** | `FSR_SAMPLE_ENABLE`; 100 kΩ to AGND; drive low at reset and disable on invalid supply/reference |
| TMUX pin **14 VDD**, pin **7 GND** | `+3V3_MCU`, `AGND`; 100 nF bypass |
| TMUX pins **4 SEL2, 10 SEL3, 13 SEL4** | AGND |
| TMUX pins **5 S2, 6 D2, 8 D3, 9 S3, 11 D4, 12 S4** | Unconnected unused signal pins |
| R_ADC 1.00 kΩ | `FSR_ISO_OUT` → `FSR_ADC` |
| C_ADC 100 nF and **R_BLEED 10.0 kΩ** | Each from `FSR_ADC` to AGND |
| MCU ADC | `FSR_ADC`; exact MCU pad and acquisition settings remain an integration gate |

**Package warning:** OPA333 DCK/SC70 has a different pin assignment from DBV/SOT-23. Use the order code above and [T1] §5, not a generic five-pin op-amp symbol assumption. TMUX1511 QFN pin numbers also differ; this table is strictly PWR/TSSOP.

## Calculations and scope

Nominal DC, ignoring bias and switch leakage:

`V_SENSE = 3.3 × 10000 / (R_FSR + 10000 + 1000 + 10000)`.

At sensor short: I=3.3/21000=**0.15714 mA**, V_SENSE=**1.57143 V**. At 10 kΩ sensor resistance V_SENSE=**1.06452 V**; at open it tends to zero. The reduced span is intentional to protect the return-to-ground fault; recalibrate and update any model using the old 2.75 V short endpoint.

Post-buffer gain including a 4.5 Ω mux resistance is `10000/(10000+1000+4.5)`=**0.908719**, giving short-end ADC about **1.4280 V**. RON uncertainty is small relative to the intentional divider; calibration must include all resistor tolerances. DC buffer load is about 11 kΩ to ground, not the original 1 MΩ load. Initial ADC-capacitor charging is a larger transient load and requires measured settling/stability.

10 mm full-contact disk area `π×(0.5 cm)²`=**0.78540 cm²**. Original nominal short current 0.275 mA needed contact area >0.275 cm² (disk diameter >5.917 mm); the housing/active diameter alone does not prove that. Revised worst low-voltage return-to-ground case with a zero-resistance FSR and assumed +5% rail/−1% R_EXC is `3.465/9900`=**0.350 mA**, requiring **actual loaded contact area >0.350 cm²**, equivalent disk diameter >6.676 mm. A 10 mm nominal pad must demonstrably maintain this area; a tiny asperity is not acceptable. This bound does not cover an external voltage driving the return cable or a shorted R_EXC.

At nominal 3.3 V, R_IN limits a charged sense-node discharge into an unpowered OPA input to at most **0.33 mA** ignoring clamp drop; +5% rail/−1% resistor gives **0.350 mA**. It limits current but does not establish allowable rail backfeed. Rail decay and input-capacitor discharge must be scoped, and no independent external source may drive this prototype connector.

With ±2 µA mux leakage, 10 kΩ bleed produces **20 mV** nominal (20.2 mV at +1% R), instead of 2 V with 1 MΩ. This is a conservative DC budget using the published grounded-drain leakage test, not a substitute for MCU unpowered-pin specifications or transient testing. MCU leakage and other board leakage add to it. ADC capacitor off-state discharge time constant is **1 ms**, subject to tolerances. Do not assume immediate zero after disable.

## Power-state and release gates

| Condition | Required disposition |
|---|---|
| Both rails valid, enable low | Mux open; ADC bleeds down; sample invalid |
| Both rails valid, enable high | Sample only after blanking and verified acquisition/settling |
| MCU/mux off, buffer live | Buffer signal must stay 0–3.6 V; bleed budgets powered-off leakage; verify MCU off-state voltage/current |
| Frontend off or collapsing | R_IN limits C_SENSE dump; verify rail backfeed and output behavior; samples invalid |
| Brownout/ramp | Do not claim zero feedthrough for every intermediate supply; validate with scopes and an enable/reset scheme tied to actual MCU supply-valid behavior |
| Exposed cable ESD/negative pulse | Not qualified by this topology; a nominal “3.3 V TVS” is not sufficient evidence of clamp voltage or leakage |
| Cable to traction battery | **Explicit blocker for vehicle/board release. Neither TMUX1511 nor OPA333 nor these resistors is rated to make this safe.** Require rated fault isolation/current limiting, continuous dissipation and pulse analysis, clamp energy and dead-rail review, or a formally reviewed physical-exclusion architecture |

This is implementable for a current-limited, segregated **low-voltage bench prototype** with no external cable driver. It is not a ride-ready protected harness. Remaining gates: actual MCU input/injection and ADC timing specifications; supervisor/reset behavior through slow ramps and rapid power loss; OPA stability with this RC/load; worst-temperature board/clamp leakage; real pad contact area; ESD and battery-short protection; mechanical noninterference. Separate binary switches remain authoritative in the control-model contract. No hardwired torque-sign inhibit exists and all firmware remains unimplemented.
