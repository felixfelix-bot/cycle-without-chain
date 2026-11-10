# Independent FSR consolidation review — 2026-11-10

**Accept as a documented, unqualified design milestone only. NOT safe to energize,
fabricate, or ride. No cross-model-family electrical approval is claimed: the
reviewer's actual model family was not established.**

Reviewed feature `44d3d9fc2c542bccb24466b791668cd05a88fadd`, merged onto
`aebd795` (published master including README/use-case, gyro and precharge work).
This review changes no entry circuit, firmware, or protection design.

## Independent electrical findings

The native schematic was exported again with KiCad 9.0.9, including a separate
XML netlist parsed with Python ElementTree rather than the generator/checker's
S-expression parser. Exact OPA and mux endpoints, supplies, connector separation
and MCU endpoints were checked in that XML. BOM values/footprints agree:
U26/U28 OPA333AIDBVR SOT-23-5; U27/U29 TMUX1511PWR TSSOP-14.

Primary documents were independently retrieved, not accepted from the feature's
prose alone: [OPA333 SBOS351E](https://www.ti.com/lit/ds/symlink/opa333.pdf),
[TMUX1511 SCDS390B](https://www.ti.com/lit/ds/symlink/tmux1511.pdf), and
[Interlink integration guide](https://media.digikey.com/pdf/Data%20Sheets/Interlink%20Electronics.PDF/FSR_Integration_Guide.pdf).
Manufacturer [400-series data sheet](https://interlinkelectronics.com/downloads/datasheets/fsr-400-series-datasheet.pdf)
indexed text independently confirms 34-00018 = 402 short-tail with female contacts
and housing, 12.70 mm active diameter. This is not connector-mate verification.

- **Excitation/contact:** actual 10k excitation + 1k return + 10k measuring
  divider gives 0.15714 mA at zero sensor resistance, 1.57143 V sense and about
  1.42799 V ADC. A return-to-ground fault bypassing return/measurement is bounded
  by 3.465 V / 9.9k = 0.350 mA under the stated tolerances. Interlink explicitly
  requires less than 1 mA/cm² of actual actuator contact; therefore contact must
  exceed 0.350 cm². Nominal pad diameter is not proof. This bound excludes a
  shorted excitation resistor or externally driven cable.
- **OPA:** DBV pins 1 OUT, 2 V−, 3 +IN, 4 −IN, 5 V+ match the actual netlist.
  OUT and −IN share BUF; the 10k input resistor is between SENSE and +IN.
  Powered common-mode range includes ground through V+ + 0.1 V; it does not
  authorize unpowered drive. The table's ±1 mA input stress limit is stricter
  than its 10 mA footnote; use the stricter value. The 10k limits a 3.465 V
  retained-capacitor discharge to 0.350 mA with −1% tolerance, not zero backfeed.
  Full-temperature output swing is 70 mV from rails for the specified 10k load,
  not guaranteed precision at zero. Actual load is about 11k to ground, whereas
  the table default is midpoint referenced. The 1k outside feedback isolates
  the ADC capacitor; stability, startup and acquisition remain unmeasured.
- **Mux/off ADC:** TSSOP pin assignments match. TI explicitly specifies 0–3.6 V
  signal operation at VDD <1.5 V and powered-off protection; ±2 µA, not the
  25°C-only 10 nA, is the conservative published powered-off leakage limit.
  A 10k bleed gives 20 mV nominal / 20.2 mV at +1%. The grounded-drain test is
  not a complete dead-MCU injection guarantee. Other leakage, rail ramps and
  retained 100n charge remain relevant (nominal discharge time constant 1 ms).
- **Actual source, not an imagined reference driver:** J2.1 supplies
  LOGIC3V3_EXT externally. R68 (0R) connects it to MCU_VREF; U17.36, both OPA
  supplies, both excitations, C50/C51/C80/C84 and D40/D43 clamp cathodes share
  MCU_VREF. R67 separately links MCU_VDDA/U17.37. Both mux VDD pins use
  LOGIC3V3_EXT. No qualified regulator/reference source or rail sink is added.
  At nominal rail, zero-resistance sensors and 28 µA per OPA quiescent allowance,
  the two frontend paths alone draw approximately 0.656 mA from MCU_VREF
  (sensor currents plus buffer output load plus IQ); this is NOT a worst-case
  system budget. ADC/reference dynamic load, tolerance, capacitor charging,
  startup, clamp current and external source regulation remain unqualified.
  Five power ERC errors must not be dismissed as a harmless flag omission.
- **Out-of-range faults:** PESD3V3U1UL and BAT54S candidates do not establish
  safe clamping at downstream absolute maxima. BAT54S can inject MCU_VREF;
  there is no established sink. External negative/overvoltage/ESD and sustained
  traction-battery shorts are NOT qualified or safely contained by this design.

## Brake authority and preserved circuits

J44/J45 are now ground1/switch2 only; J46/J47 carry the separate FSR excitation
and return. Reusing the old Hall harness is incompatible. U17.26/.34 retain
switch ADCs; .18/.25 receive FSR ADCs; PE5/.4 drives common mux enable.
All **36 motor Hall net endpoints** compared with pre-merge master remain
identical. Motor commutation Hall is not rider modulation.

The existing brake-state model retains its historical field name `hall`; it is
a normalized analog input, not FSR ADC firmware. Its plausibility check makes
asserted binary braking with zero analog a latched fault, prohibiting positive
torque. The separate FSR `inhibit` predicate ignores analog entirely. These are
executable contracts ONLY: there is no firmware implementation or independent
hardware positive-torque sign guard. Invalid modulation may remove electrical
braking; independent mechanical braking remains essential.

## Execution evidence and limits

Fresh runs in the integration worktree:

| Gate | Normal | Python `-O` |
|---|---:|---:|
| Hardware `unittest discover -s tests -v` | 32 passed, 128.362 s | 32 passed, 110.565 s |
| FSR analysis `unittest discover -s analysis/fsr -v` | 12 passed | 12 passed |
| Brake-state `unittest discover -s analysis/brake_intent -v` | 8 passed | 8 passed |

Hardware tests include actual-netlist FSR endpoint/value mutations and legacy
rider-Hall rejection, independent brake/MCU topology controls and malformed
export negative controls. These passed in both modes; they are not analog
simulation or physical fault injection.

A scratch copy ran `python3 export_artifacts.py` with actual native netlist,
PDF and SVG exports: **314 components, 181 connected nets, 956 endpoints,
51 explicit NCs, 27 pages**. Strict native ERC was explicitly run by that script:
**exit 5; five errors, zero warnings** (U1.24, U1.25, U3.1, U17.37,
U26.5/MCU_VREF). Export script exit zero does not mean ERC passed.
Local scratch evidence: `~/.hermes/profiles/manager/cache/scratch/fsr-review/`
(`export.log`, `independent.xml`, downloaded PDFs/text, regenerated artifacts).
Scratch is temporary, not a permanent remote artifact promise.

**Readability finding:** fresh PDF page 24 was actually rasterized with
`pdftoppm` and visually inspected. The sheet is not cropped, but J46 and
U26/U27 labels overlap pin graphics; passive value/reference fields lie over
vertical wiring. Thus visual-legibility approval is **withheld**. This is a
shared field-placement issue, not justification for a broad generator/layout
rewrite in this bounded electrical consolidation. Native files/netlist remain
reviewable; fix and re-render layout before a fabrication-facing release.

## Open release gates

Keep all existing blockers: external source/reference loading and sequencing;
five ERC errors; real ADC acquisition/dead-rail limits; buffer stability and
startup; worst-temperature leakage and ESD coordination; battery-short exclusion
or rated protection; actual mounted contact and load/unload calibration;
mechanical noninterference and connector retention; implemented/tested firmware
and torque arbitration; visual layout; precharge sequencing and independent
energy/thermal/storage qualification. No measured force accuracy, EMC result,
ride authorization, or safety certification is inferred from the passing tests.
