> **STATUS: CONSULTANT ANALYSIS — NOT A DECISION RECORD.** No purchase, pack assembly, board change, or riding authorization.
# Short-buffer storage: power before range

| Provenance | Value |
|---|---|
| Date / branch | 2026-11-10 / `pr/storage-evaluation` |
| Base / worktree | `30560f6` / `/home/c08r4d0r/worktrees/cycle-storage-eval` |
| Scope | Energy, cell screening, interface recommendation; not powerboard circuitry or pack qualification |
| Read first | [Powerboard concept](../evaluation/custom-powerboard-concept.md), [project plan](../PLAN-parallel-hybrid.md) |
| Reproduce | `python3 analysis/storage/model.py`; `python3 -m unittest discover -s analysis/storage -v` |

## 0. Answer and provisional decision log

**No-purchase recommendation: reserve a protected, direct-bus small high-power battery interface; do not freeze chemistry yet.** Retain an optional external bidirectional converter interface, not an assumed populated converter. Independent cadence does not require a large battery or a powered-range target. Prefer continuous generator-to-wheel flow; storage supplies the difference, not all traction energy.

- **D1:** Screen a **16s1p ANR26650M1B LFP** pack first for electrical compatibility, alongside **13s1p P28A**: 1.216 kg versus 0.598 kg **cells only**. LFP's documented 26 A continuous charge ceiling is materially different from P28A's 8.4 A; neither is a finished BMS-equipped pack. This is not final chemistry selection.
- **D2:** Do not select supercap-only by headline joules. A practical 20s Eaton XV300 string is 1.240 kg cells, **3.906 Wh between 50 and25 V**, before ESR/converter loss. It cannot supply even a 250 W residual bus deficit for60 s (4.167 Wh). A direct 50–36 V window offers just2.508 Wh before loaded-voltage guard.
- **D3:** A 10 s launch to25 km/h at assumed150 kg needs only **0.695 Wh net bus energy** with250 W crank input, but reaches **778 W storage deficit** at the end of a linear speed ramp. This assumed launch is **not an operator requirement** and exceeds the existing500 W screening ceiling. Screen a slower/nonlinear launch instead; no power uprating or launch target is approved.
- **D4:** Defer hybrid unless repeated braking demonstrably exceeds battery charge acceptance or cold operation is mandatory. Adding20 XV cells already costs1.240 kg before converter, mount and balance hardware; no demonstrated battery-life saving offsets this today.
- **D5:** No buffer is a legitimate bench baseline (with controlled power supply/dump path), but not an equivalent ride architecture: cannot deliver surplus launch torque from rest, cannot store stop energy, and must curtail generator/regen during mismatch.

These are analysis recommendations for parent/independent review, not delegated authority to release hardware. No independent cross-family consultant verdict was obtained in this bounded step.

## 1. Boundary conditions and reproducible load cases

**User facts:** human-powered first; independent cadence;80% crank-to-wheel target accepted;120 kg is confirmed rider+luggage, **not total mass**. Braking is rider-requested only; storage charging must not initiate unsolicited wheel braking. No powered-range requirement. Total140/150 kg below are assumptions corresponding to20/30 kg bike+equipment; actual build mass is unknown.

**ASSUMPTIONS, not measured:** level road, linear speed ramp over10 s,250 W crank throughout, generator/gear-to-bus efficiency0.90, bus-to-wheel8/9 (product0.80),5 W auxiliary, Crr0.006, CdA0.5 m², air density1.225 kg/m³. These cruise-like efficiencies may be optimistic at launch. Model does not include rotating inertia, wind, grade, traction/torque limits, or thermal map. Add those before sizing. `launch()` accepts grade/rider/efficiency overrides.

`KE=½mv²`; distance=`vt/2`; road work=`mg(Crr+grade)vt/2 + ½rho CdA v³t/4`.
Net buffer energy=`max(0,(KE+road)/eta_drive + Paux*t − Pcrank*eta_gen*t)/3600`.
Instantaneous ramp-end deficit=`(mv²/t+mg(Crr+grade)v+½rho CdA v³)/eta_drive+Paux−Pcrank*eta_gen`.
The reported net integral is **not minimum required capacity**: early-ramp surplus and late-ramp deficit require SOC headroom and chronological integration in the final controller model. The reviewed model now computes cumulative excursion: at150 kg/25 km/h, ideal usable swing is0.7709 Wh, with0.6951 Wh initial energy and0.0758 Wh initial charge headroom if all early generator surplus is accepted. These exclude storage losses and reserve; no claim that0.695 Wh alone suffices. `buffer_wh` remains the nonnegative net integral for compatibility, **not capacity**; `net_bus_wh` preserves its sign. `excursion_wh=max Q−min Q`, where `Q(t)=∫Pdeficit dt/3600`; initial energy must be ≥max Q and headroom ≥−min Q. Curtailing early generator surplus changes this trajectory.

| Total kg | Stop/launch km/h | KE Wh | Road Wh | Net buffer Wh | End deficit W | Recoverable stop Wh at eta_regen=0.50 |
|---:|---:|---:|---:|---:|---:|---:|
|140|20|0.6001|0.1001|0.1766|376.69|0.3001|
|140|25|0.9377|0.1507|0.6134|719.31|0.4689|
|150|20|0.6430|0.1046|0.2299|415.09|0.3215|
|150|25|1.0047|0.1564|0.6951|778.16|0.5023|

Regen is independent: `Estored=KE*eta_regen`, not80% nor the reverse of the forward efficiency. The assumed50% includes wheel-to-storage losses; it is an optimistic energy ceiling when charge acceptance/headroom limit, and excludes road losses and rider input during braking. At150 kg/25 km/h, eta0.3/0.7 gives0.3014/0.7033 Wh. Full or cold-disabled battery can accept **zero**. Stop duration sets peak current independently of energy.

| Residual bus deficit AFTER rider generation |60 s bus Wh|Store Wh at assumed95% DC/DC, excluding ESR|
|---:|---:|---:|
|100 W|1.6667|1.7544|
|250 W|4.1667|4.3860|
|500 W|8.3333|8.7719|

These are scenarios, not requested motor-only range. Repeated deficits require subsequent pedal surplus or braking energy; storage cannot make average wheel power exceed human input after losses.

## 2. Primary-source cell shortlist (catalogued, not stock-confirmed)

Sources checked2026-11-10. **No live inventory or unit price was verified; all costs remain quote-required.** Source existence is not availability for immediate delivery. BOM records blank cost fields, not zero-cost assumptions. No assembled pack mass is verified.

|Candidate / source|CITED cell specifications|Constraints|
|---|---|---|
|[Eaton XV3550-2R7307-R, TD4424](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-xv%20supercapacitor-cylindrical-snap-in-data-sheet.pdf), [manufacturer SKU](https://www.eaton.com/us/en-us/skuPage.XV3550-2R7307-R.html)|300 F,2.7 V,4.5 mΩ max initial DC ESR,62 g typical;20 A continuous at15°C rise;160 A **1 s**,600 µA max leakage after72 h/+20°C; −40…65°C|Use2.5 V/cell study ceiling for margin, not validated balance safety. −5% capacitance tolerance. Do not use1 s pulse rating as10 s rating.|
|[Eaton XL60-2R7308T-R, TD10339](https://www.eaton.com/content/dam/eaton/products/electronic-components/resources/data-sheet/eaton-xl60-supercapacitors-cylindrical-cells-data-sheet.pdf), [SKU](https://www.eaton.com/us/en-us/skuPage.XL60-2R7308T-R.html)|3000 F,2.7 V,0.23 mΩ,515 g threaded cell;143 A continuous at15°C rise;5 mA nominal leakage; −40…65°C|20s cells alone10.300 kg. Low ESR but excessive mass for this buffer case.|
|[Molicel INR18650P28A V2](https://www.molicel.com/wp-content/uploads/INR18650P28A-V2-80093.pdf)|2.8 Ah typical;3.6 V nominal;4.2 V charge/2.5 V discharge;46 g typical;35 A max discharge;2.8 A standard/8.4 A max charge;20 mΩ DC at10 A/1 s|Charge0…60°C, discharge−40…60°C does **not** permit cold regen.13s reaches54.6 V;2.5 V lower limit would be32.5 V, below36 V bus.|
|[Lithium Werks ANR26650M1B SF00008 rev3 Aug2025](https://lithiumwerksbatteries.com/content/26650%20Power%20Cell%20080625.pdf), part300832-001|2.6 Ah typical/2.5 min;3.3 V nominal;76±1.5 g;52 A continuous discharge/120 A10 s;3 A recommended/26 A max continuous charge/40 A10 s;3.6 V recommended charge|16s full57.6 V, **not generic58.4 V LFP charge**.2 V minimum cell would imply32 V: enforce36 V bus guard sooner. <10 mΩ **AC1 kHz is not DC ESR**. Charge0…60°C; special <250 mA below0°C is not permission for normal regen.|
|[Toshiba SCiB2.9 Ah high-power cell](https://global.toshiba/ww/products-solutions/battery/scib/product-next/product/cell/high-power.html)|2.4 V nominal,2.9 Ah,~150 g;520 W output/410 W input **calculated from resistance**,50%SOC,10 s,25°C|20s nominal48 V/3 kg cells. No numerical continuous current, full voltage limits, or cell-specific cold charge envelope established here. Do not convert headline watts into qualified current. Obtain application datasheet/quote first.|

Evidence retrieval: direct `urllib` downloads + `pdftotext` succeeded for P28A and LFP; web extraction rejected URLs and direct Eaton PDF timed out. Eaton tables above use search-indexed primary datasheet/SKU text; Toshiba likewise primary indexed page. Treat them as lower-confidence procurement evidence pending saved supplier revisions. Toshiba legacy page lists different2.9 Ah input/output powers; this paper uses the linked current global page, not a merged maximum. Lithium Werks older rev2 has lower charge limits; procure/review exact revision, default conservatively until confirmed.

Do not claim generic cycle superiority as a quantified saving: Eaton XL's million-cycle test is max-to-half voltage,100 A,+25°C with rest; LFP's >4000 cycles is1C/1C100%DOD; Toshiba40,000-cycle statement is10C/35°C; P28A curves have their own rest/current conditions. These are incompatible duty cycles, **not predicted bicycle lifetime**. No cycle count enters the ranking calculation.

## 3. Voltage-window energy, ESR and heat

`Cstring=Ccell/N`; `Rstring=N*Rcell`; `Eusable=½Cstring(Vhi²−Vlo²)`.
For constant terminal loadP, `I=2P/(V+sqrt(V²−4RP))`, `Vterminal=V−IR`, loss=`I²R`. On charge, replace minus inside sqrt with plus and `Vterminal=V+IR`. Current limits are different by direction; charge additionally limited by highest cell voltage/SOC/temperature.

|String / path|C F|R Ω|Open-circuit window|Ideal usable Wh|Cell kg|500 W bus discharge at low V: A / cell-string heat W|
|---|---:|---:|---|---:|---:|---|
|20s XV /95% converter|15|0.090|50–25 V|3.9062|1.240|22.9485 /47.3971|
|20s XV /direct|15|0.090|50–36 V|2.5083|1.240|14.4079 /18.6828|
|22s XV /direct|13.6364|0.099|55–36 V|3.2746|1.364|14.4642 /20.7122|
|20s XL /95% converter|150|0.0046|50–25 V|39.0625|10.300|21.1348 /2.0547|

**Ideal energies are upper bounds**, not bus-deliverable ratings. Direct XV at36 V open circuit falls to34.70/34.57 V loaded, outside provisional36 V minimum. Stop earlier (at500 W,20s needs ≥37.25 V open circuit just to deliver36 V), or use DC/DC. Converted20s XV at500 W exceeds20 A continuous rating at low voltage; thermal/pulse qualification needed or raise lower cutoff/reduce power. Its converter must operate down to22.93 V terminal, not just25 V. Doubling ESR at age/cold increases heat and cutoff margin; minimum capacitance and aging reduce energy too. Apply end-of-life and cold curves, not just nominal values.

At500 W bus **charging**,95% converter yields475 W cap terminal input:20s XV at25 V takes17.8526 A, dissipates28.6845 W, terminal rises26.6067 V. Charge headroom must be assessed at the high-voltage end too; never terminate based only on sum voltage. Heat figures are instantaneous, not ten-second mean or temperatures; integrate `I(t)²R` with thermal impedance before qualification. XV per-cell thermal resistance9°C/W from SKU is a steady-state open-air indicator, not a sealed-pack thermal model.

P28A13s uses measured-condition DC R≈0.26 Ω: at46.8 V open circuit/500 W terminal,11.4066 A,33.8287 W loss,43.8343 V loaded. This is a screening extrapolation from1 s resistance, not guaranteed continuous heat. Charge limit8.4 A allows only302.4 W at36 V or458.64 W at54.6 V **before CV taper**.500 W at36 V demands13.89 A, so reject500 W regen into13s1p P28A.13s2p doubles mass to1.196 kg and current ceiling16.8 A, halves cell-string R; then BMS/temperature/headroom may still dominate.

LFP's52 A discharge/26 A continuous charge nameplate is above13.89 A at36 V, but low-temperature, full-SOC taper and BMS can negate this. **No DC sag calculation from its AC impedance.** For an explicitly assumed pack DC resistance0.16/0.32 Ω, at10 A the loss is16/32 W and sag1.6/3.2 V; measure DC pulse resistance versus SOC/temperature to replace these sensitivity points. SCiB has insufficient primary detail here for a safe DC-loss/current calculation; do not invent ESR from nominal power.

## 4. Batteries, converters, hybrid and overhead

Battery energy is **not** capacitor energy: integrateV(SOC,I,T)dQ. Screening nominal `N*Vnom*Ah`, with an **assumed20–80%SOC60% window**, gives:

|Pack concept|Nominal V·Ah Wh|Assumed window Wh (not guaranteed)|Cells kg|
|---|---:|---:|---:|
|13s1p P28A|131.040|78.624|0.598|
|16s1p ANR26650M1B|137.280|82.368|1.216|
|20s1p SCiB2.9|139.200|83.520|3.000|

P28A datasheet's typical10.3 Wh/cell differs from3.6*2.8=10.08 Wh; table intentionally uses nominalV·Ah, not integrated datasheet energy. None of these windows is proven inside36–58.4 V under load. All greatly exceed the8.33 Wh60 s scenario on paper; **minimum series count and charge current, not powered range, drive pack size**.

Direct compatible battery avoids an additional conversion stage. Low-voltage supercap requires bidirectional buck-boost unless the motor/generator bus actually supports its full loaded voltage swing. Two machine bridges are not a third storage converter. A direct55–36 V cap string is possible in principle, but bus variability, cold/startup, reduced energy and per-cell overvoltage protection must be accepted explicitly.

Converter costing cannot be silently zero: custom500 W bidirectional stage needs switches/drivers, inductor, current sensing, protection, cooling, enclosure and integration. **No selected converter and no verified converter price/mass.** Sensitivity only, not supplier estimates: adding0.25/0.50/1.00 kg converter+mount makes20s XV2-path subsystem≥1.49/1.74/2.24 kg before balance/protection; adding assumed EUR50/100/200 is a quote sensitivity, not a BOM price. At assumed95% one-way efficiency500 W bus delivery loses26.32 W in converter alone;90–98% sensitivity gives55.56–10.20 W.95% each way is90.25% roundtrip **before cap ESR**. Do not route all pedal power through charge/discharge to get independent cadence: direct power flow avoids that penalty. At250 W crank the80% target allows50 W total system loss, so this overhead matters.

Hybrid example:13s1p P28A +20s XV converter bank =1.838 kg cells alone, versus1.196 kg for13s2p P28A or1.216 kg LFP cells. Hybrid can clamp battery charge peaks and support brief cold regen, but adds another control loop, contactors/fuses and failure modes. It cannot fix60 s energy deficit or long descent once caps fill. Its incremental benefit must beat simply limiting electrical regen and retaining mechanical braking.

Standby/balance:20s XV leakage proxy at50 V is0.030 W (0.72 Wh/day),20s XL0.250 W (6 Wh/day); these are full-voltage proxies from specified leakage, not constant-current lifetime predictions. Passive balance sized to dominate mismatch can exceed leakage. For illustration only,1 kΩ across each2.5 V cell costs0.125 W/string (3 Wh/day); active balance costs unknown quiescent power and parts. Battery BMS and converter quiescent draw are unverified: even assumed0.1 W costs2.4 Wh/day. Sleep/isolation and restart sequencing matter more than a nominally huge cycle rating. No actual assembled mass/cost total is asserted: BMS, fuse, precharge, connectors, busbars, insulation, enclosure, mount and cooling remain additional line items in the CSV.

## 5. Ranking reversal thresholds and interface handoff

1. **Short pulses only:**20s XV converted bank's optimistic60 s crossover is222.66 W average residual deficit; ESR, reserve and cold/aging lower it. Above that, this bank fails on energy regardless of peak-current rating. Below it, cap-only remains possible if mass, standby and converter losses are acceptable. At the provisional36 V motor-bus minimum direct caps lose additional energy; a genuinely wide-voltage motor bus could improve cap ranking.
2. **Regen charge demand:** warm13s1p P28A is plausible if charging is limited below8.4 A with taper; above that choose more parallel cells, charge-limiting with mechanical braking, qualified LFP/LTO, or hybrid. Do not equate35 A discharge with35 A charge. LFP's charge advantage is conditional on exact cell revision/BMS.
3. **Mandatory subzero charge:** present LFP/P28A baseline inhibits normal cold charging, including regen and generator surplus. Qualified SCiB cold-charge envelope could change the ranking despite3 kg cells; Toshiba's generic/10 Ah cold claim alone does not qualify the2.9 Ah pack. Caps could accept brief cold pulses only after their ESR/current derating is verified.
4. **Mass priority with modest regen:** P28A1p wins bare-cell mass. High repeated accepted braking current may favor LFP or2p P28A before hybrid. No price-based winner is defensible without quotes. Very frequent cycling is not yet a proven lifecycle-cost case for caps.

**Message for electrical-interface owner:** provisionally support a fused/precharged direct **36–57.6 V16s LFP evaluation interface**, with13s Li-ion compatibility only through pack-specific configuration (54.6 V max). Keep58.4 V as provisional bus envelope, not charger setpoint. Do not change circuitry from this study alone. Storage interface must expose independently enforced charge/discharge current permission, cell high/low warning, pack temperature, presence and fault/contactor state; loss of communications defaults to no charge/torque. Reserve external bidirectional DC/DC boundary if later selected; do not author it now.

A BMS disconnect is not energy disposal. Generator surplus, regenerative wheel power and PM back-EMF can continue after BMS opens. Curtail generator torque/regen, use independently qualified dump path, preserve mechanical brakes, and test disconnect/full/cold/absent storage. Bus undervoltage can occur before cell minimum; graceful torque limiting precedes BMS hard cut. Boot/precharge must work from chosen storage window; cap empty state cannot power immediate wheel torque.

## 6. Risk ordering and next evidence (no orders)

Likelihood is unmeasured; qualitative priority, not fabricated probability:

|Priority / severity|Failure|Required mitigation or remaining evidence|
|---|---|---|
|1 critical|Pack short/fire or reverse connection|Battery-rated fuse, insulation, keyed connector, DC disconnect, thermal sensing; professional pack design; none qualified here|
|2 critical|BMS opens during regen; bus overvoltage|Independent energy disposal/control and fault injection; mechanical brakes; no accepted uncontrolled case|
|3 high|Cold/full cell charged beyond permission|Per-cell voltage and temperature limits; reject normal charge below0°C for provisional LFP/P28A; independent charge/discharge permissions|
|4 high|Cap imbalance hides overvoltage|Cell monitors/balance validation, not sum voltage alone; fail-safe charge inhibition|
|5 high|Undervoltage/thermal torque loss at launch|Loaded-voltage guard and measured maps; slower launch; safe coast/stop; no mechanical chain fallback|
|6 medium|Overnight depletion / extra mass|Sleep-isolation validation and weighed assembled pack; standby trade remains open|

Open before purchase: authenticated supply/stock and exact datasheet revision; prices including tax/shipping; actual bike mass; braking duration/frequency and cold-use requirement; cell DC pulse/thermal maps and reserve SOC; BMS thresholds/standby/charge current; pack mechanical design and weighed mass; converter selection/mass/efficiency/price if needed; chronological transient model including inertia/grade and measured machine efficiency. Validate recovery after rejected regen without pedal back-drive. No road legality or battery certification conclusion here.

## 7. Verification record

See [independent arithmetic/source-boundary review](storage-review.md) for cumulative-excursion corrections, high-voltage charging corner, confirmed user boundaries and the expanded12-test result.

Original implementation record: eight test methods initially **FAILED** because model was absent, then all eight passed after implementation. Tests cover series energy, current/heat, separate charge equation, infeasible constant power, rider subtraction, independent regen efficiency, nonnegative deficit and invalid voltage window. Real model ran exit0 and produced tables above. These are arithmetic tests, not bench validation; no battery, capacitor string, converter, BMS or PCB was exercised.
