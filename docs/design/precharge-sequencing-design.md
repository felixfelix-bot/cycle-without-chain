# Precharge and auxiliary sequencing — proposed implementation contract

> **Numerical architecture superseded:** [budget revision](precharge-budget-revision.md) replaces 100 Ω, 0.1 W sink, 0.5 W CTRL, and the LDO cascade. Below is historical rationale, not the current build contract.

> **STATUS: CONSULTANT ANALYSIS — NOT A DECISION RECORD. NOT SAFE TO ENERGIZE.** Docs/model only; no schematic, PCB, ordering, operation or hardware approval. Follow-up independent review: [precharge-review.md](precharge-review.md). Its corrections supersede the historical price-verification and pin-level-readiness language below; architecture and auxiliary budgets remain blocked.

2026-11-10; branch `pr/precharge-design`; worktree `/home/c08r4d0r/worktrees/cycle-precharge-design`; base `d07bdb2` (fetched github/master). Read first: `entry-review.md`, `dc-entry-milestone.md`. Scope: source switching/boot dependencies, not FSR/brake changes. 120 kg rider/payload excludes bicycle mass. Human-powered short buffer; 36–58.4 V, 500 W screen and 15 A target are NOT installed ratings or a final battery chemistry.

## 0. Recommendation and decisions

**D1 — split power domains, not merely delay all auxiliaries.** An early, reverse-protected pack-fed controller operates the entry switches without MCU boot. Delay the substantial drive/MCU auxiliary load until main conduction is proven. A separate **always bus-fed sink controller** survives ordinary pack disconnection. Its standby input allocation is **0.10 W**, not the existing entire AUX12V load. At 57.4 V, the old 100 ohm branch allows only **0.244524 W** additional input power: postponing the MCU but leaving the old auxiliary rail intact is not a solution.

**D2 — retain resistor precharge; replace manual jumpers with two independently driven back-to-back MOSFET pairs.** Candidate baseline: four IRFP4568PbF 150 V MOSFETs, two TPSI3052DWZR isolated 15 V static drivers. One pair bypasses the resistor; the other switches its branch. Fully enhanced channels permit both motoring and regen. No series power diode. Each pair is common-source, drains at the external endpoints. The isolated gate driver avoids exposing an ordinary high-side controller's TS pin to negative pack voltage. 150 V, not 100 V: a +58.4 V bus opposite a −58.4 V pack can impose **116.8 V** across one off device. Transient margin still needs qualification.

**D3 — latch timeout, do not retry a hot resistor.** Nominal timeout 1.5 s, ready requires |pack−bus| <1 V for 20 ms, followed by main confirmation and 20 ms settling before drive AUX enable. Model gives close at **0.85245 s**, precharge energy **2.602695 J**; 1 ohm bus fault dissipates **49.336146 J** before timeout. The latter, not capacitor energy alone, governs resistor qualification.

**D4 — baseline is lowest-complexity credible candidate, NOT a proven cheapest complete BOM.** Historical quoted partial silicon subtotal is $47.876 (arithmetic checked, purchase-price tiers unverified) (four MOSFETs, two drivers, two LM5164 controllers). This excludes passives, third-party assembly, protection, third supply if needed, and instrumentation. No fabricated complete cost. An optional rated relay adds $108.11 before driver hardware. Price/stock and qualification can reverse this choice.

## 1. Existing connectivity actually read

Read-only `hardware/powerboard-reva/exports/powerboard-reva.net`, `generate_schematic.py`, `protection_circuit.py`:

* ENTRY_FUSED = F1.2, J41.1, J42.1; BUS_SHUNT_HI = J41.2, R116.2, R117.1, J43.1.
* R117.2, C73.1/C74.1, R118.1, D20.K, U3.1 and both bridge VDRAINs join DC_LINK.
* U3 R-78HB12-0.5 directly feeds AUX12V from DC_LINK. AUX12V powers U1/U2 VM, U4 safety LDO, U6 comparators and U10 driver. R39 1k alone draws 12 mA at 12 V (0.144 W output); R40 reference bias adds load. Thus **0.10 W sink budget cannot describe this unmodified rail**.
* D20 remains a shunt reverse clamp, not a source isolator. No shared hardware files changed.

## 2. Option comparison

| Architecture | Result / decisive constraint |
|---|---|
| Existing passive harness, early entire bus AUX | Reject: model 1.2 W output / 80% efficiency plus startup surge never reaches ready; timeout, bus peak 54.9283 V. |
| All control powered only after main closure | Reject circular dependency unless a separate analog trickle controller is added; then it is no longer “all delayed.” |
| Early full pack-side AUX | Electrically workable for boot; do NOT move sink exclusively to pack. Requires power-OR or extra sink supply; more idle draw and backfeed paths. |
| **Early small pack controller + delayed drive AUX + always-bus sink** | Baseline. Extra supply and signal partition are mandatory, not optimizations. Sink idle envelope must be met or precharge resistance/time/ready criterion must change. |
| LTC4368-1 B2B circuit breaker | Useful bidirectional current protection, but specified reverse protection −40 V is insufficient for −58.4 V; 60 V operating ceiling too close to screen. Not selected. |
| LTC7001 + B2B | Strong static driver, but TS minimum −6 V means reverse pack needs additional protection; do not assume two FETs alone protect driver pins. |
| VOM1271T photovoltaic drive | $2.08 each attractive, but minimum 7.8 V open circuit at 10 mA LED, only 6 uA minimum short-circuit current at 25 C; not guaranteed 10 V Rds(on) drive. Slow linear passage/temperature burden. Rejected for baseline main switch. |
| Panasonic HEV2AN-P-DC12V | Two series contacts; specified 20 A/800 V resistive forward and −20 A/400 V reverse, 40 A/800 V inrush endurance in cited table. 1.92 W coil, $108.11, bulky. Credible optional independent isolation, not fuse substitute. |

## 3. Provisional next schematic net/function specification (new refs reserved by implementer)

This is a **net/function contract**, not a finished pin-numbered schematic. Final package pins, gate capacitance sizing, analog tolerance stack and protective component ratings must be independently checked before implementation approval.

1. Keep SOURCE_POS → F1 → ENTRY_FUSED, common PGND return. Replace J41 with QMAIN_A drain at ENTRY_FUSED, QMAIN_B drain at BUS_SHUNT_HI; sources tied MAIN_FLOAT. Each gate receives its own 10 ohm series resistor from MAIN_DRV; 100k gate-source and 18 V gate-source clamp per device. TPSI3052 VSSS→MAIN_FLOAT, VDRV→MAIN_DRV; secondary capacitors only to its floating rails. **Never connect VSSS to PGND.** Three-wire primary supply CTRL3V3, VSSP→PGND, EN→MAIN_CMD with 100k pull-down. Select non-S continuous variant, not one-shot S variant. Copy manufacturer three-wire application capacitance/PXFR design, verify minimum 10 V actual gate drive across temperature before claiming 5.9 mOhm.
2. Replace J42 with second identical common-source pair (QPRE_A drain ENTRY_FUSED; QPRE_B drain PRE_OUT); PRE_OUT→R116 100 ohm→BUS_SHUNT_HI. Driver EN→PRE_CMD. Both paths must block reverse when off. Retain shunt and bleeder. No energized manual jumper sequence.
3. ENTRY_FUSED→dedicated small branch fuse→200 V reverse-blocking diode (candidate STTH1R02A)→CTRL_RAW→LM5164DDAR, configured 12 V from TI reference design. This diode is ONLY in the controller branch, never traction path. CTRL12→TLV76033DBZR→CTRL3V3. Dedicated branch fuse rating and downstream short protection remain to be selected, not borrowed from 20 A F1. Limit controller allocation to 0.5 W input in model. Avoid GPIO/ADC paths that backfeed a reverse or missing pack. Pack sense divider top chain must tolerate −58.4 V with current-limited clamps; logic may not interpret a clamped reverse voltage as valid pack.
4. Keep U3 on DC_LINK **only for sink service**, or replace with second LM5164DDAR 12 V reference circuit for higher input ceiling. Rename output SINK12; retain autonomous OV reference/comparator and dump gate driver on SINK12, separate safety rail SINK3V3 as needed. Do not tie SINK12 directly to CTRL12. Remove/move R39 and unrelated loads from this rail; audit complete current budget including reference, comparator, driver switching charge, bias and converter losses. Existing U3 has no convenient EN: simply holding MCU reset does not inhibit its input power.
5. Drive/MCU supply is a separate enabled converter or switched downstream supply. Candidate third LM5164DDAR with EN/UVLO forced low until MAIN_PROVEN. Its input bypass capacitance counts in 1.5 mF. Configure 30 V rising / 28 V falling design UVLO, verify thresholds with actual EN hysteresis/tolerances; 12 V output with 0.1 A running, 0.1–0.5 A startup for 30 ms is **allocated**, not measured. Preserve original MCU external supply supervision; no boot auto-arm.
6. Analog sequencer, powered CTRL3V3/CTRL12: matched 0.1% pack/bus dividers nominal 240k/10k (split HV resistors), protected inputs, TLV9002IDR buffer/difference stage biased at 1.65 V; LM339BIDR window comparators, independent source-valid window, TLC555IDR timeout, SN74LVC1G74DCUR fault/state memory with power-on supervisor. At 1:25 scaling, 1 V difference is 40 mV. Full resistor/opamp/comparator/reference error must be subtracted from threshold: design nominal 0.75 V window with ≤0.25 V worst-case error. 0.1% independent divider ratio errors can already contribute about 0.23 V worst-case differential at 58.4 V; therefore **use matched networks/tighter ratios or calibrate/trim and bound drift**, not blindly the nominal divider. Model uses ideal 1 V boundary, not this unclosed error budget.
7. CHECK with both commands low, monitor off-state voltage/current; then PRE_CMD high only if pack-valid, DISCHARGE_ALLOWED, sink healthy and no latched fault. Nominal TLC555 timeout 1.1RC: 1.37 Mohm/1 uF gives 1.507 s; capacitor leakage/tolerance and timer temperature must bound maximum <1.7 s. Ready 20 ms stable→MAIN_CMD; maintain PRE until main proven, then PRE low; drive AUX enabled only after confirmation/settle. MAIN_PROVEN must include commanded gate supply plus electrical response (mismatch collapse under known small test load), **not solely low voltage difference**, since a charged open bus already has that. MCU has veto only, no authority to bypass ready/timeout.
8. Hardware fault latch clears both commands and drive AUX enable, never sink power. Manual release/re-arm only after fault remediation, verified dead/discharged circuit and resistor cooldown. No automatic retry. Loss of CTRL supply defaults gates off. Gate kill is not a stop to PM diode generation.
9. Separate CHARGE_ALLOWED and DISCHARGE_ALLOWED inputs default false with missing cables/supply. Conservative baseline opens pack when either required permission is lost; no claim of discharge-only flow through closed B2B FETs. Inhibit generation/propulsion appropriately and use qualified bus sink. Software cannot enforce BMS charge acceptance by itself. Battery-absent bus generation is an independent operating case, not an entry-controller start event.

## 4. Quantitative model and honest limits

Run from `analysis/precharge`: `python3 model.py`; `python3 -m unittest discover -s tests`; repeat with `python3 -O`.

Equation: C dVbus/dt = Ipack + Iregen − Vbus/Rbleed − Paux/Vbus − Isink − Vbus/Rshort. Source: (Vpack−Vbus)/(Rsource+Rpath), clipped by **assumed external** discharge/charge limits. Converter UVLO hysteresis and 30 ms startup current envelope are modeled, rather than treating the bus as an unloaded capacitor. Euler step 50 us; convergence checked at 25 us. Source R=0.15 ohm, main pair=0.012 ohm, current limit=15 A and charge acceptance=2 A are test assumptions, NOT switch/BMS capabilities. Reverse pack, initial live bus, limited source, short, sink excess idle load, regen accepted/refused, and shorted main are exercised. 18 combinations span 36/48/58.4 V, 940/1500 uF, 0.1/0.3/0.5 A startup.

| Actual model output | Result |
|---|---:|
| Delayed drive aux close time / mismatch | 0.85245 s / 0.9687797 V |
| Normal resistor energy / peak pack current (includes closing) | 2.602695 J / 5.980122 A |
| Bus short resistor energy to latch | 49.336146 J |
| 30 mA source limit | timeout; peak branch 21.438 mA after controller allocation |
| Pack absent, 1 A PM injection, 3 s | maximum 60.032999 V; sink 172.035662 J |
| Regen refused at 1.2 s | pack opens; sink 106.347344 J |
| Regen accepted at 1.2 s | returned 101.618060 J into hypothetical accepting source |
| Main shorted | fault detected but bus remains 58.398777 V — NOT isolated |

**RED/GREEN:** first run failed import because model absent. First implemented run exposed hot-bus test failure: dump control reduced an initially hot bus before delayed CHECK sampled it. Fixed by latching initial hot-bus condition. Final 13 tests PASS normal (7.044 s) and optimized (9.433 s). These verify algorithm intentions, not actual comparator/gate waveforms. Weld detection in model uses injected fault knowledge; real diagnostic coverage must be proven with electrical test stimulus. Charge refusal is instantaneous in this ideal state model; actual sensing/turnoff latency and charge overshoot are unmodeled.

No vendor SPICE model used, no ngspice result claimed. Semiconductor SOA, parasitic L, gate Miller behavior, switch turnoff overshoot, converter regulation loop, contact arcs, sensor faults, thermal dynamics, and supply startup latency are NOT solved. Dump hysteresis 60/59 V is an ideal plant assumption, not a validated bound or revised schematic threshold. For PM cold start, available time from 15 V sink startup to 60 V is C(60−15)/I: 67.5 ms at 1 A and 4.5 ms at 15 A at 1.5 mF. A 3 ms nominal converter soft-start does NOT establish complete sink readiness inside either limit. At 940 uF time is smaller. No pack-absent fault-tolerance claim until this is measured and bounded.

## 5. SOA, energy and failure boundaries

* Main closing must not perform the 58.4 V/1.5 mF charge in its linear region. Residual energy at 1 V mismatch is 0.5 C ΔV²=0.75 mJ; at assumed 0.162 ohm loop, initial current ≈6.17 A. At 10 mOhm unknown loop, 1 V means 100 A: voltage match alone does not bound pulse current. Main gate turn-on and energy-sharing still require vendor SOA plot and measured R/L/current. Do not derive DC interrupt rating from 171 A headline silicon current.
* Precharge FETs switch resistor-limited ≤0.584 A at nominal 58.4 V; turn-on transient crosses high Vds before enhancement. Check full waveform against temperature-derated SOA, not only average dissipation. Main pair cold conduction target: 2×5.9mΩ×15²=2.655 W; hot Rds(on), cooling, terminals remain open.
* RH050100R0FE02 nominal 50 W requires specified chassis mounting. 1.7 s worst timeout at 58.4²/100 is **57.98 J** conservative stalled envelope. Require mounted pulse/thermal evidence, a normally closed thermal cutoff in PRE enable, and no automatic retries. Open timer or shorted precharge FET means continuous ~34 W: fault latch alone cannot remove a welded path. Fuse does not necessarily clear 0.584 A.
* MOSFETs are semiconductor isolation, NOT touch-safe galvanic disconnect. Single short may defeat reverse blocking in one direction. Four devices/two branches are not redundant series safety barriers. A failed main switch cannot be isolated by opening parallel precharge. Independent rated series contactor is the optional improvement; two series contacts in one relay are not independent actuators.
* Fuse clearing at real prospective battery current, inductive opening clamp/SOA, and 100 V existing bridge/cap/supply maximum voltages remain release gates. 150 V entry devices do not upgrade the rest of the bus. No “TVS selected” claim: clamp must stay below weakest rating while absorbing wiring energy; selection needs current/L and duration.

| Failure, severity priority (likelihood unmeasured) | Response / residual risk |
|---|---|
| Main short/weld, reverse pack | Dangerous; detect abnormal off-state response, prohibit start, independent disconnect optional. No single-fault isolation claim. |
| Sink supply fails/too slow with PM | Dangerous bus OV despite open pack; qualification blocker, mechanical brakes independent. |
| BMS full/cold/open or permission loss | Open pack/inhibit active generation; residual uncontrolled PM goes to bus sink only within its validated domain. |
| Precharge short/timeout failure | Resistor sustained heating; independent thermal interrupt required, fuse coordination unresolved. |
| Divider open/short, comparator stuck | False ready possible; independent plausibility diagnostics/dual-channel review required. Not safety-rated. |
| MCU absent/crashed | Entry hardware still sequences; propulsion remains inhibited; autonomous sink does not need MCU. |

## 6. Candidate BOM and price evidence

See `analysis/precharge/candidate-bom.csv`. USD displayed supplier prices accessed 2026-11-10, excludes VAT/shipping; stock/checkout not guaranteed. $47.876 is a **partial** baseline (4×$6.864 + 2×$5.24 + 2×$4.97). Third enabled drive converter adds historically quoted IC-only $4.97 if not reusing an independent qualified supply. Optional series HE-V adds $108.11 plus coil driver/clamp and 1.92 W controller output demand, invalidating the 0.5 W controller allocation. Unknown rows stay unknown; no complete cheapest-price claim.

Primary evidence:

* [IRFP4568 datasheet](https://www.infineon.com/assets/row/public/documents/24/49/infineon-irfp4568-datasheet-en.pdf): 150 V, max 5.9 mOhm at 10 V gate; SOA Fig 8 and transient thermal plot must be checked on actual switching waveform. [Arrow displayed $6.864](https://arrow.com/en/products/irfp4568pbf/infineon-technologies-ag).
* [TPSI3052 datasheet](https://www.ti.com/lit/ds/symlink/tpsi3052.pdf): isolated 15 V rail, 1.5/3 A peak driver; three-wire 3–5.5 V primary. [DigiKey displayed TPSI3052DWZR $5.24 related item](https://www.digikey.com/en/products/detail/texas-instruments/TPSI3052SQDWZRQ1/19236281); do not buy S variant by accident.
* [LM5164 datasheet](https://www.ti.com/lit/ds/symlink/lm5164.pdf): 6–100 V, 1 A, nominal 3 ms soft-start, programmable EN. Copy 12 V/68 uH/47 uF reference plus ripple network, not just IC. [DigiKey displayed DDAR $4.97, zero stock](https://digikey.com/en/products/detail/texas-instruments/LM5164QDDARQ1/10434647).
* [Panasonic HE-V manufacturer datasheet via distributor](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8810/mech_eng_hev.pdf): use both contacts in series; forward and reverse resistive ratings distinct. [DigiKey $108.11](https://digikey.com/en/products/detail/panasonic-electric-works/HEV2AN-P-DC12V/3945771). Actual inductive DC interruption and mounting/temperature not proven here.
* [VOM1271](https://vishay.com/docs/83469/vom1271.pdf), [price $2.08](https://digikey.com/en/products/detail/vishay-semiconductor-opto-division/VOM1271T/3588700); legacy mirror differs isolation rating, so use current manufacturer revision for any future adoption.
* [LTC4368](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc4368.pdf), [LTC7001](https://www.analog.com/media/en/technical-documentation/data-sheets/ltc7001.pdf); reverse protection limitations explicitly disqualify unmodified circuits.
* [Vishay RH/NH](https://www.vishay.com/docs/30201/rhnh.pdf); direct extraction blocked, prior entry milestone cites same primary document. No new pulse-curve validation claimed.

## 7. Work left before circuit release

Close actual three-domain auxiliary current/startup envelopes; sink ≤0.10 W standby is an acceptance requirement, not a solved measured fact. Select/verify matched sensing network, timer components and actual state-gate pin wiring. Prove main confirmation detects failed-open switch and recognizes PM-driven bus without falsely diagnosing a weld. Measure source min/max R/L and prospective fault current; select branch fuses/transient clamps; complete reverse live-bus testing in simulation first. Validate SOA and resistor hot-fault pulse/cooldown. Quantify turnoff latency versus BMS charge budget. Finish sink cold-start/thermal/PM envelope and physical disconnect protections. Obtain independent review. These gaps block energization/order/PCB, not publication of this independent design contract.
