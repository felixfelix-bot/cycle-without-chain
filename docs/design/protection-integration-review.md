# Protection integration review — UNSAFE DRAFT, NOT APPROVED

2026-11-10. Independent integration of verifier `a339c6c2bff4917690ac4ce9719a4c3e62a95ab1` then protection `fb86258cf406723f8a48307bc0b8c902ef64582c`, from default `16b19d1d082e2c0e98894190b1f7ea5b1cfd1813`.

**Publication preserves unfinished engineering work. It is not electrical approval, fabrication permission, energization permission or road-use approval. No PCB/layout or circuit redesign was performed. Three native ERC errors remain release blockers.**

## Integration and evidence

Inspected generator, circuit population, exported identities, tests, calculation assumptions and milestone reports. Reconciled checker expectations to exactly 130 unique parts, 452 unique endpoints, 104 named nets, 13 Q references and 10 U references (two bridge drivers plus eight added ICs). Exact ref/value/footprint, endpoint/net equality, duplicate rejection and ERC identity checks remain intact. ERC identity migrated from old external U1.3 VM to new U3.1 IN/DC_LINK; U1.24 VREF/LOGIC3V3_EXT and U1.25 AGND/PGND remain. This is an explicit reviewed incomplete-state signature, **not an ERC waiver**.

Fresh generator and real KiCad 9.0.9 netlist/PDF/SVG export ran in isolated scratch, producing 10 pages/130 parts/452 endpoints. Native ERC with `--exit-code-violations` returned **5: three errors, zero warnings**. Ordinary export script ERC is report-only and exits zero despite violations; it must never be used as a release gate. Independent checker passed both committed exports and freshly regenerated exports. The historical `verification.json` was refreshed from a successful real read-only checker invocation, not hand-invented counts. No source generator is imported by that checker.

`python3 -m unittest discover -s tests -v` and `python3 -O -m unittest discover -s tests -v` each passed **12 tests**. Checker tests run CLI corruption controls in both modes, preserve file bytes, and now assert the integration summary counts plus reject a substituted U3 ERC endpoint and corrupted DC_LINK. This proves consistency/refusal behavior, not electrical adequacy. Logs: `hardware/powerboard-reva/exports/integration-tests.txt`.

Real ngspice 42 rerun: **80,086 rows**, OV rise **60.33114 V**, fall **58.20219 V**, enable before fault **3.3 V**, simultaneous reset/fault **0 V**, retained inhibit after fault **0 V**, deliberate rearm **3.3 V**, OV while bridge disabled **3.298251 V**. Log: `exports/integration-spice.log`. Exact divider/RC with ideal behavioral comparator/open-collector and logic delays only: **not transistor/vendor-model validation, power switching, UVLO, thermal, EMI or hardware timing validation**. Simulation excludes ARM by assuming permission requested and drives HEALTHY externally; it cannot validate actual fault aggregation.

A second actual ngspice run held reset high across fault clearance (changed reset PWL 4.301–6.5 ms to 3.3 V). `held_after_fault` became **3.3 V**, versus 0 V in baseline: automatic rearm is demonstrated in the behavioral model, not merely conjectured. Reproduction fixture/log: `exports/integration-held-reset.cir`, `exports/integration-held-reset.log`.

Scratch reproduction directory: `/home/c08r4d0r/.hermes/profiles/manager/cache/scratch/cycle-integration-review/board`. Scratch is disposable; committed test/log evidence is the durable record. Exports were regenerated there without replacing the committed render set with path/timestamp churn. No visual layout quality or footprint approval is asserted.

## Prioritized electrical findings and corrections

### P0 — Auxiliary-loss defeats the only active bus sink

U3 feeds AUX12V; U4 derives SAFETY3V3; U5 reference and U6 comparator depend on AUX12V; U10 drives Q13 from that same rail. The chopper is independent of MCU firmware and bridge ENABLE, **not independent of auxiliary supply failure**. Losing U3, its input, ground, U4 or reference can remove bus clamping while permanent-magnet machines continue rectifying through body diodes. Gate pulldowns/driver UVLO turn Q13 off; they do not dissipate energy. Mechanical brakes remain mandatory but do not prove electrical overvoltage containment.

**Correction:** specify the worst generator/regen energy under rail loss and choose an independently powered/energy-backed clamp or qualified source isolation/fail-safe sink architecture, including common-cause analysis. Size hold-up from measured fault energy and disconnect latency, not an arbitrary capacitor. Test loss of each supply/reference with an energy-limited source only after the protection design is approved.

### P0 — Held-high RESET_REQUEST automatically rearms

U7 computes RESET_N=NAND(HEALTHY,RESET_REQUEST), and U8 gates HEALTHY/PERMIT/ARM. Fault wins at external enables while HEALTHY is low, but a permanently high reset clears memory as soon as HEALTHY rises. If ARM is high, drive resumes without a new deliberate action. The model's `latch_next` truth table agrees. Calling this unconditional manual reset or fault memory that always requires a new pulse would be false.

**Correction:** hardware edge-qualified reset with release-before-rearm, persistent-fault rejection and a separately verified ARM sequence. Specify reset stuck-high/shorted, bouncing switch, brownout and simultaneous reset/fault tests. Firmware advice to pulse reset is not an independent safety remedy.

### P0 — Incomplete protected entry, MCU and fast-current trip

Entry still lacks a qualified fuse/interrupt rating, reverse/regen blocking, precharge, contactor/disconnect and discharge design. Storage chemistry/BMS charge acceptance and opening-under-regen energy are unresolved. Real MCU, timer BREAK input connection/polarity, PWM dead-time/fault behavior, ADC conditioning/sampling and position/thermal inputs are absent. TIMER_BREAK_OK exported to a connector is not an MCU hardware shutdown path. Watchdog 0.9–2.5 s is not a fast overcurrent trip; ENABLE and unspecified driver OCP configuration do not qualify short-circuit protection.

**Correction:** finish source/storage fault-energy specification and protected-entry schematic; select MCU and exact timer/ADC pins; add independently budgeted fast OC detection and latching with guaranteed propagation, blanking and MOSFET SOA coordination. Verify both bridge shutdown paths, including frozen firmware/PWM. Close all three ERC errors by completing actual supplies/returns, not by cosmetic PWR_FLAGs.

### P1 — LM339B VOL budget is understated; diode logic margins are not closed

Fetched primary TI LM339 datasheet includes LM339B electrical characteristics: VOL maximum **400 mV at 25 °C, 550 mV over −40…85 °C**, at ISINK≤4 mA and VID=−1 V. U6 is LM339BIDR. OV pullup 1k draws roughly 3 mA; HEALTHY 4k7 draws roughly 0.7 mA. The existing corner code assumes low=0…0.4 V, even while claiming a ±50 K screen. That is not the full-temperature limit. Changing low from .4 to .55 shifts the associated turn-on corner downward by about **0.102 V** (225k/330k × .15); do not reuse the published 59.417 V minimum as a qualified bound. Small-overdrive propagation and VOL behavior also require analysis rather than assuming the −1 V test condition applies at threshold.

For direct HEALTHY comparator pull-down, .55 V is substantially below a nominal .3×3.3=.99 V CMOS low criterion, but full supply/temperature/slew bounds must be established for the selected HC parts. HC00's table lists thresholds at 2/4.5/6 V, not a complete guaranteed 3.3 V corner table; do not silently interpolate a safety guarantee.

D1/D2/D3 add BAT54WS forward drop to driver/supervisor VOL. DRV8353 nFAULT VOL max .125 V at 5 mA; TPS382x-33 reset VOL max .4 V at 1.2 mA at its specified supply test point. BAT54WS table gives max .32 V at 1 mA (25 °C). Screening sums are .445 V for nFAULT and .72 V for supervisor, versus nominal .99 V low threshold: nominal headroom exists, **not proof of failure and not a full-temperature guarantee**. At lower safety voltage the logic margin shrinks; diode temperature/leakage, supply sequencing and HC threshold specification must be included. The divider/reference supply is not the MCU supply.

**Correction:** replace the .4 V corner assumption with properly selected maximum limits across the intended temperature/overdrive/current range; recompute all OV corners. Produce a per-path VIH/VIL budget with tolerances, sink current, diode VF/leakage and actual logic supply extremes. Use a specified Schmitt/interface stage or direct open-drain aggregation with suitable power-off behavior if the full margin cannot be guaranteed. Qualify input edge rates; HC logic is not a Schmitt trigger and the fault bus has offboard capacitance.

### P1 — Startup, brownout and backfeed are unproven

UCC27511 UVLO holds outputs low below its threshold; full-temperature supply start threshold spans **3.70–4.65 V**. That protects its output state while undervoltage, not the correctness of OV_CMD/reference after it starts. As AUX ramps through this range, LM339 common-mode headroom (VCC−2 V over temperature) may not yet accommodate 2.5 V REF/other inputs; U5 regulation and U4/supervisor sequencing also matter. An arbitrary high or low OV command in that interval is not modeled. U7/U8 are not guaranteed below their minimum supply and a collapsing supply must not be treated as a digital truth table.

PWM/SPI/ARM/RESET/WDI from a live MCU can inject current into unpowered driver/safety logic. SO outputs and pullups can back-power a dead MCU; the safety supervisor watches SAFETY3V3, not all these injection paths. LM339 inputs driven by bus/MCU while AUX is absent require datasheet-valid power-off analysis. Series 1k ENABLE resistors are not a universal sequencing solution.

**Correction:** enumerate every supply permutation and every externally driven pin, establish absolute-max injection and rail-current bounds, and add qualified Ioff isolation/clamps/series limits or sequencing controls. Prove hardware disable throughout slow ramps/dips and abrupt supply removal. Qualify reference-valid and supply-valid gating without removing the required bus sink during a dangerous fault. Use vendor models and controlled bench measurements; ideal PWL sources cannot close this.

### P1 — Watchdog edge semantics and reset interaction

Selected **TPS3823-33**, not TPS3823A: datasheet §8.3.2 specifies **negative transitions** servicing watchdog; floating WDI disables it. Fitted 10k pulldown helps prevent a deliberately open input but is not proof against leakage/backfeed or a running peripheral masking frozen application code. Primary datasheet explicitly warns that transitioning WDI during reset on the non-A device can leave RESET stuck low after supply recovery. A-version behavior differs (either edge), so firmware must not assume interchangeability.

**Correction:** specify pulse widths (≥100 ns per table), falling-edge service interval comfortably below minimum timeout, startup/reset WDI policy and stuck-high/low/open/busy-peripheral tests. Resolve the documented stuck-reset mode with a reviewed device/interface choice. This is a sequencing/availability blocker as well as a test omission, not a reason to bypass the watchdog. Prevent automatic rearm after any watchdog recovery.

### P1 — Sink energy, latency and thermal qualification remain open

Two nominal 4.7-ohm resistors give about **383 W at 60 V**, below the illustrative 500 W source. The existing 10 us latency is an unverified budget; LM339 typical delay is not a maximum. No validated heatsink, allowable pulse energy, cable inductance clamp, branch fuse or resistor open-circuit detection exists. 100 V FET rating alone does not qualify bus/regulator/driver pin stress or switching SOA.

**Correction:** define continuous and transient mechanical/electrical power envelope, select resistance and thermal system with tolerance/derating, model and measure transient current/voltage/energy and guaranteed shutdown latency. Include resistor disconnection, shorted Q13, overtemperature and BMS-open tests. Do not use the behavioral OV waveform as power-stage validation.

## Primary sources inspected

PDFs fetched and converted with pdftotext during this review (not reliance on the earlier report alone):

- [TI LM339 family, LM339B characteristics](https://www.ti.com/lit/ds/symlink/lm339.pdf): VOL, common-mode range and response-time dependence.
- [TI SN74HC00](https://www.ti.com/lit/ds/symlink/sn74hc00.pdf): recommended supply/input thresholds and edge rates. U8 HC11 needs its own complete margin qualification before release.
- [TI TPS3823 family](https://www.ti.com/lit/ds/symlink/tps3823.pdf): electrical table and §8.3.2 watchdog negative-edge/non-A reset caveat.
- [TI UCC27511](https://www.ti.com/lit/ds/symlink/ucc27511.pdf): UVLO electrical limits and §9.3.1.
- [Diodes BAT54WS](https://www.diodes.com/assets/Datasheets/BAT54WS.pdf): forward voltage and leakage table.
- [TI DRV8353](https://www.ti.com/lit/ds/symlink/drv8353.pdf): nFAULT/SDO open-drain VOL specification.

This bounded review did not independently qualify every passive ordering code, footprint, package land pattern, regulator thermal model or storage architecture. Prior design report is useful provenance, not an approval. All findings above remain open; correction recommendations are not implemented redesigns. **Default publication verdict: UNSAFE DRAFT. Release verdict: BLOCKED.**
