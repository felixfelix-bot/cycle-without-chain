# Autonomous protection circuit milestone — NOT SAFE TO ENERGIZE

> Superseded electrical verdict: [independent integration review](protection-integration-review.md).
> UNSAFE DRAFT. In particular the comparator output-low corner below is not the
> full-temperature limit; the *qualified* band is the 0.55 V-corner one, and
> neither band is a qualified limit at small input overdrive (see
> `analysis/cx/ov_threshold.py` and PROT-07).

## Delivered and bounded

10 native hierarchical sheets, 130 placed components, 452 mapped pins (previously 6/84/308). Four real circuit sheets now supply the safety rail, compare bus/rail/brake signals, retain a hardware fault and drive a bus-connected brake chopper. No PCB/routing. Human-powered conversion with a short buffer only; no range target. Bus 36–58.4 V remains provisional. **This is a reviewable circuit increment, not safety approval.**

## Circuit and primary-source identities

Primary PDFs were fetched and converted with pdftotext during design; links below are authoritative. The generator embeds complete numbered single-unit symbols, avoiding hidden power units.

* [RECOM R-78HB12-0.5](https://g.recomcdn.com/media/Datasheet/pdf/.fSx_VzyW/.t62b2d6a7acf719dba8f3/Datasheet-270/R-78HB-0_5.pdf): U3 pins 1 IN, 2 GND, 3 OUT. 17–72 V operation, 75 V absolute, 12 V/0.5 A. 3.3 uF/100 V input capacitor required above 50 V. Fitted 1 kohm preload consumes 12 mA/144 mW. Output capacitance including both driver bypass banks is below 100 uF. No hotplug/transient survival claim: protected entry is still mandatory.
* [TLV760](https://www.ti.com/lit/ds/symlink/tlv760.pdf): U4 TLV76033DBZR, pins 1 OUT, 2 IN, 3 GND. Safety3V3 from AUX12V, separate from external MCU rail. 100 mA maximum is not a thermal budget; 20 mA screening load dissipates 174 mW. U3 total includes bridge gate-charge consumption, which still needs PWM/current validation.
* [LM4040-N](https://www.ti.com/lit/ds/symlink/lm4040-n.pdf): U5 LM4040AIM3-2.5/NOPB, SOT23 pins 1 cathode, 2 anode, 3 tied to anode as permitted. 4.7 kohm bias from 12 V gives 2.02 mA; 100 nF bypass.
* [LM339B](https://www.ti.com/lit/ds/symlink/lm339b.pdf): U6 LM339BIDR. Supply3/GND12; output2 uses IN−4/IN+5 for OV. Output1 uses −6/+7 for AUX UV; output14 uses −8/+9 for MCU UV; output13 uses −10/+11 for brake loop. Open collectors for the last three form HEALTHY. Comparator inputs near 2.5 V are inside common mode at the 10 V AUX cutoff. LM339B, not legacy LM339, limits used: ±5.5 mV offset, 50 nA bias.
* [SN74HC00](https://www.ti.com/lit/ds/symlink/sn74hc00.pdf): U7 NAND pin pairs 1/2→3, 4/5→6, 9/10→8, 12/13→11, GND7/VCC14. RESET_N=NAND(HEALTHY,RESET_REQUEST); FAULT=NAND(HEALTHY,PERMIT); PERMIT=NAND(RESET_N,FAULT). Unused gate inputs grounded and output given a 100 kohm load (no floating input).
* [SN74HC11](https://www.ti.com/lit/ds/symlink/sn74hc11.pdf): U8 AND inputs 1/2/13→12 and 3/4/5→6 generate separate enable outputs; 9/10/11→8 supplies TIMER_BREAK_OK. Outputs require HEALTHY AND PERMIT AND MCU_ARM. Driver ENABLE pulldowns remain fitted; 1 kohm output resistors added.
* [TPS3823](https://www.ti.com/lit/ds/symlink/tps3823.pdf): U9 TPS3823-33DBVR pins 1 RESET_N,2 GND,3 MR_N,4 WDI,5 VDD. Its push-pull reset is diode-isolated, NOT shorted to the collector bus. WDI has a real 10 kohm pulldown because floating WDI disables watchdog operation. −40…85 °C reset threshold 2.86–3.00 V; startup delay and watchdog are not fast current trips. Watchdog timeout 0.9–2.5 s. Two driver nFAULT channels also diode-isolated by BAT54WS-7-F (cathode to source, anode HEALTHY); cold electrical verification of worst-case VOL plus diode drop is still required.
* [UCC27511](https://www.ti.com/lit/ds/symlink/ucc27511.pdf): U10 UCC27511DBVR pin1 VDD,2 OUTH,3 OUTL,4 GND,5 IN− grounded,6 IN+ OV_CMD. Independent 10 ohm turn-on and 2.2 ohm turn-off resistors feed Q13 gate; 10 kohm gate-source pulldown. Internal UVLO holds output low on inadequate supply. Q13 CSD19532Q5B source1–3/gate4/drain5 (KiCad electrical collapse of physical drain leads5–8 and exposed drain).

C22 GRM32-series input capacitor uses a 1210 candidate footprint, not the 0805 default. New signal resistor/capacitor values include exact candidate ordering codes in BOM. These are selections, not procurement/footprint qualification. Existing bridge passives and connectors remain provisional. External brake resistor is an assembly candidate, not a hidden on-board resistor or a populated PCB part.

## OV thresholds and timing

Comparator IN+ node: bus through 112k+113k, ground through 10k, positive feedback from OV_CMD through 330k; IN−=2.5 V. Output pullup 1k to Safety3V3. A 100 pF C0G sense capacitor suppresses very short spikes, not a large RC delay.

`Vbus_trip = Vref*(1+Rt/Rb+Rt/Rh) - Vout*Rt/Rh`.

Nominal turn-on **60.318 V**, turn-off **58.205 V**, hysteresis **2.114 V**. Budget: resistor 0.1% initial +25 ppm/K×50 K; reference 0.1%+100 ppm/K×50 K; ±5.5 mV comparator offset plus 50 nA×10k; output low corner and high ±4%.

**Qualified band, comparator output low 0–0.55 V** (the LM339B −40…85 °C VOL limit at ISINK ≤ 4 mA, VID = −1 V): turn-on **59.315–61.226 V**, turn-off **57.356–59.058 V**. Qualified minimum turn-on **59.315 V**, **0.915 V above the provisional 58.4 V bus maximum**. Recomputed by `analysis/cx/ov_threshold.py` (tests in `analysis/cx/test_ov_threshold.py`), which also reproduces the retired 0.4 V-corner figure below.

**Superseded, kept for the record:** the earlier exhaustive 64-corner arithmetic printed turn-on **59.417–61.226 V**, turn-off **57.356–59.058 V**, using an output-low corner of 0–0.4 V. That 0.4 V is the 25 °C VOL limit, not the −40…85 °C limit. Raising the low corner to 0.55 V moves the minimum turn-on down by **0.102 V** (= Rt/Rh × 0.15 V = 0.6788 × 0.15), so **59.417 V must not be quoted as a qualified bound** — this is the correction recorded in [the integration review](protection-integration-review.md) §P1, now applied here.

Both bands cover only a ±50 K excursion from calibration, **not** the entire component rated-temperature guarantee. Resistor tracking, aging and reference load regulation require closure (PROT-07). The sweep also assumes the datasheet VOL limit, which is specified at VID = −1 V, still holds at the ~0 V overdrive of the threshold itself; TI publishes no guaranteed VOL there, so even 59.315 V is a screening number rather than a datasheet-backed one. Output pullup loading at 3.3 V into 1 kΩ sinks ≤ 3.3 mA, inside the 4 mA test condition, and creates millivolt error below this screening allowance. Qualified minimum on threshold remains above provisional 58.4 V.

Sense Thevenin resistance ≈9.30 kohm, nominal RC≈0.93 us. LM339B propagation is overdrive-dependent; its typical 1 us must not be promoted to a guaranteed maximum. Reserve 10 us total comparator/filter/driver/gate turn-on as an **unverified design budget**, not a demonstrated hardware bound. At 500 W into the existing 100 uF, 60 V rises to **60.828 V in 10 us**, from sqrt(V²+2Pt/C). At 50 us it reaches 64.031 V. Ringing and cable energy are excluded. This is why 100 V MOSFET headroom does not close safety.

AUX divider30k/10k trips nominally at 10.0 V; MCU divider2k/10k trips at 3.0 V. There is deliberately no separate analog UV hysteresis: the fault memory retains excursions and prevents ordinary rail chatter re-enable. Reset must be a deliberate pulse; **holding RESET_REQUEST high causes rearm once HEALTHY returns**. Firmware/UI must not hold reset continuously; a future edge-qualified manual-reset circuit is a release requirement.

## Startup / fault / supply truth table

| Condition | Bridge permission | Autonomous sink |
|---|---|---|
| Power absent | pulldowns off | off; no energy sink |
| Safety3V3 starting / supervisor reset | HEALTHY low, fault set, off | enabled only after AUX/UCC UVLO and comparator/reference valid |
| Supplies good but no deliberate reset | retained fault, off | OV-responsive |
| Healthy + reset pulse + ARM | enabled | OV-responsive independently |
| Brake loop open / cable broken / MCU UV / AUX UV / either nFAULT / watchdog expiry | HEALTHY low, both enables low and latch set | remains OV-responsive if AUX/safety/reference still valid |
| Reset asserted during persistent fault | HEALTHY still forces enable low; fault wins externally | independent |
| Fault clears without reset | off, memory retained | independent |
| Bridge disable or MCU rail lost | off | still supplied from bus, independent of MCU |
| AUX or safety rail lost | intended off; sequencing/backfeed proof outstanding | **lost**: cannot promise clamp |

Brake loop is normally closed from Safety3V3 through brake and resistor thermal switches to BRAKE_LOOP; local 10k pulldown detects opens. TIMER_BREAK_OK is only an exported hardware signal until the real MCU BREAK connection is placed. ENABLE is not a fast short-circuit protection mechanism.

## External sink selection and derating

Candidate **two TE Connectivity HSC3004R7J (1-1630027-7), 4.7 ohm ±5%, 300 W chassis resistors in series**, documented by [manufacturer product page](https://te.com/en/product-1-1630027-7.html). Total9.4 ohm, minimum8.93 ohm. At 61.226 V, maximum current6.856 A and total419.8 W (209.9 W per equal low-tolerance resistor). At64 V, 7.167 A/458.7 W, 229.4 W each; at72 V,8.063 A/580.5 W,290.3 W each, nearly rating before temperature derating. A 10 s event at64 V deposits4.59 kJ total,2.29 kJ each. **No pulse-overload energy rating is claimed**; this is requested energy, not a qualified allowable energy.

The 300 W rating requires the specified heatsink and mounting conditions; it is NOT a free-air rating. Require verified heatsink thermal impedance, thermal-interface/mounting procedure, NC overtemperature loop, touch guarding, cable strain relief, DC-rated branch fuse and cable-inductance clamp. Until those exist, allowable dissipative power/energy is **unknown**. Even nominal 60 V sink is only383 W: it cannot hold an arbitrary500 W sustained source; the 500 W latency example is not a continuous sink specification. Continuous downhill envelope and BMS-opening energy remain unknown, with no road-ready claim.

## Driver pin-stress audit

[DRV8353 SLVSDY6A](https://www.ti.com/lit/ds/symlink/drv8353.pdf), pp10–11: VM actual12 V, recommended9–75 V/absolute80 V; old 75−58.4 arithmetic corrected to nominal75−12, not a transient margin. VDRAIN recommended up to100 V/absolute102 V and maximum2 V/us slew. SHx continuous limits −5 V to102 V AND ≤VDRAIN+5 V; GHx/SHx differential ≤16 V. 200 ns transient allowances must not be treated as continuous. SP/SN continuous ±1 V, transient ±5 V for200 ns, differential linear range±0.3 V. At30 A×2mohm=60 mV static shunt drop, but Kelvin-return spikes are unmeasured. VREF3.3 V is external; SO outputs may backfeed an unpowered MCU, and PWM/SPI/ARM/reset/WDI can backfeed unpowered safety logic. Supply sequencing isolation/clamps remain blockers. Neither this increment nor a clean netlist qualifies those stresses.

## Executed evidence and limits

* Test-first `test_protection.py` initially failed import (saved protection-tests-red.txt); new calculations and latch truth table then pass. Separate VM expectation failed old arithmetic (vm-tests-red.txt), then corrected calculation passes. Full current unittest suite: **8 passed**.
* Real **ngspice42** transient run, `ngspice -b protection_transient.cir -o exports/protection-spice.log`: **80,086 solved rows**. Exact passive OV divider/RC plus ideal behavioral comparator/open-collector and delayed NAND logic: rise60.33114 V, fall58.20219 V; enabled3.3 V before fault;0 V during simultaneous reset/fault;0 V after fault clears without reset;3.3 V after deliberate rearm; OV output3.298251 V while bridges disabled. This is **NOT vendor transistor-model simulation**, not a switching power/thermal/EMI/UVLO model, and not hardware timing proof.
* Native KiCad export loaded all10 pages, netlist/PDF/SVG refreshed. Native ERC `--exit-code-violations`: **exit5, three real undriven-power errors**: external MCU VREF supply, PGND external return, DC_LINK external input. No waiver or fabricated power flags. No dangling-signal warnings after tying the unused NAND load. Nonempty artifacts retained.
* Existing verify_exports/export_artifacts scripts intentionally untouched (owned by parallel verifier worker). Their old count expectations are stale for this milestone; do not treat prior verification.json as evidence for this head. Parent integration must regenerate independent validation and confirm exact endpoint sets.

## Release blockers and review debt

Protected entry fuse/reverse/regen isolation/precharge/disconnect/discharge; storage chemistry/BMS charge acceptance; real MCU/pin mux/ADC conditioning/position and thermal sensors; fast overcurrent trip; reset edge qualification; logic power-sequence/backfeed and low-voltage brownout behavior; resistor heatsink/fuse/clamp/energy rating; qualified footprints and pin geometry; auxiliary transient and full current/thermal budget; measured comparator worst-case delay; independent cross-family PCB reviewer and consultant gates. **No energize, fabrication or road-use permission.** Parent review/merge only; publication is an unfinished design milestone.
