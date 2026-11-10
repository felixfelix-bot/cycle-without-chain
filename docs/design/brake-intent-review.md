# Brake-intent topology review — UNSAFE DRAFT

**Suitable only for default-branch design consolidation. NOT SAFE TO ENERGIZE, fabricate or ride.** This is a bounded independent inspection of the actual native schematic/netlist and normalized policy model, not cross-family approval, functional firmware verification, or hardware qualification.

Reviewed feature: `78d92ec131640d1bc505b36d943a1cc0ceed69f3`, merged with current `github/master` in the review worktree (README changes preserved). No FSR redesign or electrical circuit change was made by this review.

## Actual topology verdict

- **Hard inhibits retained:** J5.2 → FAULT_CHAIN → U6.11, with R50 pulldown; U6.13 sinks ANALOG_OK when the NC E-stop/thermal chain opens. Existing fault conditioning reaches U14; U14.3 WD_OK and U14.6 OC_OK remain hardware health inputs. U14.4 HEALTHY reaches U16.1 and latch clear inputs. U16.4 TIMER_BREAK_OK drives both DRV8353 ENABLE paths through R60/R61, MCU timer-break pins46/84, and U25.2. These are physical connections, not a claim that MCU timer setup exists. Supply loss/transient/propagation behavior still needs qualification.
- **Rider switch is not the hard kill:** J44/J45 switch/Hall channels terminate in protected ADC inputs, not FAULT_CHAIN. Removing the old blanket brake shutdown permits controlled negative torque in principle. It also removes an independent positive-torque inhibit: healthy watchdog transitions plus wrong-sign MCU commands remain dangerous. There is no implemented firmware or hardware torque-sign guarantee.
- **Normal dump:** U17.50 → BRAKE_DUMP_PWM → U25 AND TIMER_BREAK_OK → U24 OR → U10.6. TIMER_BREAK_OK is permission, not evidence of a rider request. Valid rider demand and a qualified cool sink must authorize the normal command in future firmware; the hardware does not independently authenticate that demand. The model correctly commands zero dump/regen when both levers are released even with either sink permission true.
- **Emergency OV:** U6.2 OV_CMD → U24.1 bypasses U25 and rider request. It can command clamping while bridges and normal dump are inhibited. The override still needs powered safety logic, AUX12V and an intact dump path; it is not an unconditional guarantee with hot resistor, supply failure or PM generation. Gate-off is not generation-off.

Fresh exported endpoint maps exactly matched the committed netlist. Relative to master, existing endpoint changes were the FAULT_CHAIN/status rename, U10.6 OV_CMD→CHOP_CMD, and five newly allocated MCU pins. The other hard-gate endpoints were retained.

## Sensor and electrical limitations

**FSR pressure pad is the selected user direction. The FSR front end, part, force range, mechanical arrangement and calibration do not exist in this milestone.** Hall pages and the Hall/switch model are alternative/reference work only. No metallic strain bridge, R-2R linearizer or inferred FSR transfer curve was added. Independent binary activation must remain authoritative over zero FSR pressure; disagreement must fault rather than permit positive torque.

The offboard switch network is electrically plausible: 10k pullup with 4.7k + (10k || NC contact) gives release 3.3×4.7/14.7 = 1.055V and brake 3.3×14.7/24.7 = 1.964V. Whole harness open tends to rail; signal short tends to ground. EOL resistors must actually live at the lever. A welded contact, shorted EOL element, cross-short, ground fault or plausible stuck analog signal is not comprehensively diagnosed by this topology. The model receives already-decoded normalized inputs and does not implement these voltage windows, debounce, startup proof, stale-sample detection or time bounds.

Each 22Ω sensor feed has 100nF board-side decoupling: at 10mA, drop is 0.22V and dissipation 2.2mW; at ideal 3.3V hard short, current is 150mA and dissipation 0.495W. This is not a qualified current-limited sensor supply. Two candidate 10mA Hall sensors alone need up to 20mA, excluding bias, MCU and fault loads; rail minimum, cable loss and remote decoupling remain unqualified. The selected passive FSR needs its own future excitation/loading budget.

Four inputs have 10k series, 10nF ADC shunt, PESD3V3U1UL connector TVS and BAT54S clamps. The nominal 100µs RC excludes source impedance. The binary source adds approximately 3.20k released or 5.95k braking, giving approximately 132/160µs RC before ADC acquisition effects. A hypothetical externally held 3.3V input with the MCU rail off can inject roughly (3.3−Vf)/10k per channel into that rail; four channels aggregate and can back-power it. Neither BAT54S forward drop nor TVS standoff proves MCU absolute-maximum compliance. Injection limits, rail sink capability, power sequencing, leakage/temperature, ESD and battery miswire are still release blockers.

## Pin/document corrections

Recovered primary-authored ST DS12288 Rev5 Table12 was fetched independently from the documented mirror; current ST revision/errata validation remains open. PC3/18 ADC12_IN9, PA3/25 ADC1_IN4, PA4/26 ADC2_IN17 and PB2/34 ADC2_IN12 agree with the native symbol allocation. PA4 DAC must stay disabled. Acquisition scheduling alongside phase-current ADCs is unimplemented.

**Found and corrected documentation errors:** dump pin50 is **PB11**, not PE0; native netlist was already PB11. J5's actual value is SAFETY_FAULT_CHAIN_NC, not the milestone's former invented value. The stale MCU allocation CSV now includes the four brake ADCs, PB11 command and FAULT_CHAIN_SENSE rename. No netlist repair was necessary. GPIO naming is not proof of configured timer PWM.

Native and freshly exported SVG labels identify Hall/supervised binary, OFFBOARD EOL, firmware unimplemented, clamp/power-off unqualified, no torque-sign guard, and independent OV bypass. Their electrical meaning is consistent with the circuit; “sensor supply limit” means series resistance only, not short-safe current limiting. The Hall titles describe the alternative circuit, not the selected FSR. This review checked source/export text, not full-page visual legibility. Existing entry warnings remain: no approved energized jumper sequence; never manipulate J40/J41/J42 energized or charged.

## Executed verification

- `python3 -m unittest discover -s tests -v` in hardware directory: **29 passed**; repeated with `python3 -O`: **29 passed**. Includes structural/missing-artifact/endpoint mutation controls.
- `python3 -m unittest discover -v` in `analysis/brake_intent`: **8 passed**, normal and `-O`.
- Fresh `kicad-cli sch export netlist --format kicadsexpr` and SVG export: exit0, scratch outputs only; fresh component/value and endpoint maps exactly equal the committed export; MCU and brake fixed-endpoint validators passed on fresh data.
- Fresh strict `kicad-cli sch erc --format json --exit-code-violations`: **exit5, four errors**: undriven U1.24 VREF, U1.25 AGND, U3.1 IN and U17.37 VDDA. Not waived; not ERC clean.
- Sixteen fresh-netlist endpoint mutations covering fault chain, watchdog, OC, health, all ADC inputs, normal AND, OV OR and driver input were rejected.
- Three executable state-source mutations were rejected by assertion failures in both normal and `-O`: permission-as-dump-demand, rider request incorrectly made a hard kill, and OV incorrectly gated by rider demand.

Local raw evidence: `/home/c08r4d0r/.tmp/cycle-brake-review/` (hardware/state logs, fresh netlist/SVG/ERC, mutation logs and recovered ST source). The hardware suite writes SPICE logs into its source export directory; this review preserved those new logs in scratch and restored only its own test-written tracked logs to baseline, with no regenerated exports committed.

## Disposition

Consolidate as an **UNSAFE design milestone**, not an implementation completion. Open blockers include FSR front end and calibration, independent positive-torque safety architecture, all MCU firmware, sensor plausibility/timing qualification, connector/harness selection, clamp/backfeed and supply qualification, dump energy/thermal/SOA and power-loss behavior, unresolved ERC errors, independent review and staged bench fault injection. Mechanical braking remains independently necessary. The model proves a policy under assumptions; it cannot enforce that policy on the bicycle.
