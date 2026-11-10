> **STATUS: CONSULTANT ANALYSIS — NOT A DECISION RECORD. NO ENERGIZE / NO FAB.** Numerical candidate and next-sheet contract only; no implemented hardware, validated SOA, diagnostic safety integrity or isolation claim.

# MAIN_PROVEN: bounded electrical proof candidate

2026-11-10 · worktree `/home/c08r4d0r/worktrees/cycle-precharge-budget` · lens: electrical diagnostic observability, not supply redesign. Read with [sequencing](precharge-sequencing-design.md), [independent review](precharge-review.md) and `analysis/precharge/model.py`. Existing `hardware/powerboard-reva/entry_circuit.py` and those documents were read; no shared hardware/model changes were made. All new values below are **requirements**, except explicitly sourced silicon limits and computed results. This document supersedes the implication that PRE can remain on throughout electrical MAIN proof.

## 0. Decision and limits

**D1. Use a known switched 330 ohm bus load for 40 ms, with PRE commanded OFF, after MAIN closure.** Observe both pack-to-bus mismatch and the injected-load current. MAIN_PROVEN requires the response, not merely MAIN_CMD or a charged bus. Keep PRE on during the initial MAIN gate-establishment interval; then remove PRE for the diagnostic interval. If MAIN fails open, do not re-enable PRE automatically: latch fault, AUX stays off.

**D2. Restrict this proof to physically stationary/disconnected PM machines and bounded other sources.** A bus fed independently by a PM bridge can perfectly mimic a conducting main switch. No voltage-only algorithm resolves this ambiguity. Require independently established `PM_QUIET_VALID` and total unmodelled injection ≤10 mA throughout the test; MCU PWM-off is NOT this evidence. Without that condition the outcome is **INDETERMINATE**, never MAIN_PROVEN. Likewise do not call an energized bus a welded main merely because it matches the pack.

**D3. Use a ±0.50 V nominal main-proof window with ≤0.20 V total bus-referred uncertainty.** Actual |Vpack−Vbus|≤0.30 V guarantees passing; ≥0.70 V guarantees failing. This is separate from the original pre-close 1 V window. Require healthy path plus sensor response to settle inside the tighter window before evaluating the final 5 ms of the pulse. This does not establish 15 A capacity or reverse-current conduction.

**D4. A full pair short, one shorted MOSFET, failed-open MAIN and failed PRE are different faults.** The diagnostic rejects a high-impedance MAIN even if the 22 ohm PRE path remains conducting, under the bounded assumptions below. It cannot distinguish a full MAIN short from another sufficiently low-resistance pack-to-bus bypass. Nor can one directional test rule out a single shorted FET/body-diode path.

## 1. Exact power-sheet attachment contract

Existing anchors: `entry_circuit.py:8–18`; sequencing §1 identifies generated passive references. Existing pins remain historical connectivity, not authority to manipulate jumpers energized.

| Next-sheet terminal | Exact attachment / function |
|---|---|
| PACK_KELVIN | ENTRY_FUSED at F1.2 / existing J41.1 / J42.1; sense before MAIN and PRE |
| BUS_KELVIN | DC_LINK at R117.2 / J43.2 (also J43.3), **not BUS_SHUNT_HI** |
| PGND_KELVIN | J43.4 / capacitor negative return; route separately from diagnostic load current |
| DIAG_POWER | DC_LINK → dedicated diagnostic branch protection → RDIAG 330 ohm → QDIAG drain |
| DIAG_RETURN | QDIAG source → RDIAG_SENSE 1.00 ohm → PGND; Kelvin sense both ends |
| DIAG_CMD | hardware pulse gate → QDIAG gate driver; gate-source pulldown; default off on CTRL invalid |
| MAIN_CMD / PRE_CMD | the two TPSI3052 EN pin 1 inputs; primary VDDP pin 3=CTRL3V3, VSSP pin 4=PGND |
| GATE_VALID | new isolated floating gate/secondary-supply monitor per pair; **not a TPSI3052 output** |
| MAIN_PROVEN | reset-dominant state latch output; controls delayed drive-AUX enable only; never powers off autonomous sink |
| DIAG_CURRENT_VALID | window comparator on RDIAG_SENSE; active only during stimulus; hardware low at rest |

Use reserved symbolic references until schematic owner assigns real references; do not reuse R116/R117. The diagnostic branch bypasses neither R116 nor MAIN; it is a bus load. RDIAG effective resistance including temperature/pulse drift must remain 326.7–333.3 ohm. Allocate total branch resistance **326.7–334.5 ohm**, with shunt+FET ≤1.20 ohm (including shunt tolerance and hot FET resistance). The lower bound deliberately ignores positive shunt resistance for conservative stress calculations. Select QDIAG voltage/transient rating against the real bus clamp, not its nominal 60 V; package/pins, pulse resistor part, protection and driver are **unselected release blockers**. An open pulse-load path must cause missing DIAG_CURRENT_VALID, not a pass.

Source-backed TPSI3052 pin assignment: TI [SLVSGS3B](https://www.ti.com/lit/ds/symlink/tpsi3052.pdf), Table 5-1, as checked in review §TPSI3052. Pins 5/6/7/8 are VSSS/VDDM/VDDH/VDRV. VSSS remains the corresponding floating common-source node. There is no READY/PG feedback pin. A floating monitor implementation and its failure behavior are still required; EN high is not gate proof. Add this monitor's load to PXFR/CDIV and pack-controller budgets.

## 2. Concrete analog measurement candidate

Replace the unspecified TLV9002/LM339 difference path for this diagnostic with **OPA4197IDR (SOIC-14) plus TLV1702DGKR (VSSOP-8)**. This is an optional candidate, not a completed precision BOM. Power both from SINK12, never CTRL3V3: OPAx197 requires ≥4.5 V. Local 100 nF bypass per IC; SINK12-valid reset prevents startup outputs being interpreted as valid.

Two nominal 240k/10k dividers make `VP=PACK_KELVIN/25`, `VB=BUS_KELVIN/25`. Split each 240k upper leg into appropriately voltage-rated series resistors. **Require each aggregate resistance within ±0.01% over the entire qualification temperature range including initial error, drift and voltage coefficient**, not merely 0.01% at room temperature. This is a procurement requirement, not a sourced stock network. Protect bipolar/missing-pack inputs against −58.4 V and bus transients with external current limiting/clamps that cannot back-power an unpowered CTRL supply; protective parts/pins and leakage remain blockers. A clamped negative input must not satisfy PACK_VALID.

Pin-exact low-voltage core (TI pin tables cited below):

* OPA4197: pin 4→SINK12; pin 11→PGND. Channel A pin 3→VP, pin 2 tied pin 1; pin 1=`VP_BUF`. Channel B pin 5→VB, pin 6 tied pin 7; pin 7=`VB_BUF`.
* Channel D buffers qualified 2.500 V bias: pin 12→BIAS_2V5; pin 13 tied pin 14; pin 14=`BIAS_BUF`.
* Channel C: 10k from VB_BUF to pin 9; 200k feedback pin 8→pin 9. 10k from VP_BUF to pin 10; 200k from BIAS_BUF to pin 10. Pin 8=`VDIFF=2.5+20(VP−VB)=2.5+0.8(Vpack−Vbus)` nominal. Use a ratio-matched four-resistor network; bound individual effective resistances ±0.01% over temperature. Output saturation outside the ready region is expected, but recovery must be timed/verified.
* TLV1702 pin 8→SINK12, pin 4→PGND. Channel 1 pin 3→VDIFF, pin 2→TH_LOW=2.100 V. Channel 2 pin 5→TH_HIGH=2.900 V, pin 6→VDIFF. Open-collector pins 1 and 7 wired together with 10k to CTRL3V3 form `MATCH_OK`: either out-of-window channel pulls low. Do not infer validity during brownout or a disconnected sense wire.
* BIAS_2V5 and TH_LOW/HIGH must be supplied by a qualified reference/buffer ladder: bias ±5 mV and each threshold relative to actual BIAS_BUF within ±10 mV across temperature/load/startup. **Reference IC, resistor network, buffer output impedances and their exact package pins remain requirements**, not a fabricated finished sheet. No source-backed reference BOM was established here.
* DIAG_CURRENT_VALID needs a separate comparator pair: require true load current 80–200 mA, nominal shunt voltage 80–200 mV. Comparator/threshold/1 ohm shunt error together ≤5 mA; a tighter measured acceptance band may be used. Final pin-numbered current-window circuit and a stuck-high detection test are required. Test LOW before and after pulse, HIGH during; a permanently high input cannot qualify.

### Error ledger: sourced silicon limits versus open component requirements

TI [OPAx197 SBOS737C](https://www.ti.com/lit/ds/symlink/opa2197.pdf), §5 pin functions and §6.7: ±100 µV input offset at listed test conditions; ±2.5 µV/°C drift in lower common-mode region, ±4.5 µV/°C in the upper region; ±5 nA input bias over −40…125°C for D-package (PW has worse bound); power-supply rejection ±3 µV/V over temperature. CMRR minimum 110 dB over temperature in lower region at specified ±18 V supply. These conditions are **not a blanket guarantee of the complete single-12 V front end**: characterize actual common-mode/supply and include residual in allocation. Budget 0.70 mV effective offset per amplifier (100 µV+4.5×100 µV + supply allowance), not the typical 25 µV headline.

TI [TLV170x SBOS589D](https://www.ti.com/lit/ds/symlink/tlv1702.pdf), §6 pin functions / §7.5: offset ±5.5 mV over −40…125°C; bias ≤20 nA over temperature. 560 ns delay is typical, not a worst-case sequencing bound. Full primary PDFs were downloaded and extracted with pdftotext; the web extractor exposed only front matter.

| Contribution | Bus-referred bound / status |
|---|---:|
| Two dividers at 60 V with every resistor ±0.01% effective | ≈0.0231 V, computed `2×60×0.0002×0.96` |
| Two buffer offsets, each allocated 0.70 mV | 0.0350 V, computed `2×0.00070×25` |
| Difference-amplifier offset, noise gain 21 | 0.0184 V, computed `21×0.00070/0.8` |
| Divider buffer bias 5 nA into 9.6k | 0.0024 V total |
| Four-resistor subtractor mismatch | allocate 0.030 V; exact corner solve mandatory before release |
| TLV1702 offset | 0.006875 V, computed `0.0055/0.8` |
| Relative reference/threshold error | 0.0125 V, computed `0.010/0.8` |
| Remaining gain, bias, clamp leakage, CMRR, filter/dynamic/noise effects | remaining ≈0.0717 V of **0.20 V total**; must be measured/bounded |

This is an achievable-looking allocation, **not a closed worst-case tolerance proof**. Specify low source impedance at comparator inputs (≤1k gives ≤20 µV bias error); no uncontrolled positive-feedback hysteresis may silently enlarge the 0.70 V rejection boundary. Sensor filtering must settle within 2 ms after the chosen gate-settle interval. OPA4197's four channels alone consume about 4 mA **typical**, ≈48 mW at 12 V, before comparator/reference/logic losses; reserve actual worst-case input power in the sink budget. Integration reserves 0.10 W for this analog core on SINK12; this is an acceptance limit, not a silicon maximum.

## 3. Pulse envelope and numerical separation

Requirements for the bounded demonstration:

* pack 36–58.4 V; bus ≤60 V; initial signed difference `Vpack−Vbus ≥−1 V` and pre-close |difference|≤1 V;
* **Cbus,max=1.500 mF including capacitor tolerance and all attached converter input caps**, not 1.5 mF nominal. Existing two 470 µF ±20% caps alone span 752–1128 µF (`entry_circuit.py:15–16`); prove all added capacitance fits;
* stimulus 40 ms nominal, **38–42 ms actual**, with final 5 ms continuous comparison; no AUX startup during it;
* unmodelled injection ≤10 mA, pack excursion ≤0.10 V during test; no independent bus regulation/PM generation beyond that bound;
* diagnostic branch 326.7–334.5 ohm; healthy pack-to-bus **total** source+switch+shunt resistance ≤0.50 ohm, background bus load ≤50 mA, no current limiting at test load. These are requirements, not installed ratings.

For an open MAIN, ignore bleed and background consumption (conservative for hiding a droop). For PRE also open, `g=1/Rdiag`; if PRE is stuck on, use worst minimum `Rpre=21.78 ohm`, `g=1/Rdiag+1/Rpre` and `Veq=(Iinj+Vpack/Rpre)/g`. Then `Vbus(t)=Veq+(Vbus(0)−Veq) exp(−gt/C)`. Use `Vpack=36`, `Vbus(0)=37`, `C=0.0015`, `Rdiag=334.5`, `Iinj=.010`, `t=.038` for the pessimistic droop corner. Embedded Python below reproduces the calculation; the 334.3 ohm earlier arithmetic was revised upward to include shunt tolerance/FET resistance.

```python
import math
for rp in (math.inf, 21.78):
    g = 1/334.5 + (0 if math.isinf(rp) else 1/rp)
    veq = (.010 + (0 if math.isinf(rp) else 36/rp))/g
    vb = veq + (37-veq)*math.exp(-.038*g/.0015)
    print(rp, vb, 36-vb)
print('max W,J', 60**2/326.7, (60**2/326.7)*.042)
```

Even with PRE stuck on, calculated mismatch is approximately **1.128 V**, well above 0.70 V rejection boundary; allowing 0.10 V adverse pack movement still leaves >0.328 V separation. For a healthy path, conservative load ≤60/326.7+0.050=0.234 A, giving ≤0.117 V drop at 0.50 ohm, within 0.30 V guaranteed-pass region. Initial ≤1 V mismatch decays with RC≤0.75 ms, but gate startup and source regulation are **additional** settling delays to qualify.

Maximum diagnostic resistor stress is bounded conservatively by **11.020 W and 0.463 J per 42 ms pulse** (assigning the whole minimum branch resistance loss to it). Specify ≥1 J qualified hot-pulse capability at relevant mounting/ambient, plus continuous or independently interrupted stuck-on behavior; a generic wattage marking is not qualification. At a live 60 V bus, stuck-on draws ~11 W indefinitely and must not rely on a tiny fuse opening. No automatic retries; any new test requires cooldown policy.

## 4. State contract and fault classification

1. RESET: clear MAIN_PROVEN, PRE_CMD/MAIN_CMD/DIAG_CMD/AUX_EN low. Preserve independent sink. Validate supplies, permissions, both sense channels, diagnostic-current LOW, PM_QUIET_VALID and temperature/cooldown.
2. CHECK_OFF: both power commands low. A retained charged bus is allowed only as an explicitly handled condition, not evidence of a weld. When near pack voltage, pulse known load and observe droop. Conducting/bypass-looking response → `OFF_PATH_CONDUCTING_OR_EXTERNAL_SOURCE`, inhibit start. Droop → evidence against a **low-resistance forward bypass at this current**, not comprehensive insulation proof. If bus is initially low, no current can flow in the pulse and that pulse is not a valid test of its load circuitry; validate the stimulus later after precharge.
3. PRE: perform existing source-valid/ready/timeout checks; timeout remains absolute and must include proof time. Drive AUX remains off.
4. MAIN_SETTLE: command MAIN on with PRE on. Wait independently bounded driver cold-start/gate establishment; require GATE_VALID. **Do not use typical propagation delay as this timer.** If no worst-case bound fits the global timeout, fail rather than extend timeout silently.
5. PROVE: PRE_CMD low; wait qualified PRE turnoff interval and then pulse DIAG. Require current LOW→HIGH→LOW, gate-valid, pack-valid, PM-quiet and window continuous for last 5 ms. Only then latch MAIN_PROVEN. The original additional 20 ms AUX-settle interval starts after successful proof, not after MAIN_CMD.
6. Fault/brownout/permission loss: reset-dominant clear all entry/drive enables, no automatic PRE retry; retain sink. A weld may remain energized despite this command. Re-arm requires physical isolation/remediation and cooled resistor.

| Observed condition | Honest inference / response |
|---|---|
| MAIN on, PRE off, verified load, bus droops beyond window | MAIN not proven: failed-open/high resistance/weak source possible; latch fault, not “weld” |
| MAIN off, PRE off, verified load, bus remains close to pack | unexpected supply path **or PM/external injection**; classify ambiguous and inhibit; only with valid quiet condition can infer unintended pack path |
| MAIN on and matching, but PM state unknown | indeterminate; do not enable AUX |
| Load missing/open, current comparator stuck high/low, no low-high-low edges | diagnostic invalid; never MAIN_PROVEN |
| PRE failed on with MAIN open | numerical bound rejects under stated conditions; does not prove PRE was physically off |
| One MAIN FET shorted, other off | polarity-dependent body diode may conduct; forward test can flag some failures but cannot guarantee bidirectional off-state isolation |
| MAIN pair fully shorted | electrically conducting even with command off; cannot be isolated by PRE; independent series disconnect needed |
| Sense stuck at valid value / comparators stuck released | single-channel proof can falsely pass; require independent sensor plausibility/test injection or redundant channel; no single-fault-safe claim |

## 5. Remaining release gates

Select all precision network/reference/protection parts with actual full-temperature limits; close resistor-corner and analog dynamic error budget; pin-number current-window and floating gate monitor; implement reset/latch truth table with faults dominant over every transition; qualify actual timer limits and supply startup. Verify the **physical** PM-quiet/≤10 mA premise, maximum C and total source resistance. Exercise failed-open MAIN, stuck PRE, full and single-FET shorts, external source/PM, missing load, stuck comparators and supply-loss states in electrical simulation and then controlled isolated fixtures. Bound clamp/driver switching SOA and resistor hot repetition independently. This analysis cannot approve hardware until those items close. A software `welded=True` oracle and ideal voltage match remain insufficient evidence.
