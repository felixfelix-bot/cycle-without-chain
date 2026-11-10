# FSR circuit milestone — reviewable, NOT safe to energize

Replaces rider Hall modulation with two Interlink 402 short-tail **34-00018** FSR inputs. Motor commutation Hall interfaces remain unrelated. Rider Hall is an optional future alternative, not a fitted default. Binary lever switches remain independent and authoritative in the **control model only**; no torque-sign hardware guard exists and all firmware remains unimplemented. Mechanical brakes remain essential.

## Implemented deliverables

`hardware/powerboard-reva/fsr_circuit.py` generates actual OPA333AIDBVR/TMUX1511PWR channels, candidate ESD/clamps and J46/J47 FSR connectors. J44/J45 are now two-pin binary-switch connectors: old harness pinout is incompatible. Exact DBV/PW pin maps and primary-source limits: [electrical evidence](fsr-electrical-evidence.md). Circuit details: [implementation](../../hardware/powerboard-reva/docs/fsr-implementation.md).

Usable next-stage review inputs are `review-bom.csv`, `pin-net-map.csv`, `exports/powerboard-reva.net`, `exports/powerboard-reva.pdf` and native KiCad sheets under `hardware/powerboard-reva/`. No PCB/fabrication output or entry-stage redesign.

10k excitation limits a return-to-ground low-voltage fault to 0.350 mA under assumed +5% rail and −1% resistance, rather than the study's unsafe 3.3 mA case. Normal short-end sensor current is 0.157 mA. Actual contact must exceed 0.350 cm² for that fault bound under Interlink's <1 mA/cm² rule; a nominal 10 mm pad is not proof of contact. Mounted geometry and force range remain unknown calibration gates.

## Analog model and diagnosis

`python3 analysis/fsr/implemented.py` regenerates the ideal DC/first-order results in `exports/fsr-calculations.json`: sense=3.3×10k/(RFSR+21k), ADC=sense×10k/(11k+4.5). Short ADC=1.427987 V; open ideal=0. OPA low-rail swing means very low readings are not precision measurements. No invented force-resistance curve and no SPICE qualification.

Sense RC ≤1 ms nominal; ideal half-LSB settling for a full-scale 12-bit step is ln(8192)×1 ms=9.011 ms. ADC RC≈91.28 µs. Proposed 20 ms startup/enable blanking is only a firmware hypothesis: resistor/capacitor tolerances, OPA startup/load/stability, ADC acquisition and brownout must be measured. OPA 100 µs startup is typical at 5 V, not a guaranteed 3.3 V deadline. 1k outside feedback isolates its 100nF load. TMUX powered-off protection really is specified for 0–3.6 V; full-temperature 2 µA leakage into 10k bleed budgets ≈20.2 mV, not zero injection. Disable discharge tau=1 ms.

Open cable and unloaded FSR are indistinguishable at the low band; short and extreme low resistance may overlap at the high band. Classify both as **ambiguous/invalid modulation until mounted calibration and binary-switch plausibility**. Do not claim complete open/short detection. Firmware must never turn an invalid analog value into propulsion permission. Sensor short to excitation/ground, stuck ADC, leakage, slow ramps and broken measuring resistor require injection tests; credible-but-wrong values remain possible.

## Why no Wheatstone/R–2R

The study compares divider, bridge, conductance and switchable ranges. A one-active-arm bridge offers no true sensor temperature cancellation; gain4 only covers roughly 6.1–16.4kΩ before clipping in the historical example. R–2R creates a DAC, not a nonlinear-FSR linearizer. Neither fixes creep/hysteresis. Provisionally retain the simpler divider/buffer and calibrated lookup. No extra calibration header is necessary at this milestone; disconnected sensor connector can support controlled bench resistance substitution, not live-vehicle jumper instructions.

## Verification and explicit failures

Hardware suites: **32 passed normal and 32 passed `-O`**, including endpoint/value/topology mutations; logs `exports/fsr-tests.txt` and `fsr-tests-O.txt`. Export checker independently rerun: **314 components, 181 nets, 956 endpoints, 51 NCs, 27 SVG/PDF pages**. Native strict ERC: **5 errors, 0 warnings, exit5**, no suppression: U1.24, U1.25, U3.1, U17.37 and newly exposed U26.5/MCU_VREF undriven supply. Five are not a clean ERC. `fsr-erc-strict.json` is the exact report. New DC/RC tests supplement the historical nine FSR study tests. No physical verification, EMC result, force measurement or visual-legibility signoff.

## Remaining gates (not optional)

- **Hardware:** resolve five ERC supply errors; qualify MCU_VREF source/load/ramp, ADC limits/acquisition/injection, rail clamps/sink, dead-rail backfeed and sequencing. BAT54S secondary clamps can backfeed MCU_VREF. Candidate PESD3V3U1UL is not an ADC-rail limiter; coordinate pulse clamping, negative pulses, leakage and energy with downstream abs-max limits. Protection is wired but NOT qualified safe under ESD.
- **Battery-short:** explicit release blocker. Neither small resistors, TVS, OPA nor TMUX proves continuous traction-battery fault tolerance. Require rated isolation/current/power/energy analysis and testing, or reviewed physical exclusion. No ride/vehicle energization authorization.
- **Mechanical/calibration:** validate connector mate, retention, wet/dry cover, non-jamming detached pad, full friction-brake travel, true contact area, multiple mounted load/unload cycles, creep, temperature, gloves and finger position. Full-range force calibration requires actual mounted sensors; no precision force claim.
- **Firmware:** all unimplemented—binary authority, valid-state gating, startup blanking, ADC scheduling/calibration, disagreement/open/short plausibility, torque arbitration, regen limits, sink permission, watchdog/fault behavior. Python contracts do not implement these.
- **Energy:** precharge sequencing remains next separate task; independent chopper thermal/duty/energy qualification, storage charge acceptance, BMS opening and bus overshoot remain unresolved system gates. FSR completion does not close them.

## Cost policy / bounded scope

Cheapest feasible baseline; safety cannot be traded away and no numeric budget cap exists. The divider plus buffer is the provisional complexity baseline, **not a verified globally cheapest BOM**. Baseline 2×34-00018, 2×OPA333, 2×TMUX1511 plus passives/protection: supplier-verified total **unknown**. Optional bridge/PGA, range switching or higher-resolution ADC prices **unknown**, incremental force-resolution benefit **unmeasured**; not fitted. One shared quad TMUX could reduce IC count from two to one, but routing/common-cause trade and actual price saving remain unverified; defer. Require verified supplier quotes and quantified benefit before upgrades. No guessed prices.

Thin road tyres and recalled 9 bar do not establish ETRTO or a pressure recommendation. No tyre sizing or pressure inference enters this circuit milestone.
