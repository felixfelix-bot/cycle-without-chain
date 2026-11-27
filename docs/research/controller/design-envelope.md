# Custom series-hybrid bicycle dual-inverter: candidate design envelope

Research date: 2026-11-10. **Candidate architecture, not a validated circuit or manufacturing BOM.** No schematic, layout, thermal design, firmware timing proof, machine selection or safety certification exists. No purchasing or git modifications performed. All ratings below are either manufacturer facts (cited) or explicitly provisional engineering assumptions.

## Recommended architecture

```text
reversible crank gear / guarded belt or chain
  -> clamped PM generator -> 3-phase active rectifier (6 MOSFETs)
                            |
                protected shared DC bus <-> battery / BMS
                            |              fuse, precharge, reverse protection
                            +-> independent chopper + external dump resistor
                            +-> motor inverter (6 MOSFETs) -> motor -> wheel
                            +-> 100V-input auxiliary buck -> 12V / 5V / 3.3V
STM32G474: two current loops, two angle inputs, supervisory energy control
hardware: current trips + OV comparator/latch + watchdog -> PWM kill
hardware OV -> dump chopper independently of MCU
```

A battery-buffered common bus avoids forcing every crank joule through a battery charge/discharge round trip. A crank generator bridge can boost into the bus using machine inductance only with a properly designed active-rectifier control scheme; a diode bridge alone will not charge a 48V bus at arbitrarily low speed. At zero speed no crank power is available. Batteryless starting is a separate unresolved architecture, not an included feature.

## Provisional electrical envelope (assumptions, not ratings demonstrated)

- Start with a **48V-class common bus**, example 13-series lithium-ion pack at 4.2V/cell = 54.6V maximum charge. Cell chemistry and BMS remain unselected. A 16-series LiFePO4 example at 3.65V/cell is 58.4V and leaves substantially less protection margin. Neither charging voltage is a selected pack specification.
- Normal regulated bus target **36–58V; never >60V normal**. Low-voltage shutdown must follow the selected battery, not this provisional lower bound. Reject 72V-class packs for this revision. A 14s 4.2V pack reaches 58.8V: do not accept without redoing tolerance and dump thresholds.
- Preliminary 13s-only coordination example: inhibit discretionary regeneration around 56V, autonomous dump begins around 58V, independent OV fault around 62V. Tolerances/hysteresis and dynamic overshoot must be budgeted. This set is incompatible with fully charged 16s LiFePO4 without revision.
- Engineering goal: keep bus surge below 70V and local MOSFET VDS ringing below 80V. These are **measurement acceptance goals**, not a promised clamp characteristic. A TVS marked 60V may clamp far above 80V at rated current; choose from its full I–V curve and actual surge impedance, not its label.
- 100V MOSFETs, 100V-rated bulk/link capacitors and 100V-input auxiliary converter are starting candidates. No 63V bulk capacitors on an unvalidated 60V bus. Derating, ceramic DC-bias loss, ripple current, life, temperature and cold-start must all be checked.
- DRV8353's name says 100V, but **VM recommended supply is only 9–75V**, whereas VDRAIN is 7–100V [S1 §7.3]. Prefer regulated 12V VM and direct bus VDRAIN; obey the TI split-supply implementation and sequencing. Direct bus VM is possible only if all transients stay within its own limits, and has higher gate-drive dissipation.
- Initial research sizing point: 150W continuous crank input, 300W short crank burst, 250W nominal motor-side class, up to 500W brief electrical throughput and ±15A battery branch, ±20A peak phase current. These are **placeholders to avoid leaving power unspecified**, not a validated/legal operating rating. Low-speed phase current can greatly exceed DC current. Select shunts, copper, fuse and connectors only after motor Kt, generator gearing and stall envelope are known.
- Start PWM study at 20kHz (assumption), then optimize acoustic noise versus switching loss and ADC sampling windows. Do not increase frequency merely because MCU/driver allow it.

## Candidate comparison and verified manufacturer facts

| Block | Candidate and assessment | Verified facts / unresolved issue |
|---|---|---|
| MCU | STM32G474RE, provisional 64-pin choice; larger-pin G474 if routing fails | ST product page [S2] confirms 170MHz Cortex-M4, 512KB flash, 128KB total SRAM, CORDIC/FMAC, five 12-bit 4MSPS ADCs, advanced motor timers and HRTIM. Product-family peripheral counts do not prove RE package pin availability. Check exact order suffix, alternate-function mapping, ADC trigger/DMA conflicts, dual encoder interfaces, two simultaneous control-loop WCET, errata. One MCU per bridge is a fallback if timing/pin allocation fails; it adds synchronization and quiescent loss. |
| Gate drivers | 2 × DRV8353SRTAR (SPI, no buck), leading candidate | TI [S1] confirms order code, 3 low-side shunt amplifiers, gains 5/10/20/40, bidirectional sensing, 1A source / 2A sink peak, adjustable gate current, VDS OCP, fault outputs, UVLO and charge pump supporting 100% duty. VM and VDRAIN are different domains. DRV8353RS integrates a 6–95V, 350mA buck, not a free 100V/1A supply. Separate LM5164 gives a more explicit auxiliary budget. |
| Main switches | 12 × CSD19536KCS, verified starting comparator rather than final optimum | TI [S3]: 100V, TO-220, RDS(on) typ 2.3/max 2.7mΩ at VGS=10V, 25°C, ID=100A; Qg typ 118/max 153nC under datasheet conditions. Large package and charge may be excessive at 150W. Current printed on datasheet is not PCB continuous current. Compare smaller-die 100V MOSFETs after actual current and loss sweep; lower RDS is not always better. |
| Alternate MOSFET | IPP023N10N5, deferred | Infineon manufacturer URL found [S8], but direct fetch returned empty HTTP 202. **Not independently verified here; not promoted to selected BOM.** Search snippets suggest low RDS and substantial charge, but these are not accepted design inputs. |
| Phase currents | 6 Kelvin low-side shunts using the two DRV8353 CSAs | Provisional 2mΩ, gain 20: ±20A gives ±0.8V around mid-reference, 0.8W instantaneous per conducting shunt at 20A. Actual RMS dissipation, pulse overload, output swing, CSA offset and sample timing must be checked. Three-shunt reconstruction has high-duty sampling constraints even though gate drive supports 100% duty. |
| Battery current | INA240A1, 20V/V plus Kelvin shunt | [S4] confirms bidirectional measurement, REF inputs, −4 to 80V common-mode, 2.7–5.5V supply and PWM rejection. 80V common-mode is a tighter limit than the MOSFET rating. Example 2mΩ gives ±0.6V at ±15A; keep headroom for fault measurement. Check package order code. Use on battery branch to measure net buffer energy; bus/phase readings do not substitute. |
| Higher-voltage current alternative | INA293 not a drop-in replacement | [S5] verifies −4 to 110V common-mode but **unidirectional only** (§7.3 and §8.2). It cannot measure both battery charge and discharge by adding a reference pin it does not have. If >80V sensing tolerance is needed, qualify a genuine bidirectional ≥110V amplifier or isolated/Hall sensor; exact MPN unresolved. |
| Bus voltage | resistor chain, RC, ADC protection; independent divider for OV | Example 3×100kΩ top plus 10kΩ bottom gives 31:1: 60V ->1.935V; 80V ->2.581V; total dissipation at 60V =11.6mW. 0.1% ratio parts and resistor working-voltage limits; high ADC source impedance requires acquisition-time/buffer analysis. Include open/short divider diagnostics and avoid back-powering an unpowered 3.3V rail through clamps. |
| Auxiliary | LM5164, bus-to-12V, followed by efficient 5V regulator and clean 3.3V rail | [S6] confirms 6–100V input, up to 1A, light-load diode emulation, 10.5µA no-load IQ, UVLO/PGOOD, 8-pin PowerPAD. 12V output cannot regulate from input below 12V. This is an IC, not a module: inductor, caps, RON, feedback, ripple-injection/stability and thermal design remain. No assumption that datasheet peak efficiency holds at our load. |
| Independent OV | TLV1811 comparator candidate, reference + hysteresis + latch unresolved | [S7] confirms 2.4–40V supply, rail-to-rail inputs, 420ns typical delay, push-pull. **Never power from raw 48V bus**. Supply from protected 12V; use divided bus. TLV1821 open-drain sibling may simplify fault combining. Not a complete short-circuit protector and not a safety certification. |

## Low cadence, loss of power and bootstrap distinction

A bootstrap-only high-side driver needs periodic low-side switching to recharge its capacitor; held high at low electrical speed can lose gate voltage. DRV8353 uses a charge pump supporting 100% duty, so that specific bootstrap limitation is avoided, subject to pump current, capacitance, startup and UVLO requirements [S1]. It does **not** solve sensorless angle estimation at standstill. Fit a generator angle sensor and motor Hall/encoder provision; do not count on back-EMF sensing at walking speed. Gear ratio, pole count and minimum cadence set electrical frequency. High-side duty support also does not remove low-side shunt sampling blind zones.

With gates disabled, each bridge still contains six MOSFET body diodes. A spinning PM machine can rectify into the DC link whenever line-to-line EMF exceeds the bus plus diode drops. **PWM kill, nFAULT, MCU reset or opening the battery is not generator isolation.** Assess worst-case open-circuit EMF at maximum attainable crank/wheel speed and towing. A true blocking path needs a rated bidirectional disconnect/contact arrangement or appropriate back-to-back switches, and interruption of machine inductive current needs a safe commutation path. Do not short the generator as a universal emergency action: it can create severe crank torque and winding heat. Preserve mechanical brakes independent of electronics.

## BMS disconnect, regeneration and dump load

Battery charge acceptance depends on SOC, temperature and BMS state. A charge-limit message is useful but not a safety barrier. A BMS can open abruptly while generator and wheel machine feed the link. Both dump and its autonomous controller must remain on the **inverter side** of that disconnect and remain powered when the pack opens. Assert controlled torque reduction and PWM faults as appropriate, but remember diode rectification persists.

Capacitors provide milliseconds, not sustained absorption. With an assumed 1mF link, energy from 54.6 to 62V is 0.5*C*(62²−54.6²)=0.4314J: at 150W surplus only 2.88ms, at 500W 0.863ms (ignoring other losses). Thus an MCU/BMS protocol alone cannot be the OV defense.

A chopper MOSFET and external enclosed power resistor absorb sustained surplus. At an illustrative 60V dump voltage: 150W requires R=24Ω at full duty, 300W R=12Ω, 500W R=7.2Ω. To cover 500W, a 7.2Ω resistor draws 8.33A when on and uses roughly 30% duty to dissipate 150W at that voltage. Those are calculations, **not a selected resistor or safe continuous rating**. Derate for housing temperature, airflow, fire/contact safety, rain and mounting; add resistor thermal cutoff and fault diagnosis. Downhill regen can exceed human power, so choose between a bigger sink, limited regen and mechanical braking based on vehicle mass/speed/grade. If dump fails open, a second independent strategy must prevent dangerous voltage while preserving braking. TVS/snubber protect short spikes only, not ongoing 150–500W energy. Fuse protects fire faults, not semiconductor microsecond faults.

## Hardware protection and PCB blocks still required

See candidate-bom.csv for a complete functional-block checklist, including unselected parts. Mandatory architecture elements: default-off gate-enable pulls; independent fast phase overcurrent latch and timer-break/driver-disable route; VDS OCP correctly configured and tested; fault wired-OR that cannot be masked by stalled firmware; independent watchdog/brownout; bus OV comparator with reference/tolerance budget; dump control not disabled by normal PWM kill; supply UVLO/sequence; fuse with DC interrupt rating; precharge resistor and bypass with weld/stuck detection; reverse-polarity and reverse-current handling; service disconnect; thermal sensors on both bridges, machines and dump; connector interlock/brake inputs; ESD filtering on long external lines; protected debug/communication interfaces; mechanical weatherproof enclosure and strain relief.

Layout requirements: short commutation loops with local ceramics at each bridge, bulk link between branches, Kelvin shunt and source/sense routes, segregated power and quiet analog returns without forcing signal return paths across splits, controlled gate loops, thermal spreading/vias and accessible test points. Choose stackup/copper from thermal/current modelling, not a generic copper width calculator alone. TO-220 tabs may be live drains and require electrical insulation from common heatsinks and bicycle frame. No frame current return. Gate-resistor/split-diode/snubber footprints should exist but values come from double-pulse/ringing tests. Common-bus current and simultaneous switching require actual ripple analysis; two bridges are not two independent quiet supplies.

## 150W crank-to-wheel efficiency budget

Target is **120W wheel /150W measured crank =80%**, with zero net battery energy change over the measurement interval. Battery assistance can otherwise fake the target. The following is an optimistic *allocation*, not measured machine data:

| Stage | Assumption | Output W | Loss W |
|---|---:|---:|---:|
| Crank mechanical input | measured test input target | 150.000 | — |
| Reversible gear/belt stage | 98% | 147.000 | 3.000 |
| Generator | 93% | 136.710 | 10.290 |
| Active rectifier | 98% | 133.976 | 2.734 |
| Shared link wiring/connectors | 99.5% | 133.306 | 0.670 |
| MCU, drivers, sensing, auxiliary fixed draw | 1.5W | 131.806 | 1.500 |
| Motor inverter | 98% | 129.170 | 2.636 |
| Motor including final wheel transmission | 93% | 120.128 | 9.042 |

Total 80.085%. This leaves almost no reserve: an extra 1W fixed load costs about 0.61 percentage points at the wheel. Both machines must achieve roughly **92.95% each at their actual operating point** if assumed equal and the other allocations hold. With both machines at 90%, result is approximately 74.97%; at 85%, 66.83%. An optimistic 95%/95% machine pair gives about 83.59%. These are sensitivity estimates, not manufacturer efficiencies. They cannot establish feasibility until generator/motor maps exist.

A mechanical reference of 97% (assumption, not a measured Villiger baseline) delivers 145.5W. Equal machine efficiencies would need about 102.3% each to match it under the above other losses: impossible. Thus this series hybrid is a cadence/packaging/control project, not an efficiency improvement over a good mechanical drivetrain. Record direct drivetrain baseline if making a real comparative claim.

MOSFET budget sanity checks: at 20kHz and 10V, 12×118nC×10V×20kHz =0.283W gate-charge energy before driver supply losses; with direct 54.6V supply and linear charge provision, input can be materially larger. At 5A RMS phase current and assumed hot RDS=4mΩ, approximate bridge MOSFET conduction loss 3*Iphase²*RDS =0.30W per bridge. These ignore switching overlap, Coss, reverse recovery, deadtime, shunts and wiring. Large current and low speed quickly invalidate the 2–3W bridge allocation. Use the selected driver topology and measured rail currents to avoid counting gate-drive losses twice.

## Release gates and reversible installation constraints

1. Select and characterize generator and motor: Kt/Ke, R/L, pole count, angle sensing, rated speed/current/temperature, open-circuit EMF over gearing/overspeed, and efficiency maps at 50/100/150/300W crank-equivalent. Measure crank torque/cadence and wheel torque/speed independently.
2. Measure Villiger crank/chainring interface and clearances. Use removable bolt-on gear and padded, load-spreading generator clamps only; no frame drilling/welding. Verify clamp torque reaction, frame material/crush limits, heel clearance, chain retention/guards, bearing side loads, freewheel/backdrive behavior. No mechanical dimensions or clamp safety have been validated.
3. Produce complete schematic, pin allocation, exact orderable BOM and fault tree. Set pack/BMS specs first. Resolve whether generator can unexpectedly motor the pedals and add current/torque direction limits and mechanical protection.
4. Simulate loop stability and fault energy; calculate every operating/absolute maximum separately. Bench first on current-limited low voltage, then full bus with guarded machines and isolated/differential instruments.
5. Verify gate waveforms, double-pulse switching, current calibration, sensing windows, dual-loop timing, stall/low cadence, precharge, thermal steady state and EMI. Inject MCU reset, sensor loss, supply brownout, disconnected dump, hot/full battery and abrupt BMS-open at maximum generator/regen input. Demonstrate local peaks below chosen acceptance goals.
6. Only claim ≥80% after synchronized energy measurement, net battery energy correction, declared sensor uncertainty and duty/cadence range. A decisive inexpensive test is generator plus rectifier at 150W crank; if it cannot approach the allocated 133.98W DC output before auxiliary draw, the stated system allocation already fails.

## Sources and verification provenance

[S1] Texas Instruments DRV835x datasheet SLVSDY6A, downloaded as drv8353.pdf/txt: https://www.ti.com/lit/ds/symlink/drv8353.pdf . Read features, recommended operating conditions, pin descriptions and order addendum. [S3] TI CSD19536KCS SLPS485C: https://www.ti.com/lit/ds/symlink/csd19536kcs.pdf . Read overview and electrical table; local PDF/text retained.

[S2] ST STM32G474RE manufacturer product page: https://www.st.com/en/microcontrollers-microprocessors/stm32g474re.html . Direct ST PDF/page requests repeatedly timed out; browser unavailable (missing Chromium). Actual ST page body retrieved through https://r.jina.ai/https://www.st.com/en/microcontrollers-microprocessors/stm32g474re.html and retained as stm32g474re-proxy.txt. This verifies page-level features, not the full package datasheet or errata.

[S4] TI INA240 SBOS662C https://www.ti.com/lit/ds/symlink/ina240.pdf ; [S5] TI INA293 SBOS470B https://www.ti.com/lit/ds/symlink/ina293.pdf ; [S6] TI LM5164 SNVSAU4D https://www.ti.com/lit/ds/symlink/lm5164.pdf ; [S7] TI TLV181x/TLV182x SNOSDC8E https://www.ti.com/lit/ds/symlink/tlv1811.pdf . All downloaded from manufacturer, PDF-to-text converted and relevant features/limitations inspected. Exact suffixes not explicitly listed in CSV remain unresolved.

[S8] Infineon candidate source (fetch unsuccessful): https://www.infineon.com/assets/row/public/documents/24/49/infineon-ipp023n10n5-ds-en.pdf . An empty 202 response is not verification. No distributor stock, price, sourcing authenticity or lifecycle qualification was performed. Local efficiency_model.py regenerates model numbers and efficiency-budget.csv; candidate-bom.csv is a functional candidate list, not a purchase/assembly file.
