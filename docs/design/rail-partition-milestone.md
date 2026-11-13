# Rail partition milestone: load ledger and unresolved qualification

> **STATUS: ENGINEERING SCREENING — NOT SAFE TO ENERGIZE.** 2026-11-10. No bench measurements, whole-rail maximum, sequencing qualification, PCB release or authorization to remove inhibits is claimed.

## Integrated execution addendum

Native KiCad regeneration completed: **32 pages, 382 components, 218 nets,
1129 connected pins, 51 explicit NCs**. Full suite **45 tests pass normally and
45 under `python3 -O`**; logs `exports/rail-tests{,-O}.log`. New native XML
endpoint tests first failed on the unpartitioned export (`rail-red.log`) and
then passed, including empty/corrupt negative controls. BOM, netlist, PDF and SVG
were regenerated. Strict ERC **exit 5: 10 errors, zero warnings**: inherited nine
plus DRIVE12 undriven across passive L501. No PWR_FLAG or pin-type suppression.
> **Historical record — superseded.** This review describes the state at the
> commit it was written for (10 strict-ERC errors). ERC is now 0/0 as of the
> PWR_FLAG work; see `erc-power-flags.md`. The figures above are left as the
> record of that run and must not be read as the current state.


Exact changes: U1/U2 VM and four VM capacitors move AUX12V→DRIVE12; all remaining
AUX12V consumers move to SINK12. U501 VIN is DC_LINK; SW→L501→DRIVE12.
U502 VIN is DRIVE12, SW→L502→LOGIC3V3_EXT, FB senses that output directly.
J2 is now explicitly test-only, not a second source. U500.6→CTRL_PG with R520
10k pullup to CTRL3V3; U510 ANDs CTRL_PG with MAIN_PROVEN_IN. R519 fitted 0R
holds MAIN_PROVEN_IN low. U501.6 open drain joins ANALOG_OK, feeding the existing
fault/inhibit path; U6 continues monitoring SINK12 and MCU voltage. MAIN/PRE
R402/R412 0R inhibits remain unchanged. This avoids the circular dependency of
using TIMER_BREAK_OK (which needs the MCU rail) to start that same rail.

**Partial implementation, not full milestone acceptance:** MAIN proof and settle
hardware remain absent. No dynamic brownout/interlock test was performed. The
sink is the inherited 500mA R78HB rather than the proposed LM5164 replacement;
its startup/efficiency cannot inherit the earlier LM5164 model. AP63203 internal
LS valley limit is 2.5/3.2/3.9A min/typ/max; L502's provisional 2A designation is
NOT fault-current qualification and must be replaced/qualified against peak
ripple/current-limit overshoot before any energization. LM5164 peak limit is
1.25–1.75A, not an external load-current cap. No added external load limiter is
claimed. Full MCU/DRV/external-load maxima and source-backed closed operating
budget are **unfinished**, rather than replaced by an invented allocation.

CTRL's prior 0.7033W screening plus R520 worst low pullup 3.3²/10k/0.6
= **0.70515W** before any additional uncertainties, versus 0.8W acceptance.
SINK's 1.027109W screening corresponds to **28.531mA at 36V /17.588mA at
58.4V**. CTRL+SINK screening is **1.732257W**, or **48.118/29.662mA**,
excluding separately listed direct-bus loads. Acceptance caps together are
1.9W (**52.778/32.534mA**), not 0.8W for the whole board. These are computed
arithmetic, not measured currents. Transient, DC bias, sequencing timing,
loss-of-sink supply and MAIN proof remain blockers. Mechanical brakes mandatory.

## Outcome

The intended partition retains **U3 R-78HB12-0.5**, renamed from AUX12V to **SINK12**, always powered by DC_LINK. **U501 LM5164** supplies delayed DRIVE12. **U502 AP63203** takes **DRIVE12**, not SINK12, and supplies the existing **LOGIC3V3_EXT** net (MCU3V3 is a descriptive alias, not a second disconnected rail). U510 requires CTRL_PG AND MAIN_PROVEN_IN; fitted R519 0-ohm inhibit keeps the latter low. **Not** all safety loads are on SINK12/U4 SAFETY3V3: the U18-U23 TLV3202 comparators and both OC reference ladders are on LOGIC3V3_EXT, which is downstream of the delayed DRIVE12 cascade (see the OC-supply note below, which supersedes any "all safety loads always on" reading of this paragraph). Only the OC_OK pullup is on SAFETY3V3. There is no implemented MAIN conduction detector or PGOOD sequencer.

**J5 stays SAFETY3V3 → normally closed emergency-stop/thermal chain → FAULT_CHAIN. It is a sense loop, not an external accessory power connector.** Disconnecting it to save power would break the safety contract. Its known board-side demand is included below; arbitrary external power draw is forbidden, not allocated.

The reproducible calculator is [`analysis/precharge/rail_budget.py`](../../analysis/precharge/rail_budget.py), stdlib only. It deliberately returns `qualified: false` and named unknowns rather than inventing a total for the MCU and bridge drivers.

```
python3 analysis/precharge/rail_budget.py --self-test
python3 analysis/precharge/rail_budget.py --json
python3 analysis/precharge/rail_budget.py --oc-on-safety --json
```

Executed: self-test **PASS**, both configurations exit 0. These are arithmetic/model tests, not hardware tests. The circuit generators and native exports are now integrated; see execution addendum below.

## Connectivity evidence and integration boundary

Read `hardware/powerboard-reva/{rail_partition,protection,fast_oc,fsr,brake_intent,mcu}_circuit.py`, `generate_schematic.py`, `analysis/precharge/power_budget.py`, and [precharge-power-sources.md](precharge-power-sources.md). The latter's proposed replacement sink LM5164 is **not** the retained U3 implementation. Its efficiency/UVLO assumptions cannot be transferred to R78HB as proven behavior.

Integration corrected U502 VIN to DRIVE12 and output to LOGIC3V3_EXT; native XML endpoint tests verify these connections. The calculator assumes the target DRIVE12 cascade for running-domain accounting. Re-check regenerated connectivity before release.

At inspection, **U18–U23 TLV3202 supply and both OC reference ladders are on LOGIC3V3_EXT**, with only the OC_OK pullup on SAFETY3V3. Therefore “all safety loads always on” is not yet literally true for OC comparators. The default calculation records that source wiring; `--oc-on-safety` explicitly screens relocation of all three OC load rows to SAFETY3V3. This switch does not silently edit or claim changed connectivity. Moving OC references requires a separate threshold/ratiometric review against driver CSA reference; merely moving the supply label is not a complete safety design. The autonomous OV/dump chain is already on the early safety domain. FSR is a delayed rider-measurement frontend, not an independent safety interlock.

## Source discipline

Resistor watts below are **COMPUTED nominal**, not tolerance maxima. Datasheet typical and specified maxima retain their test conditions. Values marked **ASSUMPTION** are design allocations only. A mixed sum is a screening envelope, never a manufacturer-guaranteed maximum. Capacitor charge, dynamic logic current, temperature, tolerances and backfeed remain open.

Manufacturer PDFs read on 2026-11-10:

| Source | Evidence used |
|---|---|
| [CSD19532Q5B SLPS414B](https://www.ti.com/lit/ds/symlink/csd19532q5b.pdf), §5.1 | Q13 actual selected MOSFET: Qg **48 nC typical / 62 nC max**, at **VGS=10 V, VDS=50 V, ID=17 A, TA=25°C**. Neither number is a 12 V/full-temperature bound. |
| [TLV3202 SBOS561C](https://www.ti.com/lit/ds/symlink/tlv3202.pdf), §6.5/6.7 | **40 µA/channel typical**, 50 µA at 25°C max, **65 µA full-temperature max** at 5 V/2.7 V test supplies. Twelve channels, not six single comparators. 3.3 V arithmetic is an envelope. |
| [OPA333 SBOS351E](https://www.ti.com/lit/ds/symlink/opa333.pdf), §6.6 | **17 µA typical**, 25 µA max at 25°C, **28 µA full-temperature max** per amplifier, output unloaded; output current counted separately. |
| [TMUX1511 SCDS390B](https://www.ti.com/lit/ds/symlink/tmux1511.pdf), §5.5 | **37 µA typical / 70 µA max** per package, 1.5–5.5 V, −40…125°C, stated select/signal conditions; typical at 3.3 V/25°C. |
| [Existing source audit](precharge-power-sources.md), §3/5 | TI LM339B, TLV760, UCC27511, TPSI3052 and CTRL component evidence. UCC27511 UVLO startup current is not operating current; TLV760 5 mA is a **no-load** ground-current test, used only as an allowance here. |
| rail_partition_circuit.py source header | R78HB 500 mA output, 17–72 V input for 12 V version; LM5164 12 V/1 A reference; AP63203 3.3 V/2 A. Ratings are not measured available power at board temperature. |

## Actual load ledger

### Always-on SINK12 and SAFETY3V3

| Load | Formula / allocation | W at named rail |
|---|---|---:|
| R39 SINK12 preload | 12²/1000 | 0.144000000 |
| R40 + U5 LM4040 whole input branch | 12(12−2.5)/4700; do not add reference dissipation again | 0.024255319 |
| R46/R47 SINK12 monitor | 12²/40000 | 0.003600000 |
| U6 LM339B | 12×1.6 mA; conservative envelope from 36 V test | 0.019200000 |
| U10 UCC27511 static | 12×1 mA **ASSUMPTION** | 0.012000000 |
| **Direct SINK12 subtotal** | excludes U4 cascade and active gate charge | **0.203055319** |
| R45/R51/R56/R57/R115 pullups | 3.3²(1/1k+2/4k7+2/10k), all low | 0.017702043 |
| J5 sense loop | 3.3²(1/10k+1/110k), closed NC chain incl. MCU sense divider | 0.001188000 |
| RELEASE_N/FAULT_LATCH pulldowns | 2×3.3²/100k, both high screening | 0.000217800 |
| U7/U8/U11–U16/U24/U25/U510 | 11×20 µA×3.3 **ASSUMPTION**; exact mixed-family limits/dynamics open | 0.000726000 |
| U9 TPS3823 | 50 µA×3.3 **ASSUMPTION**, not a quoted maximum | 0.000165000 |
| U510 delayed EN resistor chains | 3.3²(1/182k+1/147k); zero while inhibited, included conservatively | 0.000133917 |
| **SAFETY3V3 subtotal** | present source OC placement | **0.020132759** |

SAFETY3V3 current = **6.100836 mA**, already above the historical 6 mA aggregate allowance before unbounded switching effects. U4 input = 12×(0.006100836+0.005) = **0.133210034 W**; this replaces, rather than adds to, the old 0.132 W LDO line. U4 thermal dissipation must be checked separately; output watts must not be counted twice at SINK12.

Retain **0.10 W main-proof analog allowance** as an explicitly unimplemented allocation, not fitted BOM current. With historical **60% assumed end-to-end efficiency** and **0.30 W input reserve**:

`(0.203055319 + 0.133210034 + 0.100000000)/0.60 + 0.30 = 1.027108922 W`

Margin to the **1.1 W early sink input acceptance envelope** is **0.072891078 W**. This is not demonstrated compliance. The optional all-OC-on-safety scenario is **7.447379 mA SAFETY3V3**, **0.149368546 W U4 input**, and **1.054039775 W sink input**, leaving **0.045960225 W**. A modest efficiency or load miss exhausts that margin. Do not round this result into a release claim.

### LOGIC3V3_EXT delayed loads

| Actual load | Formula / basis | W |
|---|---|---:|
| U18–U23 OC comparators | 12×65 µA×3.3; typical corresponding IQ is 12×40 µA | 0.002574000 |
| OC reference ladders | 2×3.3²/38k7 | 0.000562791 |
| Q14–Q25 gate pulldowns | 12×3.3²/100k, all high screening; dynamics extra | 0.001306800 |
| U26/U28 OPA333 IQ | 2×28 µA×3.3 | 0.000184800 |
| U27/U29 TMUX1511 IQ | 2×70 µA×3.3 | 0.000462000 |
| Two FSR excitation paths | 2×3.3²/(10k+1k+10k), FSR resistance→0 | 0.001037143 |
| Two OPA output/ADC bleed paths | 2×3.3×(3.3×10k/21k)/11k, mux enabled, neglect RON | 0.000942857 |
| FSR_SAMPLE_ENABLE two pulldowns | 2×3.3²/100k | 0.000217800 |
| Binary switch bias paths | 2×3.3²/10k, cable-short bound; normal NC includes 4k7 EOL | 0.002178000 |
| Six Hall and two encoder pullups | 8×3.3²/10k, all low | 0.008712000 |
| MCU rail monitor | 3.3²/(2k+10k) | 0.000907500 |
| WDI/ARM/RESET_REQUEST/dump PWM/NRST | 3.3²(1/1k+4/10k), simultaneous screening states | 0.015246000 |
| **Known partial subtotal** | excludes MCU silicon and external devices | **0.034331691** |

With OC relocated this partial subtotal is **0.029888100 W**. MCU_VREF is physically linked to LOGIC3V3_EXT by 0 ohm, so FSR excitation is **not free reference energy**. ADC bleed current is drawn through the OPA output and must be counted in addition to excitation current. Internal TMUX select pulldowns/leakage, comparator dynamic output gate charging, ADC sampling, clamp injection and GPIO transition current remain additional unclosed terms.

**Unknown, not zero:** U17 STM32G474VET6 consumption for actual firmware/PLL/ADC/temperature, Hall sensor supply current, optional encoder supply, SWD/debugger loading/backfeed. No running LOGIC3V3_EXT maximum exists yet.

### DRIVE12 and conversion chain

U1/U2 DRV8353 VM and bypasses belong on DRIVE12. Their **running static demand, charge-pump losses, six gate channels per bridge and PWM frequency/charge** are unresolved. Their logic supplies/CSA output loading also require a separate audit. The six raw CSA 100k bias resistors load driver outputs; they are not an extra direct LOGIC3V3_EXT shunt. U501 feedback divider alone is **12²/502900 = 0.000286339 W**. This is plainly not a whole DRIVE12 total.

Use `P_DRIVE_out = P_U1_VM + P_U2_VM + P_U502_in + P_feedback`, and `P_U502_in = P_LOGIC_out/eta_AP63203` with end-to-end measured efficiency, or an explicitly separate loss model. Then `P_bus_drive = P_DRIVE_out/eta_LM5164`. Never charge MCU demand to both SINK12 and DRIVE12. Do not add IQ again if already included in the measured efficiency. Disabled U501 input leakage remains on DC_LINK even when its output is off.

## CTRL is separate from early sink

The **0.8 W CTRL input cap** is pack-side, not part of the **1.1 W bus-side sink cap**. The existing model's low-voltage allocations are two TPSI3052 at 50 mA each assumed (26 mA each typical at 20k PXFR), two LM339B at 1.6 mA, TLV9002 2×85 µA, TLC555 1 mA assumed, three latches 10 µA each, and 5 mA other logic/reference allowance. They are documented in the existing source audit; neither cap is a measured maximum. Their loads must not be merged into a single bus-precharge constant. At the source, total demand includes CTRL plus the precharge path, but CTRL is not drawn through the precharge resistor. Existing analysis/precharge/power_budget.py is left unchanged.

## Q13 dump-driver arithmetic and direct bus demand

The actual dump FET is **Q13 CSD19532Q5B**, not an unrelated high-charge MOSFET. Driver supply energy is `Qg × Vdrive × f`, plus the fitted **10k gate-source pulldown** `Vdrive²/10k × duty`, plus U10 quiescent current already in the ledger. Do not multiply gate energy by two for charging and discharging.

At an **illustrative assumed 20 kHz, 50% duty, 12 V**, using the datasheet's **10 V** charge numbers only as sensitivities:

- 48 nC: `48e−9×12×20000 + 144/10000×0.5 = 0.018720 W`.
- 62 nC: `62e−9×12×20000 + 144/10000×0.5 = 0.022080 W`.

**These are not 12 V bounds.** Qg at actual VGS/VDS/current/temperature, frequency, duty and gate waveform must be established. They are active-braking additions, not part of a standby-precharge claim. Add to SINK12 output before conversion, not as bus watts. Fault chopper activity invalidates an ordinary standby precharge case.

Dump resistor energy, Q13 conduction/switching loss, bridge power, **D20 bus TVS**, R118 bleed and bus HV sense are supplied **directly from DC_LINK**, not through SINK12. TVS normal leakage and transient absorption are separate unknowns; TVS clamping is not steady regulated auxiliary demand. At nominal bus voltages:

| Vbus | R118 10k bleed | 235k sense-chain approximation |
|---:|---:|---:|
| 35 V | 0.122500000 W | 0.005212766 W |
| 57.4 V | 0.329476000 W | 0.014020255 W |

The sense approximation neglects R44 hysteresis injection; solve the actual branch for tighter accounting. Existing **0.04 W bus-leakage allocation** and **2 W/30 ms sink-startup acceptance cap** are assumptions to verify, not additional measured loads. Do not add both a blanket leakage reserve and each covered leakage as if independent.

## Blocking unknowns and next evidence

1. Regenerate and audit U502 DRIVE12→LOGIC3V3_EXT, all VM/bypass migrations, retained J5 sense function and all independent safety supply pins. Decide OC placement explicitly and reclose reference thresholds; test unpowered comparator/CSA backfeed.
2. Measure retained R78HB startup and efficiency at this small load across bus voltage/temperature, plus TLV760 loaded ground current. The earlier LM5164 sink UVLO/soft-start narrative is inapplicable to U3. R78HB minimum operating input is 17 V; PM cold-start autonomous braking is not proven.
3. Replace safety static allowances with exact orderable-part limits, assess ΔICC and dynamic current, divider tolerance, rail tolerance, enable input loads and feedback current. The old 6 mA SAFETY3V3 allocation has no demonstrated spare margin.
4. Bound U17 firmware modes, DRV8353 VM/DVDD/charge pump/PWM demand, sensor supply current, ADC/FSR dynamics and all external interfaces. Until then no full DRIVE12/LOGIC3V3_EXT max, U501/U502 thermal margin or inductor saturation verdict exists.
5. Qualify Q13 charge at actual 12 V drive and switching conditions; determine chop frequency/duty and U10 losses. Qualify dump energy/thermal/TVS/SOA separately from auxiliary watts.
6. Close leakage/backfeed and startup capacitor budgets including disabled U501 input caps and U1/U2 VDRAIN. Validate early sink ≤1.1 W and CTRL ≤0.8 W independently; if either fails, revise precharge simulation and timeouts rather than relabeling the assumptions as measurements.

**This milestone enables continued design and arithmetic review only. It does not clear any existing energization, protection, sequencing, thermal, or fabrication gate.**
