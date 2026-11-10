# Selected FSR implementation — unqualified bench candidate

Primary exact-package pin evidence: [electrical review](../../../docs/design/fsr-electrical-evidence.md), TI SBOS351E (OPA333 DBV) and SCDS390B (TMUX1511 PW). Do not substitute DCK/QFN pinouts. `fsr_circuit.py` embeds exact custom symbols in `Powerboard.kicad_sym` and generated sheets.

- LEFT: J46, U26 OPA333AIDBVR, U27 TMUX1511PWR, U17.18 PC3 ADC12_IN9.
- RIGHT: J47, U28 OPA333AIDBVR, U29 TMUX1511PWR, U17.25 PA3 ADC1_IN4.
- J46/J47 logical pin1 excitation, pin2 return, external Interlink 34-00018 sensor between them. Connector mating part is NOT selected. Sensor is offboard, not a fictitious PCB component.
- Each: MCU_VREF → 10k 1% excitation → sensor → 1k 1% return → SENSE; 10k 0.1% and 100n from SENSE to PGND; 10k 1% from SENSE to OPA +IN3. OUT1 and −IN4 have direct local feedback. V+5=MCU_VREF, V−2=PGND, 100n bypass.
- TMUX S1=2 buffer, D1=3 isolation output, SEL1=1 FSR_SAMPLE_ENABLE; VDD14=LOGIC3V3_EXT, GND7=PGND, 100n bypass. SEL2/3/4 pins4/10/13 grounded; pins5/6/8/9/11/12 explicit NC. Each select has 100k pulldown (50k combined common-enable load).
- Post-mux: 1k series then FSR_ADC, with 10k bleed and 100n reservoir to PGND. ADC capacitance is outside the buffer feedback loop.
- Shared enable=U17.4 PE5, formerly unused; exact-package native symbol confirms physical pad. Default low; firmware must enable only with valid rail/reference, blank at least assumed 20ms, and establish settling/plausibility. No firmware or supervisor guarantee exists.
- Existing 0R links connect MCU_VREF and MCU_VDDA to LOGIC3V3_EXT. Excitation deliberately uses the actual ADC reference net; no new unsourced rail or ground alias is invented. PGND common is NOT galvanic isolation.
- J44/J45 now contain ONLY binary switch ground1/signal2. Their switch bias, ADC filtering, clamps, offboard EOL, MCU pads and policy are retained. This is a harness pinout change from the old four-wire alternative; do not reuse the old Hall harness.
- D38/D39 and D41/D42 are connector PESD3V3U1UL candidates (cathode1 cable/anode2 ground). D40/D43 BAT54S candidates clamp SENSE (junction3) toward PGND anode1 / MCU_VREF cathode2. These are real circuit connections, not qualified transient protection. In particular they can backfeed the reference rail; no rail sink is implemented. Worst leakage/temperature, clamp voltage and transient coordination are open gates.

**Battery short is a release blocker.** Neither these diodes nor 0805 resistors, OPA333 or TMUX1511 make a traction-battery cable fault safe. Only segregated current-limited low-voltage frontend bench work is in scope, with no external cable driver. This is not authorization to energize the powerboard or manipulate entry connectors. Entry was not redesigned. Parent design documentation owns the detailed powered-off/backfeed assessment.

Binary braking is authoritative in the proposed firmware contract: zero/open/invalid FSR must never grant propulsion over a binary assertion. The actual board has no independent positive-torque sign guard; this milestone does not invent one. Mechanical braking remains independent.

## Reproduced evidence

`python3 export_artifacts.py`: native netlist/PDF/SVG exported; checker passes consistency with 314 components, 181 connected nets, 956 connected endpoints, 51 explicit NC endpoints, 27 pages. Root grid expanded to three columns to keep the extra sheets on A1. Obsolete rider-Hall SVGs removed; GEN/HUB commutation Hall circuits remain intentionally.

- `python3 -m unittest discover -s tests -v`: 32 passed, 112.912s (`exports/fsr-tests.txt`).
- `python3 -O -m unittest discover -s tests -v`: 32 passed, 110.970s (`exports/fsr-tests-O.txt`).
- New exact pin/passive/connector/legacy topology tests include every FSR signal/IC/ESD endpoint mutation. Initial missing-circuit RED retained as `exports/fsr-red.txt`; duplicate common-enable termination blind spot was discovered and corrected before final GREEN.
- Strict native ERC: `kicad-cli sch erc --format json --exit-code-violations -o exports/fsr-erc-strict.json powerboard-reva.kicad_sch` returns **5**. **Five unresolved power_pin_not_driven errors, zero warnings**: U1.24 VREF, U1.25 AGND, U3.1 IN, U17.37 VDDA, new U26.5 V+ on MCU_VREF. No flags, suppression or waiver added. `exports/fsr-erc-exit.txt` records exit status. Export/checker success means artifact consistency, NOT ERC clean.

No new FSR vendor-model SPICE, physical measurement, acquisition/settling, ESD/battery-fault, visual legibility review or mechanical testing was performed. Existing non-FSR ideal-model SPICE tests are not FSR qualification. No fabrication or riding release.
