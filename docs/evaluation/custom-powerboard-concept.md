> **STATUS: FIRST-STAGE ENGINEERING EVALUATION — NOT FAB-READY, NOT A PURCHASE LIST.**
# Custom pedal-by-wire powerboard concept

2026-11-10 · branch `pr/custom-powerboard-concept` · base `1da4bc8` · worktree `/home/c08r4d0r/worktrees/cycle-powerboard`.
Scope: architecture, provisional sizing and source screening. No schematic, PCB, prototype, thermal test, motor map measurement or bicycle inspection performed. Read the existing [plan](../PLAN-parallel-hybrid.md) and its historical-claim corrections first.

## 0. Recommendation and decision log

- D1: proceed with **two custom three-phase silicon-MOSFET bridges**, one generator active rectifier, one hub inverter, sharing a protected DC link. Supervisory MCU and storage interface are custom too; do not substitute a commercial complete controller.
- D2: screen **36–58.4 V operating bus**, 100 V MOSFETs; this is not a 100 V operating design. Initial supported battery chemistry should be one explicitly selected pack, not arbitrary “48 V”.
- D3: generator selection is the hardest constraint: maxon 500267 is documented, but its **0.964 Nm continuous rating** and **41.3 rpm/V** imply substantial gear-up and leave a 250 W continuous rider case unqualified. Do not choose from headline watts alone.
- D4: 80% crank-to-wheel at cruise is a **target, never achieved evidence**. At 250 W crank it permits only 50 W aggregate loss, including gears, both machines, converters and auxiliaries. A vendor maximum motor efficiency is not a generator map.
- D5: authorize only a reviewable, low-energy prototype schematic specification next. Unknown frame dimensions block mechanical fit/fabrication, not source research. No orders or frame modifications authorized.

## 1. Assumptions and numeric provisional envelope

All entries below are **design assumptions**, not rider requirements or measured ratings. Script `envelope_model.py` reproduces the arithmetic.

| Item | Screening assumption and limit |
|---|---|
| Bicycle | Old Villiger road bicycle; clamp-mounted generator; crank-to-generator Zahnrad gear drive; no crank-to-wheel chain. Preserve both independent mechanical brakes. |
| Inputs still unknown | Rider+cargo+bike mass, wheel circumference, gradient/duration, country, budget, frame/fork material and condition, dropout spacing, gearing clearance. No road legality conclusion. |
| Pedalling | 60–100 rpm, 250 W design study point; 500 W short transient study only, duration/torque not qualified. At 250 W and 80 rpm crank torque is 29.84 Nm. |
| DC bus | 36–58.4 V normal screening range: 13s Li-ion at assumed 4.2 V/cell = 54.6 V; 16s LFP at assumed 3.65 V/cell = 58.4 V. Pack-specific charger/BMS limits override. |
| DC input/output | 500 W electrical screening ceiling implies 13.89 A at 36 V. Provisional 15 A continuous bus design target, 20 A transient review ceiling, **not proven PCB rating**. |
| Generator phase | Hardware measurement range ±30 A peak; initial software cap 5 A peak until current convention, generator map and thermal limits are established. This does not grant 5 A continuous operation to 500267. |
| Hub phase | Design study 15 A RMS continuous, 30 A peak short transient. 30 A is a measurement/control ceiling, not a qualified motor torque or duration. Low-speed phase current can be much larger than bus current. |
| Switching | Start loss model at 20 kHz; validate acoustic/EMI/current sampling and motor inductance before freezing. |
| Overvoltage | Provisional chopper onset 60 V, independent bridge inhibit 65 V. Account for tolerances, latency and overshoot; keep driver VM below its **75 V recommended maximum**, phase-sense common mode below 80 V, MOSFET VDS below 100 V with margin. No claim thresholds alone enforce those limits. |

DC-link capacitors provisionally 100 V class, ripple-current and lifetime sized from switching/load model. A 63 V capacitor is not accepted merely because full charge is 58.4 V. TVS selection must use **clamping voltage at actual surge current**, not standoff voltage; TVS cannot absorb sustained downhill regen. Cable inductance, MOSFET ringing, reverse polarity and BMS opening under regen must enter the transient model.

## 2. Machine shortlist: evidence versus missing maps

Sources checked 2026-11-10; search-index excerpts are identified where direct extraction failed. Listing existence is not confirmed inventory. No efficiency map was obtained in this bounded stage.

| Candidate | Source-backed facts | Availability / torque-speed / mounting verdict |
|---|---|---|
| maxon EC90 flat **500267**, PM BLDC used as generator candidate | [Manufacturer shop](https://www.maxongroup.it/maxon/view/product/motor/ecmotor/ecflat/ecflat90/500267), search-index manufacturer excerpt: 48 V; 1960 rpm no-load; 1670 rpm nominal; 0.964 Nm nominal continuous; 4.06 A nominal; 41.3 rpm/V; Kt 0.231 Nm/A; terminal R 0.844 ohm; L 1.07 mH; max speed 5000 rpm; 985 g; radial load 130 N at 10 mm from flange. | Shop excerpt shows add-to-cart and EUR276.73 qty1–4 excluding VAT/shipping; **live stock/quote not verified**. Direct .com extraction blocked. Nominal-point data, not generating map. Motor rating label 260 W does not make 250 W generation continuous at arbitrary speed. Drawing/bearing side-load and supplier generator approval required. |
| maxon EC90 flat **500268**, alternative winding | [Manufacturer catalog search](https://www.maxongroup.com/maxon/view/content/service_search?query=EC+90+flat): 60 V nominal, 33.4 rpm/V, 1980 rpm no-load, 0.963 Nm nominal continuous. | Catalog listed; price/stock and full datasheet not obtained. Lower Kv reduces gear-up; no evidence it fixes efficiency or continuous power. Direct extraction blocked. Keep alternative, not selected. |
| Grin All-Axle original front, winding/adapter SKU **not yet selected** | [Manufacturer](https://ebikes.ca/product-info/grin-products/all-axle-hub-motor.html): direct-drive, 4 kg original, integrated torque arm, front 100 mm QR and other adapters; rear models include 135 mm QR. | Manufacturer offers current family, stock not verified. [Manufacturer simulator](https://ebikes.ca/tools/simulator.html?motor=MGRIN2706&cont=C35) provides modeled torque-speed/efficiency exploration; no exported map or selected winding yet. Most promising compatibility research candidate, **not proof of fit**. Rim-brake rim, spoke count, wheel dish and torque-arm attachment must match bicycle. |
| Nine Continent **M-M2706RD** rear alternative | [Vendor technical page](https://ebikes.ca/m2706rd.html): 10.7 rpm/V, 0.145 ohm reported phase resistance, 0.6 mH inductance, 23 pole pairs, 6.16 kg, 135 mm OLD, 36 holes. | Clearance “remaining hubs” listing; inventory/price not verified. Disc configuration may require 138 mm OLD. Reject if frame requires spreading/cold-setting, machining or brake compromise. Vendor parameters allow model input, not a measured torque-speed map. |

Generator gear-up example: at 80 rpm and ratio 25:1, generator is 2000 rpm, ideal reflected torque for 250 W is 1.194 Nm, already above 500267's quoted 0.964 Nm continuous nominal torque. At 500 W it is 2.387 Nm. Approximate no-load EMF n/Kv = 48.43 V (500267) or 59.88 V (500268); actual rectified voltage requires waveform/line-line/RMS convention measurement. 500268 can threaten the bus at higher cadence. Ratio is **not selected**. A single spur stage with 25:1 is mechanically awkward; assess compound gearing, efficiency, bearing supports and enclosure. Generator shaft must not carry unqualified pinion loads.

Higher-Kv skateboard motors need much higher speed or boost and are not automatically efficient at rider power. A Flipsky 6354 source fetch failed; no unverified candidate rating was promoted to the BOM. No automotive claw-pole assumption is applied to the PM candidates.

For hub sizing use `T = force * radius`, `force = m*g*grade + Crr*m*g + 0.5*rho*CdA*v² + m*a`, with actual wheel radius and duty cycle. `Kt ≈ 9.55/Kv` only after matching electrical conventions; phase peak/RMS and controller-defined current differ. At 10.7 rpm/V and 48 V, 513.6 rpm is an unloaded estimate, not road speed under load. Do not infer torque capability from 500 W / bus voltage.

**Required maps:** generator torque/speed vs DC output, copper/iron/gear loss and winding temperature at cadence band; hub torque/speed vs DC input at actual wheel and hills, plus low-speed thermal saturation. Use manufacturer simulator as a hypothesis, then instrument shaft torque/speed, DC voltage/current and wheel torque/speed. Record ambient and steady-state duration. Neither datasheet nominal points nor maximum efficiency replace maps.

## 3. Electrical architecture and parts

See [block diagram](custom-powerboard-block.svg) and [candidate BOM](custom-powerboard-bom.csv). Quantities are architecture counts, not complete procurement totals.

Two DRV8353SRTAT drivers and twelve CSD19532Q5B 100 V MOSFETs are the baseline candidate bridge implementation. **Important datasheet distinction:** DRV835x VM supply recommended 9–75 V; VDrain sense supports 100 V. The “100 V driver” headline is not a 100 V VM operating permission. Driver has hardware gate protection/OCP, but does not constitute a complete safe shutdown system.

Use three low-side 2 mOhm shunts per bridge and the driver's integrated amplifiers initially; add one INA240A1PWR for a bidirectional DC-bus shunt. Optional inline phase amplifiers are alternatives, not seven extra mandatory ICs. 2 mOhm at 15 A RMS dissipates 0.45 W; at 30 A 1.8 W. Gain20 yields ±1.2 V at ±30 A, centred at 1.65 V on 3.3 V ADC: nominal 0.45–2.85 V. Check amplifier output swing, offsets, settling, blanking and worst-case tolerances; Kelvin route a two-terminal shunt carefully or select a true four-terminal substitute. Three low-side channels still require valid PWM sampling windows.

STM32G474RET6 is a candidate 170 MHz MCU. Prove LQFP64 pin assignment for two synchronized advanced-timer PWM sets (12 gate commands), six phase ADC samples, bus/temperature sensing, Hall/encoder inputs, SPI drivers and hardware break before committing package. Pin mux, ADC triggering and CPU budget for two FOC loops are open evidence items, not established by family features. A larger package or two control MCUs is a fallback if timing/pin feasibility fails.

**Loss model before GaN:** `Pcond≈3*Irms²*Rds_hot` per bridge, plus measured switching energy times frequency, diode/deadtime losses, gate power `N*Qg*Vgate*f`, shunts and auxiliary power. CSD19532Q5B max Rds at 10 V is 4.9 mOhm at specified room-temperature conditions; assumed hot multiplier2 gives 6.615 W conduction per bridge at 15 A RMS. This is a sensitivity assumption, not measured dissipation. Twelve 48 nC gates at 10 V/20 kHz imply 0.1152 W ideal gate charging. Missing switching/thermal model means no total efficiency prediction. GaN is deferred unless measured/modelled switching savings outweigh driver complexity, EMI, fault tolerance and cost; it cannot repair machine/gear losses.

## 4. Storage, full-battery regen and startup

Direct fused pack connection is the simplest baseline **only** if its voltage range, bidirectional charge current, BMS disconnect behavior and bus regulation are compatible. It does not need a DC/DC merely to exist. A supercap's wide voltage swing, incompatible pack voltage, or independently regulated bus requires **bidirectional buck-boost DC/DC**. Reserve connector/control channels; do not claim the two bridges provide a separate storage converter. A four-switch stage adds four MOSFETs, two half-bridge drivers, inductor, shunts and independent protection; topology/inductor/controller selection remains open until storage range and power are frozen. It is explicitly not included in the twelve-MOSFET count.

Regen acceptance must be bounded by BMS current, temperature and state of charge. Full/absent storage or an opening BMS causes bus rise: hardware comparator-controlled brake chopper and pulse/continuous-rated resistor must absorb the agreed transient independently of MCU. At hypothetical 60 V and 500 W, R=7.2 ohm, I=8.33 A; a 10 s event is 5000 J. These are **sizing examples**, not resistor specifications. Long descents can exceed this; inhibit electrical regen and retain mechanical brakes. Gate-disable does not stop PM back-EMF charging through body diodes; analyze maximum downhill speed, uncontrolled rectification, generator overspeed, chopper failure and safe isolation sequencing. Do not open a contactor blindly while energy flows.

Baseline boot: fused storage → protected 100 V-input auxiliary buck (LM5164 candidate) → gate/logic rails; 12 V then 3.3 V regulator is one option, power budget pending. Hardware holds bridge gates off until rails, sensors and limits validate. LM5164 starts at 6 V input; motor driver needs at least 9 V VM. Optional batteryless boot uses PM-generated EMF and passive rectification into a small auxiliary reservoir, UVLO/hysteresis and controlled precharge before enabling active boost rectification. Cold-start cadence, available power, reservoir energy and brownout behavior must be measured. Zero-speed batteryless launch cannot provide motor torque; pedalling must charge energy first. Active rectification can boost through machine inductance, but cannot assume stable operation with insufficient EMF/inductance/control supply.

## 5. Safety and reversible mechanics

| Ranked risk (qualitative; occurrence unmeasured) | Required mitigation/evidence |
|---|---|
| Critical: frame/fork fracture or wheel axle rotation | Inspect material, corrosion, tube wall and dropout geometry; load-path analysis, properly distributed removable mounts and qualified torque arms. **No universal clamp torque.** Thin tubes can crush/fatigue even if a clamp does not slip. No drilling, welding, cold-setting or filing. |
| Critical: electrical runaway / unexpected pedal back-drive | Independent brake switches and hardwired enable chain; fault latch, external watchdog, overcurrent/OV comparator, gate pulldowns; safe direction/torque checks. Consider mechanical freewheel/torque limiter with its effect on reverse operation. Independent mechanical brakes remain operable without electricity. |
| Critical: pack fire / short circuit | Battery-rated fuse at source, reverse-polarity blocking, precharge, disconnect with DC interrupt rating, current/temperature limits, insulation/strain relief and enclosure. MCU shutdown cannot clear a failed-short MOSFET. |
| High: regen overvoltage / chopper overheating | Hardware OV chopper, thermal cutout, power-rated resistor away from rider, full-pack test and energy-path FMEA. Protection components still unsized: no fabrication release. |
| High: gear nip / clothing / bearing overload | Full gear guard, crank/foot clearance, supported shafts, tooth-force and bearing-load calculation, emergency release and clamp fatigue verification. |
| High: loss of propulsion | With no mechanical wheel drive, electronics failure means no pedal propulsion. Safe coast/stop and recovery plan; do not call this chain-equivalent reliability. |

Protection independent of software includes current comparator/latch to driver ENABLE and MCU timer BREAK, driver OCP, hardware OV chopper, external watchdog and brake interlock. Separate fault domains where practical; test stuck-high PWM, sensor disconnect, MCU freeze, driver fault and loss of auxiliary power. Comparator/latch/watchdog/fuse/contactor/TVS exact parts are **unselected**, not silently omitted from a supposedly complete BOM.

## 6. Evidence gates and immediate next scoped schematic stage

**Before schematic freeze:** agree provisional pack chemistry/range, generator winding and speed limit; audit exact driver pin absolute/recommended limits; prove timer/ADC/pin allocation; select and tolerance-calculate independent protection; complete preliminary bridge/auxiliary/DC-link/chopper loss and transient model. Mechanical photos can arrive later; they are a fit/fabrication gate, not a research gate.

**Next reviewable KiCad stage (not fabrication):** sheets for (1) fused/precharged DC link and testpoints, (2) generator bridge, (3) hub bridge, (4) current sensing and comparator fault latch, (5) independent OV/chopper, (6) auxiliary rails/UVLO, (7) STM32+SWD+Hall/encoder/brake interfaces, (8) storage connector with explicit optional DC/DC boundary. Annotate every unselected safety part DNP/TBD and exclude it from release. Produce ERC, pin-budget table, fault-state truth table, test connector plan and review BOM; no copper layout release until schematic review closes the protection and thermal unknowns.

**Before PCB layout:** selected package footprints from primary drawings, commutation-loop and Kelvin constraints, thermal/heatsink model, creepage/clearance/environment assumptions, connector/fuse interrupt ratings, resistor energy rating, independent protection behavior and bench hazard review. **Before fabrication:** no safety-critical TBDs, independent schematic/layout review, mounting geometry/load analysis and explicit authorization. **Before riding:** current-limited bench bring-up, dyno maps, transient captures, fault injection, guards/brakes and jurisdiction review.

## 7. Primary evidence register and limits

- TI [DRV835x datasheet Rev A](https://www.ti.com/lit/gpn/DRV8353), features and recommended operating conditions; fetched PDF text. VM75 V versus VDrain100 V distinction retained.
- TI [CSD19532Q5B datasheet Rev B](https://www.ti.com/lit/gpn/CSD19532Q5B), ratings/thermal conditions; fetched PDF. 100 A package headline does not establish PCB current rating.
- TI [INA240 datasheet Rev C](https://www.ti.com/lit/gpn/INA240), −4 to80 V common mode and gain variants; fetched PDF.
- ST [STM32G474 datasheet DS12288](https://www.st.com/resource/en/datasheet/stm32g474re.pdf), timers/ADCs/package; fetched excerpt, exact mux review outstanding.
- TI [LM5164](https://www.ti.com/product/LM5164): primary product description 6–100 V,1 A; detailed auxiliary design outstanding.
- Machine sources are in §2. maxon shop/catalog evidence is search-indexed manufacturer text, weaker than a live stock quote. No complete generator operating map acquired. No exact hub winding selected.

**Explicit correction of old claims:** this document does not validate prior series/parallel diagrams, guessed efficiency ceilings, historical prices, Mando/Schaeffler topology claims or the claimed GaN 65%→86% jump. Parallel drive would violate the chosen no-chain crank-to-wheel architecture. 80% remains an acceptance target at a defined operating point with storage energy balanced, not a vendor-derived result. No electrical or mechanical fit is proven. No purchase/fabrication action occurred.
