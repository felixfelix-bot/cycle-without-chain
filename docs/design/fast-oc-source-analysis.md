> **STATUS: CONSULTANT ANALYSIS — UNSAFE DRAFT, NOT AN APPROVAL.** Bounded source/engineering study only; no fabrication, energization or SOA qualification.

# Six-channel CSA window overcurrent candidate

2026-11-10; worktree `/home/c08r4d0r/worktrees/cycle-fast-oc`, inspected base `30560f6a9f54788365362db412c66c81e60d009b`. Read protection milestone/integration reviews, `hardware/powerboard-reva/docs/safety-review.md`, current generator/protection circuit and `mcu-integration-review.md`. Historical HC latch and held-reset defects in the earlier protection report are not the present LVC DFF circuit. This report changes neither circuit nor firmware.

## 0. Recommendation and decisive findings

1. Use **six TLV3202D** dual comparators, candidate ordering code **TLV3202IDR**, SOIC-8, one dual per existing GEN/HUB SOA/B/C. This implements twelve comparisons, not six. Pin assignment is directly verified in TI SBOS561C Figure 5-2/table, not inferred from a generic dual-comparator symbol.
2. **Critical sign: DRV8353 output falls for positive SP→SN current.** TI SLVSDY6A p41 Equation 3 is `I=(VREF/2−VSO)/(G·Rshunt)`. Figure 41 puts SP at the inverting amplifier input. Positive current through the existing low-side shunt therefore trips the **lower** window comparator. The text extractor drops mathematical minus glyphs: Equation 3 and the SP/SN arrow were additionally checked on the rendered manufacturer PDF page. A positive-slope current conversion is wrong.
3. At VREF=3.3 V, G=20 and R=2 mΩ, sensitivity is −40 mV/A. Exact ±20 A corresponds to **0.850/2.450 V**. Candidate 28.7k/10.0k 0.1% divider pairs produce **0.852713/2.447287 V**, or **±19.93217 A nominal**. These are verified arithmetic, not guaranteed current limits.
4. Comparator speed does not establish current interruption speed: CSA settling is **1000 ns typical** at gain20 for a 0.5 V step, without a maximum in the table. Six low-side sensors have PWM-dependent blind intervals and do not independently observe every destructive current path. This is MCU-independent decision logic **after configuration**, not independent sensing or a guaranteed short-circuit protector.
5. Preserve DRV VDS/SEN hardware protection, latch/inhibit and protected-entry work. No allowable fault energy, minimum machine/short-loop inductance, or guaranteed end-to-end shutdown bound has been established.

## 1. Exact candidate connections

[TI TLV3202](https://www.ti.com/lit/ds/symlink/tlv3202.pdf), SBOS561C May2024, pp3–6; raw evidence [tlv3202-excerpts.txt](fast-oc-evidence/tlv3202-excerpts.txt).

| Physical pin, each TLV3202D | Proposed net/function |
|---|---|
| 8 VCC | SAFETY3V3; local 100 nF bypass to pin4 |
| 4 GND | quiet PGND / Kelvin analog return |
| 3 1IN+ | LOW_REF ≈0.852713 V |
| 2 1IN− | raw associated SOx, before existing 100Ω/1nF ADC filter |
| 1 1OUT | active-high positive-current fault (SOx below LOW_REF) |
| 5 2IN+ | same raw SOx |
| 6 2IN− | HIGH_REF ≈2.447287 V |
| 7 2OUT | active-high negative-current fault (SOx above HIGH_REF) |

TLV3202 is **push-pull**: never wire outputs together or directly onto the open-collector ANALOG_OK bus. OR the twelve outputs using properly supplied logic; invert the aggregate to OC_OK. Current U14 SN74LVC1G11 has pin6 tied high; the logical insertion point is **U14.6=OC_OK** in place of that tie. U14.4 HEALTHY then clears both DFFs and inhibits U16/TIMER_BREAK_OK; U17 PE15/PD2 break inputs require the active-low configuration already specified in the MCU review. This is a proposed insertion, not a verified new netlist. An OR/inverter part/pin/latency and supply-loss audit is still required. Do not drive HEALTHY against its existing push-pull gate.

Use **LOGIC3V3_EXT**, the actual DRV VREF supply, for both divider pairs, NOT nominally equal SAFETY3V3. LOW_REF: 28.7k from VREF to node, 10k node to PGND. HIGH_REF: 10k from VREF to node, 28.7k node to PGND. Shared pair is possible but introduces a common reference fault; six independent pairs cost more and do not remove the shared VREF dependency. Reference filtering must be analyzed for startup and transient tracking rather than adding a large capacitor blindly. Comparator inputs have rail clamps: safety-rail-off while VREF/SOx remain alive can inject/back-power. Existing rail supervision is necessary but does not prove that permutation safe. Comparator unpowered must not masquerade as OC_OK.

Operating supply 2.7–5.5 V; specified temperature −40…125°C. Input common-mode range is −0.2 V to VCC+0.2 V. Both thresholds and normal CSA output range fit at nominal 3.3 V. DRV linear SO range is 0.25…VREF−0.25 V, so nominal 0.85/2.45 V thresholds have 0.60 V rail headroom. This does not excuse input overshoot/injection at shutdown. TLV3202 offset maximum is **±6 mV over temperature**, not TLV3201's ±4 mV. Internal hysteresis **1.2 mV typical**, equivalent 0.030 A nominal, has no guaranteed min/max here. No external hysteresis is selected; the downstream persistent latch prevents re-enable chatter but does not reject noise-induced nuisance trips. Any added positive feedback changes both thresholds and must be solved with output swing/loading.

## 2. Threshold accuracy: bounded screen, not full qualification

With lower-divider fraction `a=Rb/(Rt+Rb)`, nominal positive trip is `(VREF/2−a·VREF)/(G·R)`. Negative trip magnitude is symmetric for mirrored dividers. Rail-derived references track the midpoint but **current threshold still scales with VREF**; ratiometric does not mean supply-independent current.

Manufacturer DRV table: G=19.4…20.6 at gain20; input offset ±3 mV; output bias VREF/2 is given as typical (no independent guaranteed midpoint-error bound). Existing shunt is specified as 2mΩ 1% in the generator, not a verified thermal Kelvin assembly. TLV3202 input bias ≤5 nA over temperature; divider Thevenin resistance 7.416kΩ means 37.1 µV per input bias contribution before aggregate loading, small relative to 6 mV comparator offset but not zero.

**Explicit illustrative assumptions**: VREF ±3% (not a qualified supply spec), each divider resistor ±0.1% initial, shunt ±1%, gain19.4…20.6, CSA input offset ±3mV and comparator offset ±6mV. Exhaustive binary-corner arithmetic on

`Itrip = ((VREF/2−VREF·Rb/(Rt+Rb)+Vcmp_offset)/G + VCSA_offset)/Rshunt`

returns **16.92639…23.08413 A**, symmetric magnitude screen. It excludes divider/shunt TCR and self-heating, hysteresis extrema, bias/midpoint uncertainty, ground error, dynamic gain/settling and rail tracking. Do not label this a certified worst-case band. CSA offset alone corresponds to ±1.5 A at nominal shunt; comparator ±6mV alone is ±0.15 A. Software calibration does not automatically calibrate this analog trip. Required operating-current/noise envelope must be below the actual earliest trip, and permitted destructive-current envelope above the actual latest trip plus latency overshoot.

## 3. Required DRV configuration and OCP limits

[TI DRV8353](https://www.ti.com/lit/ds/symlink/drv8353.pdf), SLVSDY6A June2019, §§8.3.4,8.3.6,8.6.2; [raw excerpts](fast-oc-evidence/drv8353-excerpts.txt). Both bridges use SPI DRV8353S, not fixed-resistor hardware variants.

| Register field | Candidate contract / significance |
|---|---|
| 0x06 bit10 CSA_FET | 0: shunt SP input, not MOSFET SH sensing |
| 0x06 bit9 VREF_DIV | 1: midpoint VREF/2 |
| 0x06 bit8 LS_REF | 0: low-side VDS measurement SH→SP |
| 0x06 bits7:6 CSA_GAIN | 10b: 20 V/V |
| 0x06 bit5 DIS_SEN | 0: retain sense OCP |
| 0x06 bits4:2 CSA_CAL_A/B/C | 000 during run; calibration shorts inputs and makes external OC blind |
| 0x06 bits1:0 SEN_LVL | 00b: lowest 0.25 V setting; full listed register payload **0x280** |
| 0x05 bits7:6 OCP_MODE | 00b: latched, not retry/report-only/disabled |
| 0x05 bits5:4 OCP_DEG | 00b: nominal 1 µs; validate switching false-trip margin |
| 0x05 bits3:0 VDS_LVL | Select from hot RDS(on), fault envelope, spikes and tolerance; not chosen here |
| 0x05 DEAD_TIME | Preserve separately qualified bridge timing; no blanket full-register literal |

Set linked fault response OCP_ACT and explicitly audit CBC (only active for retry mode per register table); don't rely on power-on defaults. Table17 and Figure60 disagree on some reset defaults: write and read back the complete intended register image. Reconfigure/verify after sleep/reset before permission. Lock/configuration monitoring policy and safe startup sequence remain firmware work; an external comparator can operate without live CPU decisions but cannot guarantee gain/reference settings against a corrupted driver register.

SEN_OCP monitors **SP shunt voltage**, not SO amplifier output. Lowest 0.25 V corresponds to **125 A** for 2mΩ, not 6.25 A or 20 A. Values are 0.25/0.5/0.75/1 V (nominal 125/250/375/500 A). It is not a symmetric ±20 A limit. VDS_OCP watches enabled MOSFET voltage; `I≈VDS_threshold/RDS(on)` is strongly temperature/gate-drive dependent, not an accurate phase-current comparator. Deglitch options are **1/2/4/8 µs typical**, with no min/max tolerance stated in the electrical table. Neither 1µs deglitch nor 125A arithmetic is a qualified fault-survival bound.

## 4. Latency and low-side blind intervals

TLV3202 switching tables at 2.7 and 5 V give **50 ns maximum** at listed 20/100mV overdrive, 15pF load, and **55 ns over −40…125°C**; typical low-to-high is 47ns at20mV. These endpoint tables are useful evidence, not a blanket arbitrary-load/zero-overdrive/3.3V certification. At nominal CSA sensitivity,20mV is **0.5 A** beyond a static threshold. At exact threshold or a slow noisy ramp do not assume55ns. Input common-mode dependence, actual output fanout and loading remain to be qualified.

DRV CSA settling at gain20: **1µs typical to±1% for a0.5V step**,60pF conditions in associated output specifications; slew10V/µs typical. This is neither maximum delay nor a valid additive1µs bound for every current ramp. Take comparator tap before the ADC100Ω/1nF (100ns nominal RC); its existing downstream capacitive load still loads SOx through100Ω and must be included in CSA stability/response validation.

Required measured/bounded chain is:

`blind time + shunt/CSA response + threshold overdrive acquisition + comparator + OR/inverter + HEALTHY/DFF/inhibit + timer/driver input response + gate discharge/Miller + current commutation`.

DRV IN→gate propagation200ns is typical; ENABLE sleep timing up to1ms is not a fast trip guarantee. Establish the actual ENABLE-to-gate path and hardware timer BREAK response independently, including frozen PWM, before crediting either. Fault memory timing cannot be inferred from a Boolean test.

Low-side measurement sees current only while it traverses its shunt. High-side active/freewheel states, all-high zero vectors, deadtime/diode routing and external phase/bus shorts can leave one or more shunts blind. Three shunts improve reconstruction opportunities, not continuous independent per-phase observability. No PWM frequency/duty/max blind interval is fixed here, so total detection latency is currently **unbounded by this study**. A continuously asserted high-side state can have no periodic low-side sample window. Do not add arbitrary blanking as a remedy: each blank interval increases unseen current. Separate inline/DC-link sensing or a dedicated fast short-circuit path may be necessary; do not remove local VDS protection.

## 5. 58.4V di/dt screen and SOA boundary

For an explicitly assumed effective loop inductance L and constant net58.4V, neglecting resistance/back-EMF and saturation: `dI/dt=58.4/L`, with L inµH giving A/µs; `Ipeak=20+(58.4/L)·delay_us`. These are sensitivity cases, **not measured minimum inductances**. Motor back-EMF may reduce or increase net voltage depending on fault; use actual maximum net voltage for qualification. Saturating machine inductance and local shoot-through loop inductance are different cases.

| Assumed L (µH) | A/µs | I after0.1µs | after1µs | after5µs | after10µs |
|---:|---:|---:|---:|---:|---:|
|0.1|584|78.4|604|2940|5860|
|1|58.4|25.84|78.4|312|604|
|10|5.84|20.584|25.84|49.2|78.4|
|100|0.584|20.0584|20.584|22.92|25.84|

Large values flag model breakdown/source resistance/current limiting, not achievable current predictions. Even a hypothetical1µs chain can add58.4A at1µH; a55ns comparator alone cannot fix a blind interval or an unbounded CSA/turn-off path. For a specified allowable peak `Ilim`, required minimum inductance is `Lmin=Vnet·tdelay/(Ilim−Itrip_max)`; both Ilim and guaranteed delay are currently unqualified.

No allowed joules are asserted for CSD19532Q5B. Needed MOSFET evidence includes hot-start pulsed SOA at actual VDS and duration, gate-drive conditions, transient thermal impedance, repetitive duty, avalanche/clamp path, turn-off overshoot and current sharing. `E=½LI²` is stored loop energy, **not automatically energy deposited in one MOSFET**, and a single-pulse avalanche number would not authorize repeated faults. Compute device stress from `∫VDS(t)·ID(t)dt` only after defining the commutation/clamp paths and temperatures, then compare against the actual manufacturer SOA and thermal limits. No primary SOA extraction or bench waveform is supplied here; survival remains unproved.

## 6. Decision and open gates

Proceed with the TLV3202 window circuit as a bounded schematic increment; **do not describe it as qualified short-circuit protection**. Do-nothing leaves the known independent-fast-trip gap. A faster comparator alone buys little while CSA/blind-time bounds are absent. Separate continuous sensing becomes necessary if required fault coverage includes paths not observed by the low-side shunts.

Before release: qualify exact rail tolerances/sequencing and common reference faults; select OR/inverter with pin/threshold/timing proof; validate SO loading; bound total threshold including midpoint/TCR/hysteresis; define actual minimum inductance and maximum net voltage; prove DRV configuration/readback/calibration interlock; inject each of twelve input faults through the full retained latch and both shutdown paths; test held reset, startup, stuck PWM, lost rail/reference and comparator open/short. Cold electrical review, actual hardware timing and MOSFET SOA closure remain open. This report does not close existing protected-entry, supply-loss sink or ERC blockers.

### Evidence scope

Two primary PDFs fetched successfully with curl, converted using pdftotext; selected unedited text spans and full-PDF SHA256 hashes saved alongside this report (about43kB total). The equation sign needed rendered-page verification because extraction loses minus glyphs. Numerical values in §§0/2/5 were executed in Python, not hand-estimated. No schematic edits, fabrication files, physical tests or manufacturer transient-model simulations were performed.
