# Rev-A safety candidate review

**Research only — unfinished circuit, not fabrication/purchase approval.** 2026-11-10. Read against [the concept](../../../docs/evaluation/custom-powerboard-concept.md): 36–58.4 V normal bus; provisional chopper onset 60 V and bridge inhibit 65 V. These are design targets, not demonstrated limits. Primary TI PDFs below were downloaded with `curl -fL` and converted with `pdftotext -layout`; component behavior is sourced, proposed interconnections are engineering requirements, not implemented/verified circuitry.

## Candidate decisions

| Function | Primary-source findings | Proposed use / unresolved work |
|---|---|---|
| External watchdog: **TPS3431** | 1.8–6.5 V supply; WDI requires falling edges before timeout. WDO is open-drain, active-low and asserts for a reset-delay interval, not indefinitely. EN low or SET1 low can disable monitoring. WDO is undefined below POR.[1] | Use 3.3 V supply and pull-up; translate WDO assertion into a persistent hardware fault. Strap EN/SET1 for enabled operation, not MCU-controlled bypass. Heartbeat must represent completed control/safety work, not an autonomous timer. Select CWD/timeout from worst-case detection-to-safe-state budget; startup grace and watchdog failure tests remain open. This is not a window watchdog or a brownout supervisor. |
| Fault memory: **SN74LVC2G02**, two cross-coupled NOR gates | Each gate outputs high only when both inputs are low; Ioff support does not establish a defined power-up latch state.[2] | Candidate SR latch at 3.3 V, **not a complete safety latch**. Normalize active-low watchdog/driver faults through defined polarity logic. For `Q=FAULT`, `Q=NOR(RESET,Qbar)`, `Qbar=NOR(SET,Q)`: SET=1/RESET=0 faults; 0/0 holds; 0/1 clears; 1/1 is forbidden. Add hardware reset interlock that blocks RESET while any fault persists; prove timing/race behavior. Supply supervisor must assert SET and independently inhibit bridges until rails valid. Exact inversion, OR-combination, reset-priority logic and supervisor are unselected. |
| OV detection: **TLV1702** dual comparator | 2.2–36 V supply, rail-to-rail input range, open-collector outputs. Offset maximum ±5.5 mV over temperature; 460/560 ns propagation figures are **typical**, not guaranteed worst-case shutdown bounds.[3] | One channel requests autonomous chopper, another sets bridge-inhibit latch. Run from protected auxiliary rail, never directly from 58.4 V bus. Separate divided bus inputs and explicit hysteresis/filtering required. Two channels in one package/shared rail/reference are not independent fault domains. Verify output-low voltage versus receiving logic thresholds at chosen pull-up current; direct LVC compatibility is not established. |
| Reference: **REF3330** (REF33 family) | 3.0 V option; ±0.15% initial accuracy, 30 ppm/°C maximum drift. Recommended VIN is VOUT+0.2 V to 5.5 V.[7] | Prefer qualified 5 V safety supply to relying on a marginal 3.3 V rail. Check load, startup, decoupling and reference-loss response. Ignoring hysteresis/loading, `Vtrip=Vref*(1+Rtop/Rbottom)` gives ratios 19 for 60 V and 20.667 for 65 V; these are arithmetic starting points, **not selected resistor values**. |
| Chopper gate driver: **UCC27511** | 4.5–18 V supply, dual inverting/noninverting input arrangement and outputs held low during supply UVLO.[6] | Candidate 12 V driver for low-side dump MOSFET: bus → resistor → MOSFET → return. Define comparator polarity/pull-up, gate resistor and gate-source pulldown; comparator output must not leave the MOSFET in linear operation. MOSFET, resistor, thermal switch and independent safety-rail implementation remain unselected. UVLO turns the sink off: it does **not** make a generating bus safe. |

TPS3431 Rev A has inconsistent below-minimum-supply wording between Table 7-1 and §7.4.2; do not use WDO as the sole rail-good indication. Resolve against TI and test power ramps/brownouts; independent rail supervision is required regardless.[1]

## Brake inhibit and restart contract (proposed)

- Both mechanical brakes remain mechanically effective without electricity. Each electrical brake switch must reach a **hardwired torque-inhibit path**, not merely an MCU GPIO; an open-wire-to-inhibit loop is preferable, with short-to-supply/ground faults assessed separately.
- Proposed permission: `BRIDGE_ENABLE = MCU_ARM AND RAILS_OK AND BRAKES_RELEASED AND NOT FAULT_LATCH`. Brake assertion must directly force both DRV8353 ENABLE pins low and assert both MCU timer BREAK inputs; exact mux is owned by the separate MCU review. The autonomous chopper must **not** be disabled by this bridge-inhibit chain.
- For initial low-energy bring-up, latch brake assertion as well as watchdog, OV, overcurrent and driver fault. Brake release alone must not restart torque. Manual deliberate re-arm only after fault clearance, zero torque request and validated rails/sensors; riding brake-release policy remains a human-factors decision.
- Pull ENABLE low when safety logic is unpowered; do not wire push-pull outputs together. Specify safe power-up latch initialization and safe loss-of-rail state independently of firmware. NOR latch alone does not provide either.
- DRV8353 ENABLE low enters sleep after its specified timing, disables gates and resets registers; `tSLEEP` maximum is 1 ms. Do not represent ENABLE as instantaneous overcurrent protection. Keep local driver OCP and independently designed fast current trip, and verify BREAK/PWM behavior, polarity and total latency. Register reconfiguration/validation is needed before re-arm after sleep.[5]

## Voltage limits and energy paths

**DRV8353 is not a 100 V VM design.** Recommended VM is **9–75 V**; recommended VDRAIN is **7–100 V** (datasheet §7.3). A separate VM supply can change VM stress, but does not remove VDRAIN/phase/MOSFET constraints. Gate-disable/sleep pulls the gate outputs down; it is not galvanic isolation or an energy absorber.[5]

The following are topology-derived hazards to verify in the actual schematic and bench tests:

| State | Energy path / required disposition |
|---|---|
| Storage accepts charge | Controlled generator/hub power → DC link → pack within pack-specific voltage/current/temperature limits; BMS availability must not be presumed. |
| Storage full, absent, or BMS opens | Both rotating PM machines can feed bridge body-diode rectification → DC link → autonomous chopper/resistor. Disabled gates do **not** remove this path; worst-case wheel speed and pedal/generator overspeed must be bounded. |
| Bridge hard-inhibited | Commanded torque/regen stops, but uncontrolled diode charging may continue. Mechanical braking reduces wheel energy; generator input must also cease or have a qualified sink/disconnection strategy. |
| Chopper/rail failed or resistor overheated | No qualified sustained sink currently exists. Thermal cutoff that simply disconnects the resistor removes protection. Require fault response that removes mechanical input and safely stops the bicycle, plus a bounded residual-energy path. A failed-short bridge needs source fuse/isolation protection, not only ENABLE. |
| Contactor opens during generation | Local bus and cable/machine stored energy still need a sink; opening the battery connection can worsen OV. Isolation ordering, DC interruption ratings and any phase-isolation scheme remain undefined. |

At 60 V, a hypothetical 7.2 Ω dump resistor draws 8.33 A and dissipates 500 W; 10 s is 5 kJ. This is arithmetic, **not a resistor selection** and not a bound on downhill power. Use `Ecap=½C(Vmax²−Vstart²)` and `dV/dt=Iexcess/C` to budget the interval before the chopper conducts. TVS is for a quantified transient, not sustained rider/downhill dissipation. A full pack may already reject charge below 60 V: pack charge protection and bus survival are distinct requirements.

## Release blockers — all open

1. **Circuit completion:** polarity/interface schematic, POR/UVLO supervisor, fault OR logic, set-dominant reset interlock, brake wire diagnostics, fast current trip, chopper switch/resistor and thermal protection; no asserted single-fault safety or functional-safety certification.
2. **Threshold closure:** worst-case reference accuracy/drift, comparator offset/bias, divider ratio/temperature/voltage coefficient, hysteresis, pull-up loading and RC delay. Prove no nuisance operation at 58.4 V and chopper regulation before the minimum hard-inhibit threshold; resistor values and turn-off thresholds are TBD.
3. **Transient closure:** minimum bus capacitance, BMS-opening current, cable inductance, machine inductance/EMF, maximum speed, propagation/gate-charge delays, ringing and TVS clamp at actual surge current. Prove VM remains below 75 V recommended, phase sensing within its own limits, and 100 V MOSFETs/capacitors below rated stress with margin. Nominal 60/65 V thresholds alone prove none of this.
4. **Energy/thermal closure:** maximum sustained descent plus generator input, resistor pulse/continuous rating, MOSFET switching/SOA/temperature, enclosure/fire/touch hazards, and safe disposition with full storage, chopper open/short or auxiliary loss.
5. **Verification:** independent schematic review and current-limited fault injection (MCU freeze/stuck PWM, WDI stuck/high-rate activity, brake open/short, simultaneous SET/RESET, reference loss, comparator input fault, brownout, BMS disconnect, chopper failure). No circuit simulation, ERC, transient capture or hardware test was performed in this review.

## Sources

[1] https://www.ti.com/lit/ds/symlink/tps3431.pdf
[2] https://www.ti.com/lit/ds/symlink/sn74lvc2g02.pdf
[3] https://www.ti.com/lit/ds/symlink/tlv1702.pdf
[5] https://www.ti.com/lit/ds/symlink/drv8353.pdf
[6] https://www.ti.com/lit/ds/symlink/ucc27511.pdf
[7] https://www.ti.com/lit/ds/symlink/ref33.pdf
