> **STATUS: HISTORICAL CANDIDATE ANALYSIS — superseded for actual circuit values and safety claims by [FSR circuit milestone](fsr-circuit-milestone.md). References below to a hardwired positive-torque inhibit were incorrect: only a firmware/control-model contract exists; firmware is unimplemented. Not safety qualification.**

# Brake-lever FSR analogue frontend evaluation

| Field | Value |
|---|---|
| Date / branch | 2026-11-10 / `pr/fsr-evaluation` |
| Base | `eff2bd7`, fetched GitHub master |
| Worktree | `~/worktrees/cycle-fsr-eval` |
| Scope | Sensor placement, electrical transfer functions, candidate parts, reproducible DC model |
| Excluded | Shared hardware generator, brake topology redesign, purchasing, force-accuracy certification |
| Read first | `hardware/powerboard-reva/docs/safety-review.md` |
| Reproduce | `python3 -m unittest discover -s analysis/fsr -v`; `python3 analysis/fsr/frontend.py` |

## 0. Recommendation and decision log

**D1. Start with Interlink Model 402 short-tail, MPN 34-00018 (housed female contacts), and a protected 10 kΩ divider plus OPA333 buffer.** Its 12.70 mm active circle accommodates an initial **10 mm diameter compliant actuator**, unlike the 5.08 mm Model 400. Placement is a removable finger-contact pad on the existing lever, backed by a flat support local to the pad. Do not drill, cut, weaken, constrain travel, replace the friction brake, or put the sensor in the cable/hydraulic load path. The cover must remain secure and non-slip wet or dry; a detached pad must not jam the lever. This senses local finger pressure, **not wheel braking force**. Gloves, finger position and lever curvature matter.

**D2. Keep the separate mechanical switch and hardwired positive-torque inhibit independent.** No FSR value, missing cable, unloaded state, firmware calibration, ADC saturation or invalid sample may override asserted binary braking. This study does not choose regen/inhibit topology: regen availability and safe sequencing remain the parallel brake review's responsibility. Friction braking must work without power. FSR failure invalidates analogue modulation; it must not silently mean permission for propulsion.

**D3. Do not fit a Wheatstone bridge or passive R–2R ladder by default.** A one-active-arm bridge is another divider with a subtracted reference; gain 4 clips over most of the illustrative resistance sweep. A passive linear resistor network cannot undo sensor hysteresis, creep or a nonlinear force law. R–2R is useful as a DAC for injected calibration voltage/offset only if an actual requirement emerges; firmware calibration avoids GPIO resistance, ladder matching, extra noise and power-state risks.

**D4. Full electrical resistance coverage is not full mechanical force coverage.** The default sweep is resistance-only, not invented force data. The sensor's published typical sensitivity range is approximately 0.2–20 N, dependent on contact mechanics; actual finger-force envelope and pad load share are unknown. A more sensitive amplifier cannot recover sensor saturation. If lever trials exceed the calibrated range, change pad mechanics or sensor class—not just ADC gain.

## 1. Primary evidence and limits

Sources retrieved 2026-11-10. No stock or cost claims. No sourced curve has been numerically fitted or digitised.

* **[S1] Interlink PDS-10004-C, FSR 400 Series datasheet**, characteristics and individual model pages: https://www.interlinkelectronics.com/downloads/datasheets/fsr-400-series-datasheet.pdf . Search extraction returned the document text; direct web extraction was blocked by resolver/private-address checking, so dimensional revision must be checked again at schematic release.
* **[S2] Interlink EIG-10000 Rev B Integration Guide**, manufacturer-authored PDF mirrored by DigiKey, §§2.2, 4–7, 9: https://media.digikey.com/pdf/Data%20Sheets/Interlink%20Electronics.PDF/FSR_Integration_Guide.pdf . Full text retrieved. Figure 2 is measured on a 402 using silicone rubber, 4 mm spherical-radius tip, 60 Shore A. It is **not this lever's curve**. §6 current-to-voltage and voltage-divider circuits are the electrical precedents.
* **[S3] TI OPAx333 SBOS351E**, features/electrical characteristics/application sections: https://www.ti.com/lit/ds/symlink/opa333.pdf . Returned extraction is partial; detailed load/temperature limits require PDF-table review before schematic freeze.
* **[S4] TI TMUX1511 SCDS390B**, §§5.3–5.5, 7.3.4: https://www.ti.com/lit/ds/symlink/tmux1511.pdf . Powered-off isolation is limited to 0–3.6 V; it is not high-voltage cable protection.
* **[S5] TI REF33xx Rev I**, REF3325 table and supply section: https://www.ti.com/lit/ds/symlink/ref33.pdf . Retrieved indexed datasheet text; optional reference, not fitted baseline.

### Sensor shortlist (CITED S1/S2)

| Model / candidate MPN | Geometry | Disposition |
|---|---|---|
| 400 / 34-44001 | 5.08 mm active circle | Small for finger pad; local pressure/current density rises with small contact. Reject as first prototype. |
| 402 short / **34-00018** | 12.70 mm active circle; 0.46 mm nominal thickness | Provisional recommendation; confirm pad fits actual lever. |
| 406 / 34-61152 | S1 gives 39.6 × 39.6 mm active area | Too large for an unmeasured lever; useful bench comparison, not assumed to fit. |

S1 and older S2 differ on some standard-model dimensions (S2 lists 406 as 38.1 mm). Do not mix drawings or infer mechanical fit from the series headline.

Shared S1 characteristics: actuation about 0.2 N; typical sensitivity 0.2–20 N; unactuated resistance >10 MΩ; single-part repeatability ±2%, part-to-part ±6% within a batch; average hysteresis +10% `(RF+−RF−)/RF+`; long-term drift <5%·log10(time), tested 1 kg for 35 days. These are **not guaranteed accuracy over every force and temperature**, and the drift notation is not an independently defined lifetime bound. Most figures derive from 1000 g tests and standard-deviation/mean conventions. Hot +85°C after one hour: average resistance change −15%; cold −40°C: −5%; +85°C/95% RH: +10%. These exposure results are not a usable universal temperature coefficient. Do not convert them to ppm/°C.

S2 explains turn-on, an intermediate inverse-power region, and high-pressure saturation; spreading contact can move saturation. **Maximum current <1 mA/cm² of actuator contact area**, not whole sensor area. No universal safe contact-stress allowable was established. A 10 mm full-contact disk gives 0.785 cm²; 20 N corresponds to 254.648 kPa (COMPUTED, not allowable stress). Real partial contact can be far smaller. Avoid shear, creasing, loading spacer edges, blocked vent paths and cyanoacrylate. Seal the assembly against weather without trapping the vent; validate with the actual cover/adhesive.

## 2. Transfer functions and option comparison

Assume 3.3 V analogue rail equals ADC reference, illustrative ideal 12-bit ADC, 10 kΩ measuring resistor, 2 kΩ total cable-leg protection resistance. These are design assumptions, **not measured MCU ENOB or FSR resistance extrema**.

| Option | Transfer and range | Verdict |
|---|---|---|
| Binary switch only | No continuous force signal | Safe baseline; cannot satisfy requested modulation. |
| Divider + buffer | `V=Vs·Rm/(Rfsr+Rs+Rm)` | Rank 1: monotonic, bounded short current, ratio-metric, few parts. Firmware inverse/calibration needed. |
| Constant-voltage conductance amplifier | FSR from inverting input to ground, non-inverting at E, feedback Rf: `Vout=E·(1+Rf/Rfsr)` | Rank 2 after characterisation. E=0.3 V, Rf=10 kΩ gives 0.3 V unloaded, 0.6 V at 10 kΩ, 3.3 V at 1 kΩ. Near-linear in **conductance**, not universally force. |
| One-active-arm bridge + PGA | `Vout=Vs/2+G·(Vs·Rb/(Rfsr+Rb)−Vs/2)` | Rank 3: useful near a known balance point, poor decades-wide range. No strain-gauge-style temperature cancellation from three fixed resistors. |
| Switchable divider/feedback ranges | Different Rm or Rf per sample, with explicit range metadata | Add only when measured ADC discrimination is insufficient. Must calibrate overlaps, settling and switch leakage. |

Conductance amplifier at E=0.3 V and a conservative output ceiling 3.25 V requires `Rfsr >= E·Rf/(3.25−E)` = about 1.02 kΩ for Rf=10 kΩ. A true short drives saturation and loses virtual-ground regulation; **never leave current limiting out**. With 2 kΩ series protection its actual law becomes `E·(1+Rf/(Rfsr+2k))`; max output 1.8 V and current 0.15 mA, but it is no longer constant voltage across the FSR itself. This is the protection-vs-conductance trade; do not quote the ideal formula for the protected circuit.

For bridge G=4 and Rb=10 kΩ, 0.05–3.25 V output only covers approximately 6.10–16.40 kΩ. At open the ideal prediction is −4.95 V; at short +8.25 V: both physically clip on 3.3 V power. A PGA cannot restore clipped information; a bare bridge with gain 1 gains little over the divider while adding reference and common-mode constraints. No PGA MPN is recommended until a narrow balanced operating envelope exists.

Switchable Rm=10 kΩ baseline with an optional 1.11 kΩ shunt gives about 1 kΩ high-force range. The 2 kΩ protection then caps short current at 1.1 mA, **exceeding the 0.785 mA full-10mm-contact limit**. Therefore do not enable this example without increasing current limiting/reducing excitation and re-running contact-area calculations. A 100 kΩ low-force range improves weak signals but increases leakage sensitivity and settling. All ranges retain a permanent measuring resistor: switch reset/failure must not float the input.

## 3. Computed DC and resolution results

Run `analysis/fsr/frontend.py`; resistance points are **arbitrary electrical sweep inputs, not measured or proxy force curves**.

| Rfsr | Divider V | Ideal ADC code |
|---|---:|---:|
| open | 0 | 0 |
| 10 MΩ | 0.003296 | 4 |
| 1 MΩ | 0.032609 | 40 |
| 100 kΩ | 0.294643 | 366 |
| 10 kΩ | 1.500000 | 1862 |
| 1 kΩ | 2.538462 | 3151 |
| 100 Ω | 2.727273 | 3385 |
| short | 2.750000 | 3413 |

Short current = 0.275 mA, or 0.350 mA/cm² for **full** 10 mm contact; smaller actual patches require requalification. Full code use is deliberately sacrificed for current limiting. OPA333 ground-rail swing also means the tiny unloaded values are not promised accurately; low readings are an unloaded/fault band, not precision force.

LSB `3.3/4096` = **805.664 µV**, ideal quantisation RMS **232.575 µV**. `dV/dR=−Vs·Rm/(R+Rs+Rm)^2`; local resistance per LSB is 3.574 Ω at 100 Ω, 4.126 Ω at 1 kΩ, 11.816 Ω at 10 kΩ, 306.250 Ω at 100 kΩ, and 25003.516 Ω at 1 MΩ. Thus a wide sweep is not uniformly resolved. Force per code needs **measured local dR/dF on both load directions**, which is absent.

Thermal noise `sqrt(4kTRB)` for a conservative 10 kΩ Thevenin resistance, 300 K and assumed 50 Hz equivalent noise bandwidth is **0.091 µV RMS**. This is only resistor noise, not total noise. OPA333 10 µV maximum headline offset is 0.0124 ideal LSB; 1.1 µV peak-to-peak 0.01–10 Hz noise cannot be substituted for integrated 50 Hz RMS. PWM/ground pickup, switch leakage, ADC INL/DNL, sampling charge, reference ripple and real ADC ENOB are unmeasured. Even 1 nA leakage through 10 kΩ is 10 µV; budget worst-temperature protection/mux leakage before release. Sensor hysteresis/repeatability and mounting dominate any claim of fine force accuracy; averaging does not remove them.

Ratio-metric cancellation holds only when excitation and ADC reference track the **same rail at sampling time**. Filter-induced delay, ground drops and ADC reference settling break it. If MCU uses an internal fixed reference, measure excitation or redesign scaling. Do not replace a ratio-metric rail with a precision reference solely because it sounds more accurate.

## 4. Exact candidate connectivity for next schematic milestone

This is a proposed net list, **not implemented hardware**. Component purchase suffixes/passives, protection leakage and MCU ADC pin limits remain release checks.

* `+3V3_ADC` powers U_FSR **OPA333AIDBVR**, with 100 nF close bypass to `AGND`. `+3V3_ADC` must be the same switched domain as MCU analogue supply/reference.
* `+3V3_ADC` → R_EXC **1.00 kΩ** → J_FSR.1 `FSR_EXC_CABLE`; sensor → J_FSR.2 `FSR_RETURN_CABLE` → R_RET **1.00 kΩ** → `FSR_SENSE`.
* R_MEAS **10.0 kΩ, 0.1%** from `FSR_SENSE` to `AGND`; C_SENSE **100 nF** parallel. Buffer +IN=`FSR_SENSE`, −IN=OUT=`FSR_BUF`. Cable series resistors are both part of Rs=2 kΩ in the model.
* `FSR_BUF` → U_ISO channel 1 **TMUX1511PWR** → R_ADC **1.00 kΩ** → `FSR_ADC`; C_ADC **100 nF** to `AGND`. U_ISO VDD=`+3V3_MCU`, GND=`AGND`, SEL1=`FSR_SAMPLE_ENABLE` with external **100 kΩ pulldown**. Unused SELs low; unused signal terminals no connection. R_BLEED **1 MΩ** from `FSR_ADC` to AGND discharges the local capacitor. Its roughly 0.1% attenuation through R_ADC must be included in calibration, not in the ideal divider table above.
* Fit connector-side ground-referenced ESD devices on both cable nets, provisional **PESD3V3U1UL** candidate only; **not yet qualified or included as an approved BOM MPN**. Select actual TVS from clamp-versus-pulse and leakage data; a “3.3 V TVS” does not clamp to 3.3 V. Reserve secondary low-leakage clamps after series resistors with a controlled rail sink. No direct cable-to-MCU connection.
* Keep mechanical-switch connector, `BRAKE_HW_ASSERT` and hardwired inhibit entirely separate from these ADC nets. No ladder/DAC/mux net may mask that signal.

OPA333: recommended 1.8–5.5 V supply; common mode advertised 100 mV beyond either rail; rail-to-rail output headline within 50 mV (load/temperature dependent), 10 µV max offset, 0.05 µV/°C max drift [S3]. Design around 0.05–3.25 V until exact load tables are checked; do not confuse input common-mode range with absolute input tolerance when unpowered. ADC RC isolates capacitive load; stability and acquisition-time checks still mandatory.

TMUX1511: 1.5–5.5 V supply, signals 0 to min(2·VDD,5.5 V) powered, **0–3.6 V unpowered**, logic VIH≥1.2 V/VIL≤0.45 V, RON 2 Ω typical/4.5 Ω maximum in listed conditions [S4]. 3.3 V GPIO is compatible. Isolation protects a live buffer from a dead MCU only within these limits; residual off leakage and rail ramp behaviour must be checked against the actual MCU's injection budget. The device is not a substitute for cable ESD protection.

Optional REF3325AIDBZR: 2.5 V reference, input ≥2.7 V and ≤5.5 V, ±0.15% initial accuracy, 30 ppm/°C maximum drift, ±5 mA output headline [S5]. It is **DNP**, not a buffer or PGA; common-mode/offset specs do not apply. If chosen for a conductance experiment, divide and buffer it for E, and use the same reference for conversion or explicitly correct excitation ratio. A REF3333 cannot regulate 3.3 V from a nominal 3.3 V input.

## 5. Faults, power states and unclosed protection work

Ranked qualitatively by severity, not invented probability:

| Priority / fault | Observable analogue result / requirement |
|---|---|
| Critical: mechanical interference | No electrical mitigation suffices. Verify full lever travel, friction braking and non-jamming detached cover. |
| Critical: brake asserted + any ADC value | Hardwired positive-torque inhibit remains asserted. Python predicate tests document this invariant; they do **not** verify a real circuit. |
| High: sensor/cable open | Near zero; indistinguishable from unloaded FSR using two wires. Mechanical switch mismatch diagnostics can flag, not prove which failed. |
| High: sensor short | About 2.75 V in baseline; may overlap high-force low resistance. Do not claim perfect short detection from one ADC reading. |
| High: return short to ground / excitation | Zero / high reading or buffer clipping. Both invalidate plausibility; independent switch remains authoritative. |
| High: cable short to battery | Current design **not qualified for 48 V-class fault**. Series resistors/3.3 V TVS alone are insufficient without pulse/power calculations and clamp coordination. Physically segregate wiring; choose rated protection or declare this fault outside enclosure exposure only after review. |
| High: MCU off, frontend on | U_ISO off with pulldown and powered-off protection; capacitor discharge/leakage injection measured before acceptance. Never rely only on MCU internal ESD diodes. |
| High: frontend off, cable externally driven | OPA333 can backfeed through input clamps; shared supply is insufficient for an external fault. Requires secondary clamp/rail sink or cable isolation qualified for dead-rail state. |
| Medium: mux stuck on / broken sense resistor / moisture shunt | Plausible-but-wrong modulation remains possible. Range checking alone is not diagnostic coverage. |
| Medium: slow filter / ADC mux settling | C_SENSE worst RC≈1 ms, C_ADC≈0.1 ms; evaluate at actual source resistance, rail/reference and ADC acquisition timing. Braking hardware must not wait for filters. |

No functional-safety rating, transient immunity, EMC result or riding release is claimed. Optional end-of-line resistance could distinguish unplugged cable from unloaded sensor but consumes range and still cannot diagnose every internal sensor fault. Do not add it without testing the intended diagnostic circuit.

## 6. Calibration and acceptance plan

1. Photograph and dimension actual lever, gloves, finger locations, support and cover. Measure total hand force and **actual pad normal load/contact area** separately; establish wet/dry maximum and minimum envelope. Do not assume all lever force goes through the pad.
2. On the mounted assembly, record raw ADC, excitation/reference, calibrated load-cell force and temperature across multiple load/unload cycles. Include zero, threshold region, intermediate points and the highest intended load; dwell at each, then extended holds to measure creep and recovery. Precondition using repeatable cycles; preserve first-cycle data too.
3. Repeat with different finger positions/gloves, sensor specimens, remounting and realistic cold/room/hot conditions. Do not extrapolate a single room-temperature loading curve to all these cases.
4. Store monotonic calibration tables with units, direction, mounting ID, temperature and timestamp. Quantify loading/unloading residuals separately; choose deadband/uncertainty envelope from observations. Output a normalized requested modulation with confidence/validity, not unsupported force precision.
5. Inject open, short, wet shunt, disconnected power, brownout and stuck ADC while operating the separate switch. Demonstrate with oscilloscope/logic captures that binary inhibit is independent. Exercise regen unavailable states separately with the brake-topology owner.
6. Compare observed noise and smallest repeatable force change with ADC discrimination before adding ranges or a higher-resolution ADC. Validate switch range overlap, charge injection and settling if fitted.

## 7. Release/open-items gate

Proceed to **a separate reviewed schematic milestone**, not a change to the shared generator in this branch. Required before board release: exact MCU/reference/ADC acquisition and injection limits; actual lever envelope and pad fit; chosen sensor drawing revision; full OPA load/temperature table review; worst-case TVS/clamp leakage and ESD coordination; cable battery-short policy; off-state clamp/rail-sink design; power sequencing; measured force calibration; independent brake review acceptance. A divider recommendation flips to protected conductance/range switching only if measured low-force discrimination warrants the added complexity. Sensor-class recommendation flips if mounting/force range cannot remain inside a repeatable, non-saturated envelope.

## Verification record

Tests were written first; initial interface-only module produced nine expected missing-function errors (RED) before implementation, then all **9 tests passed** (GREEN). This is missing-implementation RED, not a claimed behavioural regression test. Model covers ideal divider endpoints, ratio-metric cancellation, conductance saturation, bridge clipping, ADC clipping, invalid negative resistance, thermal-noise arithmetic and the logical binary-inhibit specification. No hardware, SPICE transient model or force measurements were run. No shared hardware files were changed.
