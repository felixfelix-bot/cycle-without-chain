# Rev A milestone — PROTOTYPE / NOT FAB READY / DO NOT ENERGIZE

This is a partial, electrically connected two-bridge schematic, not a completed powerboard. No purchases, frame modification, PCB routing or hardware tests occurred. No achieved efficiency claim.

## Verified milestone

KiCad 9.0.9 loads all six hierarchical pages and exports PDF, six SVGs and XML netlist. `python3 export_artifacts.py` verifies 84 components, 80 nets, 308 expected pin assignments, two DRV8353S drivers and twelve MOSFETs. ERC: **3 errors, zero warnings**, unsuppressed undriven external AUX12V, LOGIC3V3, PGND power inputs. This count does not prove safety. Exported connectivity is compared with the generator's manifest (consistency check, not independent electrical review).

`python3 -m unittest discover -s tests -v`: four tests pass. Tests were executed before implementation: import failure recorded in exports/tests-red.txt; green run in exports/tests-green.txt. calculations.py is screening arithmetic, NOT SPICE or switched transient simulation. It reports 13.89A bus at 500W/36V, 1.8W shunt at 30A, 0.45–2.85V ideal current-sense swing, 7.2ohm/5000J example dump requirement. These do not select real safety parts or imply continuous phase-current qualification.

## Exact release blockers

- Protection/power-entry sheet is a boundary, not fitted fuse/precharge/reverse protection/contactors.
- Independent comparator/latch/watchdog/brake inhibit and OV chopper are **not implemented**; reviewed candidates are in docs/safety-review.md, not protection that may be relied upon.
- Auxiliary buck and rail supervision absent; external interfaces only. Pulldowns hold driver ENABLE and gates low nominally but do not establish safe power sequencing or fault coverage.
- MCU not placed/wired. LQFP100 allocation has 32 unique signal pins, but latest errata, RM0440 trigger matrix/register configuration and real dual-loop deadlines remain open. Sequential ADC sampling is explicit, not simultaneous sampling.
- Storage/BMS selected chemistry, bidirectional acceptance, safe isolation and full/absent-pack back-EMF handling remain open. Gate-disable alone cannot stop diode rectification.
- No qualified bus clamp/overshoot analysis: VM recommended 75V, despite 100V MOSFET VDS/driver VDRAIN ratings. 58.4V static margin is not transient proof.
- Driver footprint and all thermal, Kelvin routing, capacitor ripple, connector, fuse interrupt and chopper energy qualifications remain open. BOM is review-only, not procurement-ready.

## Review instructions / next coherent increment

Open powerboard-reva.kicad_pro then root schematic, or exports/powerboard-reva.pdf. Compare pin-map.csv with TI source and exported netlist. Read README.md and docs/safety-review.md before interpreting external connector names. Next implement and review independent inhibit/chopper plus auxiliary rails; then MCU and sample timing, then complete storage/power-entry. Do not route before safety schematic approval. Parent reviews and merges this honest partial milestone plus inherited concept into default branch; this worktree must not independently merge concurrent work.

## Balloon tooling adaptation (read-only inspection)

Inspected ~/repos/balloon-fresh at **2c05171da269862018f906f5aa0fde2648d76d8f**, especially `tracker/hardware/output/verify_placement_v7.py` lines 1–90 and `docs/HANDOVER-QUOTA-GATES-DRC-CLEANUP.md` lines 64–97. Relevant practices: enumerate actual loaded objects, record per-gate evidence, separate valid file/export success from connectivity/clearance acceptance, gate placement before routing. Adapted here as explicit component/net/pin counts and exported-net verification, retaining ERC failures rather than calling a loadable artifact safe. Historical balloon output had hundreds of DRC faults despite export success: export is not release. No balloon files modified. Did NOT copy RF board's 1mm pad-center spacing, 5mm decoupling distance, board dimensions, copper rules or historical Python/headless claims; motor power layout needs independent creepage, thermal, commutation-loop and Kelvin limits.

## Genuine operator inputs (do not block publishing draft)

Operator has confirmed **human-powered first**, with storage only buffering starts/stops and short deficits, not powered range. Mass/hills/country/tyres/budget remain unknown, not inferred from asynchronous messages.

1. Storage: size for that short-buffer duty rather than powered range; recommend freeze one pack chemistry/voltage/BMS specification before power-entry freeze; 13s Li-ion lowers maximum bus relative to 16s LFP but only acceptable with documented regen charge acceptance. Need pack/BMS model or permission to design around a provisional bench supply plus external dump only.
2. Energy envelope: agree maximum rider power, overspeed/downhill duration and permitted resistor heat/location; recommend initially current-limited stationary bench only, no road tests.
3. Mechanics: frame/dropout measurements and material plus generator mounting photos needed before fit/fabrication. Recommend reversible clamp and full gear guard, retain both mechanical brakes. No universal clamp torque or frame modification assumed.
