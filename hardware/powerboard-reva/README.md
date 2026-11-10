# Powerboard Rev A — populated, partial schematic milestone

**NOT SAFE TO ENERGIZE. NOT FABRICATION-READY. No PCB, routing, procurement or riding authorization.**

Open `powerboard-reva.kicad_pro` or root `powerboard-reva.kicad_sch` in KiCad 9. The root references fourteen real child sheets. Nets join electrically through explicitly named global labels; GEN_ and HUB_ prefixes separate bridge/control signals. This is not a block-diagram-only drawing or connector substitution for ICs.

## Current MCU milestone (supersedes counts and missing-MCU statements below)

See [MCU milestone](../../docs/design/mcu-milestone.md): real STM32G474VET6 circuit, 15 pages, 199 components, 642 connected endpoints and 45 explicit NC pins. Native ERC: four unresolved errors, zero warnings. Firmware, fast overcurrent trip, protected entry, storage acceptance and sequencing remain blockers. Historical sections below are not current status.

## Current protection integration — UNSAFE DRAFT

The sections below record the **earlier six-page milestone**, not current counts.
Current integration has 10 pages, 130 components, 104 nets and 452 endpoints;
VM now uses bus-fed AUX12V. Four added protection sheets remain unqualified.
See [independent integration review](../../docs/design/protection-integration-review.md)
for current evidence and prioritized blockers. ERC still has three errors
(U1.24 VREF, U1.25 AGND, U3.1 DC_LINK). No release approval.

## Implemented (historical six-page milestone)

- Two **DRV8353SRTAT** SPI drivers, 40 signal pins plus exposed pad, from TI SLVSDY6A pp6–7.
- Twelve **CSD19532Q5B** MOSFETs using embedded, inheritance-resolved stock KiCad symbols; three half-bridges per machine.
- Twelve provisional 4R7 gate resistors and twelve 100k gate-source pull-downs.
- Six 2mOhm low-side shunts, each wired to the corresponding SPx input and low-side sources; SNx to PGND. Kelvin layout is mandatory and not yet implemented.
- Driver charge-pump, regulator and supply capacitors; ENABLE pull-downs; SPI SDO/nSCS and fault pull-ups.
- Six provisional local 1uF/100V bus ceramics and one provisional 100uF/100V bulk capacitor.
- Eleven explicitly external connectors for machine phases, protected DC input, regulated supplies, independent enable chain, MCU PWM/SPI/ADC.

VM deliberately uses externally regulated 12V; VDRAIN senses the shared bus. VREF is 3.3V, **not** 1.65V: CSA midpoint comes from internal VREF/2. Gain20 and driver protection configuration require software plus hardware review; no configuration is implied by the drawing.

## Executed verification (KiCad CLI 9.0.9)

Run `python3 export_artifacts.py` from this directory. Python standard library and installed KiCad symbol libraries are sufficient; no SKiDL runtime required. Direct native schematic generation was used to deliver loadable drawings, not only a netlist.

- Six loadable hierarchical pages: root, GEN driver, GEN bridge, HUB driver, HUB bridge, external boundaries.
- **84 components, 80 exported nets, 308 pin assignments** checked against the actual KiCad-exported netlist by `verify_exports.py`.
- Actual six-page PDF: `exports/powerboard-reva.pdf`.
- Six nonempty SVG pages: `exports/svg/`.
- Actual netlist: `exports/powerboard-reva.net`.
- Actual ERC: `exports/erc.rpt` — **3 errors, 0 warnings**, all `power_pin_not_driven` for external AUX12V_EXT, LOGIC3V3_EXT and PGND supply boundary. No PWR_FLAG or waiver masks these unresolved boundaries. CLI exiting zero is not a clean ERC verdict.
- Machine-readable counts: `exports/verification.json`; component list `review-bom.csv`; exact mapping `pin-net-map.csv`.
- PDF bridge page visually inspected: real populated circuit visible, no clipping/major block overlaps, but dense local MOSFET labels need drawing cleanup before formal review.

## Explicit release blockers

This intentionally **does not implement** the complete eight-sheet concept. Missing: fused/reverse-protected/precharged power entry, DC contactor and discharge, independent OV comparator/chopper/resistor/thermal cutout, current comparator and latched fault chain, brake interlock, watchdog, UVLO, auxiliary buck/3V3 rails, bus-current INA240 circuit, MCU/SWD/timer/ADC mux, Hall/encoder/temperature interfaces and storage/BMS acceptance logic. No optional storage DC/DC exists.

External connectors are interface contracts for those unfinished circuits, **not evidence that they exist**. ENABLE pull-downs and integrated driver OCP are not a complete safety system. PM machines can charge the bus through body diodes even with all gates off. No validated thermal/ripple/transient model, source interrupt ratings, EMC review or full-energy test exists.

DRV footprint is deliberately blank pending exact RTA land-pattern/thermal-pad verification (pad41 is a schematic convention). Many passive and connector footprints are unselected. Stock MOSFET and shunt footprints are candidate mappings, not fabrication qualification. Gate resistances, capacitor values and connector pin orders are provisional, not an orderable BOM. No unselected safety part is disguised as a DNP implementation.

Independent review must validate electrical and physical pin maps against primary package drawings, supply sequencing/back-powering, CSA calibration/PWM sampling, gate drive/current/OCP settings and all safety failure modes. Then close ERC and protection design before any layout release. Reviewers should retain the honest partial status even though all connectivity assertions pass.
