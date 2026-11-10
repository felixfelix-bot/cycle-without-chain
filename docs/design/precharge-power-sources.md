# Precharge supply and load audit — bounded candidate

> **STATUS: CONSULTANT ANALYSIS — NOT A DECISION RECORD. NOT SAFE TO ENERGIZE.** Read-only hardware audit, 2026-11-10. This document proposes a physically different supply partition and resistor, not a claim that existing hardware meets new allocations. No schematic/BOM approval, efficiency guarantee, pulse qualification or bench result is implied.

> **Integrated revision controls:** see [budget revision](precharge-budget-revision.md). Final sink envelope is 1.1 W including 0.10 W low-voltage analog proof allowance and 0.30 W input reserve. Below is the retained supply audit; arithmetic corrected during integration.

## Recommendation

Use **22 ohm ±1% precharge**, **300 ms nominal / 350 ms maximum latched timeout**, a **direct pack-to-3.3 V CTRL buck**, and an independently **bus-fed 12 V sink/safety buck**. Retain the existing sink/safety loads, including the 1k preload for conservative accounting; physically disconnect the two bridge VM loads and all external/MCU loads until main conduction is proven. Model **1.0 W sink input**, **0.8 W pack-side CTRL input**, and a separately bounded sink startup transient. These are **acceptance envelopes derived below, not manufacturer maxima**. A 100-ohm branch cannot support this honest sink envelope at a 1 V ready threshold.

This is the simplest credible partition using the selected IC family: two early supplies plus a delayed drive supply, no power-OR, no ultra-low-power redesign of the sink, no optional relay coil. Replace R116 with a pulse-qualified 22-ohm part; do not pretend the existing 100-ohm part has changed. A 50 W headline rating does not qualify its 157 W short-circuit pulse.

## 1. Actual exported connectivity, not an inferred block diagram

Audited `hardware/powerboard-reva/exports/powerboard-reva.net`, export timestamp `2026-11-10T13:54:09+0100`; SHA256 `51846718d63735fd59f9b556314e29d405dbefcf3bf67ea7c94c50a0796dae1e`. Also read `docs/design/precharge-sequencing-design.md` and `analysis/precharge/candidate-bom.csv`. Hardware was not edited.

| Exported net/component | Pins / implication |
|---|---|
| DC_LINK | U3.1 IN; U1.4/U2.4 VDRAIN; R118.1; R41.1; C73.1/C74.1; D20.1 K. Bridge VDRAIN and power drains remain bus-connected even if VM is gated. Their residual leakage must be included. |
| U3 R-78HB12-0.5 | .1 DC_LINK, .3 AUX12V; existing module has no exported enable. MCU reset does not stop this supply. |
| AUX12V | U3.3, U1.3/U2.3 VM, U4.2 IN, U6.3 VCC, U10.1 VDD, R39.1, R40.1, R46.1 and local bypass capacitors. |
| R39 | 1k ±1%, AUX12V to PGND: **144 mW nominal** before any useful control load. |
| R40 / U5 | 4.7k ±1% AUX12V→REF2V5; U5 LM4040AIM3-2.5 K=.1 at REF2V5. Supply current (12−2.5)/4700=2.021 mA; **24.255 mW from 12 V**, not just resistor dissipation. |
| U6 | LM339BIDR; .3 AUX12V, reference inputs .4/.6/.8/.10 REF2V5. R46/R47=30k/10k auxiliary monitor consumes 0.300 mA. |
| U10 | UCC27511DBVR; .1 AUX12V, .4 PGND, .5 IN− PGND; autonomous chopper driver must remain powered. |
| SAFETY3V3 | U4.1 output feeds U7/U8 latches, U9 supervisor, U11/U12, U13–U16, U24/U25, R45/R51/R56/R57/R115 and **J5.1 external load opportunity**. Not synonymous with a tiny isolated sink controller. |
| R45 | 1k SAFETY3V3→OV_CMD; U6.2 open collector. It can draw 3.3 mA when low. |
| Other safety pullups | R51 and R115 4.7k; R56/R57 10k. Counting all five low gives 3.3/1k + 2×3.3/4.7k + 2×3.3/10k = **5.364 mA** before IC loads. |
| R118 / bus sense | 10k ±1% DC_LINK→PGND bleeder; R41+R42+R43 nominal 112k+113k+10k bus sense. At 57.4 V these draw **0.329476 W** and about **0.014020 W** respectively. Do not hide them inside converter efficiency. |

The old 0.10 W sink claim is disproven by R39 alone. Keeping the exported AUX rail unchanged also leaves two DRV8353 bridge supplies connected. Their removal from the early rail is mandatory; this analysis does not purport to bound their running current.

## 2. Candidate power connections

### CTRL (pack side, operational before precharge)

`ENTRY_FUSED → dedicated branch fuse → STTH1R02A reverse-blocking diode → CTRL_RAW → LM5164 VIN pin 2`. PGND→pin 1 and exposed pad; pin 8 SW→inductor→CTRL3V3; pin 7 BST→2.2 nF→SW; pin 4 RON→program resistor→PGND; pin 5 FB→output divider; pin 6 PGOOD→CTRL3V3 pullup and hardware startup interlock. Configure output nominal 3.3 V (nominal divider ratio 1.75, e.g. 87.3k/49.9k); **redesign inductor/RON/ripple network for 3.3 V**, not copy a 12 V circuit unchanged. Capacitor derating, output tolerance and ripple must leave TPSI3052 VDDP between 3.0 and 5.5 V.

EN/UVLO pin 3 divider 190k/10k gives nominal rising 30 V / falling 28 V at CTRL_RAW. With ±1% resistors and TI threshold limits, rising is approximately **28.45–31.59 V**, falling **26.49–29.35 V**; these are tolerance intervals, not independently selectable thresholds. At a 36 V source allow diode/wiring drop before declaring margin. Clamp EN low on fault; never bypass reverse diode with sense/logic paths.

Both TPSI3052: pin 3 VDDP→CTRL3V3; pin 4 VSSP→PGND; pin 2 PXFR→20k→PGND; pin 1 EN→separate default-low MAIN/PRE command. Hold EN low until CTRL3V3 is valid to guarantee three-wire startup. Pin 5 VSSS→respective common-source FET node, **not PGND**; pin 8 VDRV→separate gate resistors; pin 7 VDDH and pin 6 VDDM take TI secondary split capacitors, with effective CDIV2≥3×CDIV1. These isolated rails are not additional pack-side loads to count again; transfer current includes them. Bound actual capacitance/gate-load startup before using a ready delay.

Power TLV9002, TLC555, three SN74LVC1G74 and sequencer logic from CTRL3V3. Two LM339B packages can also use this rail **only with redesigned sensing**: full-temperature common-mode upper bound is VCC−2 V, i.e. 1.3 V at nominal 3.3 V. The old 1:25 / 1.65 V bias recipe is not valid here. Candidate 1:64 input scaling and approximately 0.8 V difference-stage bias keep the intended signals below 1.3 V; re-close offset/divider tolerance and reverse-input clamps. This is a required analog implementation change, not an already qualified comparator schematic. TLC555 and comparator temperature grades constrain the assembled operating range.

Delete the CTRL12→TLV76033 cascade from this candidate. Two drivers alone at the specified 20k setting require **2×26 mA×12 V=0.624 W typical at the LDO input**; at direct 3.3 V they require **0.1716 W typical**. TLV760 additionally draws 2 mA typical / 5 mA maximum ground current under its specified no-load conditions. Thus the original 0.5 W whole-controller allocation cannot describe that cascade.

### Sink (always bus-fed, no dependence on pack presence)

`DC_LINK → LM5164 VIN pin 2`, PGND pin 1/EP; 12 V output from pin 8/inductor using TI's 12 V reference topology including ripple network. Rename output SINK12. Feed **U4.2, U6.3, U10.1, R39.1, R40.1, R46.1**, and their local bypasses from SINK12. U4.1 remains the independent SAFETY3V3 rail and keeps autonomous safety logic alive. No connection to CTRL3V3 or CTRL_RAW except protected signal interfaces.

Candidate sink EN divider 100k/10k gives nominal **16.5 V rise / 15.4 V fall**. ±1% divider plus specified thresholds gives rise **15.66–17.36 V**, fall **14.58–16.13 V**. Rising is safely above 12 V output, unlike treating 6 V IC operation as regulated 12 V output availability. This UVLO is for the sink only; never gate sink power on MAIN_PROVEN. Maximum 4.75 ms IC soft start does not bound total cold-start-to-working-chopper latency.

### Delayed drive domain

Move U1.3 and U2.3 VM and their bypasses to DRIVE12 from a separately enabled bus buck. Keep MCU/external loads off early rails. **J5.1 may not supply an unbounded external load during precharge**; disconnect or explicitly limit it. Default-low DRIVE_EN requires source valid, main-driver supply valid, electrical main conduction proof and settling time. Merely holding bridge/MCU reset is not power gating. Count disabled converter input capacitors in bus capacitance and shutdown current/leakage in early bus demand. Audit unpowered pin backfeed through SPI/ADC/enable and U1/U2 VDRAIN before claiming zero drive-domain load.

## 3. Component ledger: typical is not maximum

All watts below refer to input of the named low-voltage rail, not pack input. `ASSUMPTION` denotes a qualification envelope; efficiency curves are typical, never guaranteed minima.

### CTRL3V3

| Load | Evidence / bound | Power at 3.3 V |
|---|---|---:|
| 2 TPSI3052, PXFR=20k | TI §6.9: **26 mA each typical**, no IVDDP maximum in this row. **50 mA each assumed cap**, including both continuously powered; do not infer supply-off from EN low. | 0.1716 W typical / 0.330 W assumed |
| 2 LM339B packages | §6.7 0.8 mA typical at 5 V, 1.6 mA max at 36 V over −40…85°C; use 1.6 mA each as conservative design envelope, not a separately guaranteed 3.3 V test point. | 0.01056 W envelope |
| TLV9002 | §6.5 60 µA/channel typical; 85 µA/channel full-temperature maximum at specified 5.5 V test. | 0.000561 W envelope |
| TLC555I | TI 5 V table 180 µA typical, 600 µA full-range max; allocate 1 mA at 3.3 V pending circuit verification. | 0.0033 W assumed |
| 3 SN74LVC1G74 | 10 µA/package max static at rail-valid inputs; excludes switching and ΔICC for slow/intermediate inputs. | 0.000099 W static |
| Supervisor, pullups, references, timer/difference network and dynamic allowance | **5 mA combined assumed cap**, including extra gate/state logic. | 0.0165 W assumed |
| **Total bounded low-voltage design envelope** | Sum above, round upward | **0.362 W** |

Use **60% assumed conversion efficiency**, not a TI guarantee: 0.362/0.60=0.6033 W. Allow another **0.10 W** for reverse diode, HV sense/UVLO networks and converter bias/loss-accounting contingency → 0.7033 W. **0.8 W pack input acceptance cap** leaves 96.7 mW. Converter bias is already part of a measured end-to-end efficiency; the extra term is deliberate contingency, not an alternate physical definition of efficiency. Validate startup and both-driver transfer current across voltage/temperature; exceeding either cap invalidates this envelope. No relay coil is included.

### SINK12 + retained independent safety logic

| Load | Computation / status | Nominal or design-envelope W |
|---|---|---:|
| R39 1k | 12²/1000, nominal | 0.144000 |
| R40/LM4040 branch | 12(12−2.5)/4700, nominal total input | 0.024255 |
| U6 LM339B | 12×1.6 mA conservative envelope; typ 0.8–1 mA depends supply | 0.019200 |
| U10 UCC27511 static | Typical operating current plotted in §8.7 / described §9.3.2; **1 mA assumed cap**, not the 145 µA UVLO startup-current spec | 0.012000 |
| R46/R47 | 12²/40000 | 0.003600 |
| U4 input for SAFETY3V3 | **6 mA output-load cap**, versus 5.364 mA worst pullups alone; plus 5 mA ground-current allowance | 0.132000 |
| **Sum** | Mix of nominal computations / explicit envelopes, not guaranteed total maximum | **0.335055** |

At the same **60% assumed conversion efficiency**, input is 0.558425 W. Add 0.10 W tolerance/bias/unmodeled leakage reserve: **0.658425 W**, and round to **1.0 W early sink input acceptance envelope**. The 6 mA safety cap leaves only 0.636 mA above worst pullups: verify the actual gates, analog outputs and supervisor and forbid external J5 loading. If it fails, the cap must be revised and precharge rerun, not called measured compliance. At nominal supply using 0.8 mA U6, 0.3 mA indicative U10 and 2 mA LDO ground current, but retaining the same pessimistic 6 mA logic load, the corresponding illustrative low-voltage sum is **0.281055 W**; there is no measured typical whole-rail figure.

The 1 W is **standby during precharge, not active braking power**. Active gate charging adds `Pgate = Qg_total × 12 V × f_chop` and gate pulldown loss; neither chopper frequency nor worst-case Qg has been qualified here. Dump resistor energy comes from DC_LINK and is separate from driver supply consumption. Any premature OV/chop activation prevents ordinary ready and must latch fault rather than silently invoking this standby envelope.

## 4. Why 22 ohm works conditionally and 100 ohm does not

For ready mismatch Δ=1 V, the available steady bus auxiliary power is

`Pavailable = Vbus × Δ / Rtotal − Vbus²/Rbleed`.

Use source resistance 0.15 ohm, Rpre high tolerance 22.22 ohm, 10k bleeder, Vbus=Vpack−1. At 36 V: **1.442095 W**; at 58.4 V: **2.236461 W**. Reserve 0.04 W for bus HV sensing, disabled supply leakage and UVLO dividers outside the 1 W sink. Margins are then **0.402095 W / 1.196461 W**. These are positive with no invented 0.1 W sink. At 100 ohm nominal plus 0.15 ohm source the corresponding 36 V limit is only about **0.227 W**; even the retained R39 plus regulator/safety demands cannot fit.

A standalone numerical cross-check executed during this audit integrated `C dV/dt=(Vs−V)/22.37−V/10000−P/V`, C=1.5 mF, P=1.04 W once V≥16 V, zero prior to UVLO, timestep 1 µs. Reaches 1 V mismatch at **0.166955 s (36 V)** and **0.162515 s (58.4 V)**. This is a budget sanity check, not the parent state-machine model or a converter transient simulation. Add ready qualification, driver ramp and main proof before enabling drive. Parent integration must exercise real UVLO bounds, startup pulse, tolerance, capacitance and current-limited source cases.

At Rpre low tolerance 21.78 ohm plus 0.15 ohm source, initial precharge current is **1.64159 A at 36 V / 2.66302 A at 58.4 V**. A practical modeled source prerequisite is **at least 3 A available during precharge**, including CTRL input (~22.2 mA at 36 V / 13.7 mA at 58.4 V), but that is not a claim about an installed BMS. Output capacitor charging and available source current must be modeled explicitly. Recommend sink startup cap **2 W input for ≤30 ms** as an acceptance test envelope, then ≤1 W; it covers 47 µF at 12 V (3.384 mJ stored) with conversion/load margin, but is not a measured inrush bound. No large downstream load/capacitor bank may join this rail during precharge.

At a hard bus short, worst conservative resistor energy neglecting all beneficial source impedance is `58.4²/21.78 × 0.350 = **54.80698 J**`; instantaneous power is **156.591 W**. At 36 V the same bound is **20.82645 J**. This is why the timeout must shorten from 1.5 s: at 1.5 s the high-voltage fault would be **234.886 J**. Use an independently bounded timer maximum ≤350 ms (nominal TLC555 1.1RC: 274k×1µF≈301 ms, tolerance/leakage not yet closed), no automatic retry, cooldown interlock and independently interrupting thermal protection. A welded PRE pair can sustain ~157 W: a logic latch cannot remove it, and the branch fuse may not clear at ~2.7 A.

## 5. Source ledger and release gates

Manufacturer PDFs fetched directly and checked as text on 2026-11-10:

| Source | Specific evidence used |
|---|---|
| [TI TPSI3052, SLVSGS3B](https://www.ti.com/lit/ds/symlink/tpsi3052.pdf) | §5 pins; §6.3 3.0–5.5 V, capacitor ratio; §6.9 26 mA **typical** at 3.3 V/20k; §8.3.8 three-wire sequencing. The §6.5 dissipation test is not a universal maximum-input-current specification. |
| [TI LM5164, SNVSAU4D](https://www.ti.com/lit/ds/symlink/lm5164.pdf) | §4 pins; §5.5 rising 1.45/1.50/1.55 V, falling 1.35/1.40/1.44 V, soft start 1.75/3/4.75 ms; active bias 600/880 µA, shutdown 3/15 µA; §7 reference/ripple design. Efficiency graphs are **typical**. |
| [TI LM339B, SLCS006Z](https://www.ti.com/lit/ds/symlink/lm339b.pdf) | §6.7 whole-package supply current and VCC−2 V full-temperature common mode. |
| [TI TLV760, SNVSAV1A](https://www.ti.com/lit/ds/symlink/tlv760.pdf) | §6.5 ground current 2 mA typical / 5 mA max **specified no load**; retain as allowance, verify loaded behavior. |
| [TI UCC27511, SLUSAW9F](https://www.ti.com/lit/ds/symlink/ucc27511.pdf) | §8.5 UVLO startup-current test is NOT normal operating current; §8.7 operating-current curves; §9.3.2 and power-dissipation discussion require switching charge and pullups in addition to quiescent current. |
| [TI TLV9002](https://www.ti.com/lit/ds/symlink/tlv9002.pdf) | §6.5 60 µA/channel typical, 85 µA full-temperature limit at stated test supply. |
| [TI TLC555](https://www.ti.com/lit/ds/symlink/tlc555.pdf) | 5 V electrical table: 180 µA typical; TLC555I 600 µA full-temperature limit. 3.3 V circuit allowance is separately labeled. |
| [TI SN74LVC1G74](https://www.ti.com/lit/ds/symlink/sn74lvc1g74.pdf) | Electrical table 10 µA maximum static ICC and 500 µA ΔICC for intermediate input; no slow floating state inputs permitted. |

**Unclosed release gates:** complete candidate low-voltage netlist and analog error budget; prove common-mode and fail-safe startup; measure CTRL ≤0.8 W and sink ≤1 W over the agreed range; qualify startup caps and all leakage/backfeed paths; enforce external-load exclusion; bound supply and driver latency; qualify 22-ohm ≥55 J mounted fault pulse and independent thermal interruption; source impedance/current/BMS behavior; main FET closing current/SOA and turnoff transients; active dump gate-charge, thermal and PM cold-start envelope. The recommendation permits further design/model work only, not energization.
