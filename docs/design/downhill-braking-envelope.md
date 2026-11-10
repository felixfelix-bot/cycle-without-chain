> **STATUS: CONSULTANT ANALYSIS — NOT A DESCENT RATING OR HARDWARE RELEASE.**
> Supplemental electrical braking is requested by the rider's brake lever/cable only, thermally limited. No automatic downhill speed hold or unsolicited coasting regeneration is proposed. Autonomous emergency DC-bus clamping is a separate protection function.

# Bounded full-battery braking and heat disposal

| Provenance | Value |
|---|---|
| Date / branch | 2026-11-10 / `pr/braking-thermal` |
| Worktree / base | `~/worktrees/cycle-braking-thermal` / `30560f6` from GitHub master |
| Lens | First-order energy, load allocation, resistor and sink screening; not thermal geometry validation |
| Read first | `hardware/powerboard-reva/docs/safety-review.md`; `docs/evaluation/custom-powerboard-concept.md` |
| Reproduction | `python3 -m unittest discover -s analysis/braking -v`; `python3 analysis/braking/model.py > braking-grid.csv` |
| Scope exclusions | No schematic/PCB changes, ordering, frame machining, real motor torque validation, SPICE or physical tests |

## 0. Recommendation and decision log

**D1 — Build towards a guarded, dedicated resistor heatsink, not a heated Villiger frame.** Start with an independently powered, instrumented **100 W dump bench qualification target**, then evaluate **300 W maximum average dump for up to 600 s** on the bench, subject to temperatures and the staged protocol below. These are test targets, NOT permission to energize the unfinished powerboard and NOT qualified bicycle ratings. The 300 W limit is deliberately below the candidate bank's nominal 383 W electrical load at 60 V. There is no unlimited-mountain-brake claim.

**D2 — Two HSC3004R7J resistors in SERIES are a plausible candidate**, not two in parallel: 9.4 Ω gives 383 W / 6.38 A at 60 V, while 2.35 Ω gives 1,532 W, exceeding the pair's 600 W headline even before heat-sink qualification. Heat path, resistor pulse conditions and chopper switching/current limits remain unqualified. Do not interpret 2×300 W as a proven 600 W assembly.

**D3 — Retain mechanical brakes for all remaining and fault braking.** With 150 kg gross, 15% and 30 km/h, nominal road losses leave 1,537 W braking demand. At 300 W dump, zero battery acceptance and an illustrative 80% generator/controller efficiency, at most 375 W is electrical wheel braking: **75 W motor/controller heat + 300 W dump**, leaving **1,162 W mechanical brake heat**. This is a rider-requested cap, not a promise to hold speed. At no request, unavailable regen, overtemperature or unresolved electrical fault, credit zero electrical assistance. Mechanical brake capacity is NOT established by this calculation.

**D4 — Full pack means zero accepted charge for the limiting calculation.** Bus safety still needs an independent sink when charge acceptance disappears. Supply-loss operation is unresolved in the current design; neither a generic diode nor TVS is a sustained-energy substitute. No low-speed holding claim: wheel EMF, current/torque limits and inverter behavior must be measured. A 60 V clamp does not itself protect a 58.4 V full pack from unwanted charging; pack isolation/charge control is a separate unresolved circuit requirement.

## 1. Inputs and interpretation

All results marked COMPUTED below come from `analysis/braking/model.py`. These are explicit screening assumptions, not route or tyre specifications.

| Input | Values / basis |
|---|---|
| Rider plus luggage | **120 kg confirmed by operator**; not gross vehicle mass |
| Gross mass | ASSUMPTION 140 / 150 kg, i.e. 20 / 30 kg vehicle including all conversion hardware; must weigh |
| Grade | ASSUMPTION 5 / 10 / 15%, rise divided by horizontal distance |
| Speed | ASSUMPTION 10 / 20 / 30 km/h along road, steady only for allocating an equivalent demand |
| Vertical drop | ASSUMPTION 100 / 300 / 600 m; no route supplied |
| Rolling coefficient | ASSUMPTION .003 / .006 / .012; tyre, pressure, surface unknown |
| CdA | ASSUMPTION .4 / .6 / .8 m²; upright rider/luggage sensitivity, not measured |
| Air density | ASSUMPTION 1.0 / 1.2 / 1.3 kg/m³; not a certified altitude/weather envelope |
| Tailwind | ASSUMPTION 0 / 5 m/s; positive tailwind can add road power if faster than bicycle |
| Requested generator share | ASSUMPTION 0 / .5 / 1 of instantaneous braking demand, still capped by available sinks; not a lever calibration |
| Generator/controller efficiency | ASSUMPTION .6 / .8 / .9; lumps motor and inverter, requires actual speed/torque maps |
| Battery acceptance | Zero for full-pack envelope; model can accept a positive W limit, not SOC estimation |
| Dump limit | 300 W illustrative regulated average; duty and temperature may demand less |
| Ambient / thermal mass | ASSUMPTION 40°C; 900 J/K lumped sink capacity (approximately 1 kg aluminium at assumed 900 J/kg K), NOT a weighed part |

A 26,244-row CSV evaluates every combination above. Its brake-demand range is **133–1,764 W**; this brackets only the listed assumptions. Higher mass, steeper slopes, stronger tailwinds or continuing pedalling can exceed it. No pedal input is included: rider/generator input must be inhibited or added to DC sink demand during braking.

## 2. Mechanics, power and energy

With `s = grade / sqrt(1+grade²)`, `c = 1/sqrt(1+grade²)`, `v = km/h / 3.6`:

- `Pgravity = m g v s`; `Proll = Crr m g c v`.
- `Pair = 0.5 rho CdA (v-w)|v-w| v`, signed for a strong following wind.
- `Pbrake = max(0, Pgravity-Proll-Pair)`; if negative, propulsion is needed instead.
- `t = vertical/(v s)`, `Egravity = m g vertical`.
- `Ebrake = Pbrake t`; road dissipation is separately accounted. Acceleration is absent from this steady-speed equivalent.
- Stopping energy is `Ekinetic = 0.5 m v²`, **not** `mgh`. Add changes of kinetic energy for a descent ending at another speed; emergency deceleration peak power is not fixed by this energy alone.

COMPUTED nominal table, 150 kg, Crr=.006, CdA=.6, rho=1.2, still air. Duration is for 100 m drop; multiply by 3 or 6 for 300/600 m.

| Grade | Speed km/h | Required brake W | Seconds / 100 m |
|---|---:|---:|---:|
| 5% | 10 | 171.8 | 720.9 |
| 5% | 20 | 297.4 | 360.4 |
| 5% | 30 | 330.4 | 240.3 |
| 10% | 10 | 374.5 | 361.8 |
| 10% | 20 | 702.6 | 180.9 |
| 10% | 30 | 938.2 | 120.6 |
| 15% | 10 | 574.2 | 242.7 |
| 15% | 20 | 1,102.0 | 121.3 |
| 15% | 30 | 1,537.3 | 80.9 |

| Gross mass | 100 m mgh kJ | 300 m kJ | 600 m kJ |
|---|---:|---:|---:|
| 140 kg | 137.3 | 411.9 | 823.8 |
| 150 kg | 147.1 | 441.3 | 882.6 |

At 150 kg, stopping from 30 km/h is only **5.21 kJ**, versus **882.6 kJ** gravitational energy over 600 m (before road losses). Neither single-stop pulse capacity nor a ten-second resistor overload establishes a downhill rating. Long low-gradient descents can have smaller W yet substantially longer heating time.

## 3. Electrical/mechanical allocation

For requested fraction `f`, conversion efficiency `eta`, accepted battery power `B`, allowed dump `D`:

`Pgenerator = min(f Pbrake, (B+D)/eta)`

`Ploss = Pgenerator(1-eta)`; `Pbus = eta Pgenerator`; `Pbattery = min(B,Pbus)`; `Pdump = Pbus-Pbattery`; `Pmechanical = Pbrake-Pgenerator`.

This conserves power but **assumes** the controller reduces electrical braking when a sink saturates; the model is not evidence that circuit behavior exists. Requested torque, tyre adhesion, generator torque/current limits, speed and winding temperature must impose additional limits. At a full pack and 300 W dump, electrical wheel capacity is 333 / 375 / 500 W for eta=.9/.8/.6, with motor/controller heat 33 / 75 / 200 W. Lower efficiency is not a desirable braking strategy: it moves heat into the motor/inverter. Its unknown thermal limits can bind first.

The CSV includes 0%, 50%, 100% requested share and the resulting mechanical remainder. A brake request disappearing must remove commanded generator torque. Overvoltage clamp operation may still be required to absorb already-present electrical energy, independently of that request; do not make the protective sink conditional on the brake cable.

## 4. Resistor reality check and source-backed candidate BOM

**Primary source actually inspected:** Tyco/TE manufacturer document *Aluminium Housed Power Resistors, Type HS Series*, literature **1773035, issued 11-05**, pp.1–3, downloaded as PDF from [distributor mirror](https://xonstorage.z8.web.core.windows.net/pdf/teconnectivity_916259719_apr22_xonlink.pdf). Text extracted with `pdftotext`; page 3 rendered and inspected. This is an **old manufacturer datasheet**, not a distributor headline. The newer [Rev E, April 2024](https://mouser.com/datasheet/2/418/9/ENG_DS_1773035_E-225595.pdf) was found, but full retrieval failed (TE 403, Mouser HTTP2 failure, extractor private-address rejection). Search excerpts are not qualification of changed curves; obtain current revision and exact part confirmation before release.

- Page 1: HSC300 **300 W with heatsink at 25°C**, **75 W without heatsink**; specified standard sink **578,000 mm² area, 3 mm thick** per resistor. Do not assume one small frame tube or one shared plate equals two standard sinks; surface-area convention and boundary conditions need manufacturer confirmation.
- Page 1: thermal compound **essential** for HSC200/250/300; improved heatsinks do not justify uprating. Standard tolerance ±5%. For improved long-term stability, maximum dissipation of 70% or 50% of rating is stated for 50% or 25% of the stated resistance change respectively.
- Page 3 HSC75–HSC300 derating graph uses **HEATSINK temperature, not ambient**. HSC300's 300 W plateau visually ends around **130°C**, descending to zero at **250°C**. These approximate graph readings are NOT acceptable bike touch temperatures, nor a precise release curve. Do not apply a generic ambient-linear derating rule to this part.
- Page 3 gives pulse-energy-versus-resistance curves. No unrestricted pulse-duration/repetition approval was derived. Do not claim a 4.7 Ω pulse joule rating from a low-resolution curve or multiply it into mountain energy capacity. Confirm hot-start pulse/PWM waveform with TE.

| Candidate item | Qty / purpose | Source / qualification status |
|---|---|---|
| TE HSC3004R7J | 2, series 9.4 Ω nominal | Manufacturer family document above; exact current part drawing, terminals, availability and pulse approval pending. No order. |
| Fischer SK 56 200 SA extrusion | 1, separate guarded heat spreader/sink for trial | [Manufacturer SK56 family](https://fischerelektronik.de/web_fischer/en_GB/$catalogue/fischerData/PR/SK56_/datasheet.xhtml?branch=heatsinks) search-visible family 0.59–0.3 K/W, 300 mm wide ×40 mm high, 10 mm base. [Farnell exact part](https://uk.farnell.com/fischer-elektronik/sk-56-200-sa/heat-sink-alum-extruded-0-3k-w/dp/1211722) lists 200 mm long and 0.3 K/W. Full primary curve/orientation/temperature-rise conditions not retrieved; treat 0.3 as screening only, not measured installed performance. |
| Thermal interface compound + approved fasteners | As required by current resistor instructions | TE requires compound; thickness, torque, flatness, electrical insulation and corrosion compatibility pending. No arbitrary pad substitution. |
| Sink/base and resistor-case sensors, independent thermal interruption of test source | Instrumentation, not selected production part | Required; sensor locations and thresholds must be verified against contact hotspots. |
| Guard and reversible mount | Dedicated assembly, away from rider/tyres/cables/pack | Design requirement only. Airflow and access control must be tested with guard fitted. No irreversible frame modification authorized. |

COMPUTED electrical bank, excluding chopper losses and lead resistance:

| V | Series W nominal | Series W both −5% | Series A nominal | Parallel W nominal |
|---:|---:|---:|---:|---:|
| 36 | 137.9 | 145.1 | 3.83 | 551.5 |
| 58.4 | 362.8 | 381.9 | 6.21 | 1,451.3 |
| 60 | 383.0 | 403.1 | 6.38 | 1,531.9 |
| 65 | 449.5 | 473.1 | 6.91 | 1,797.9 |

The 36/58.4 V rows are `V²/R` arithmetic, NOT a claim the 60 V clamp is on there. At 60 V, 300 W average implies nominal duty **0.783**; resistor on-state power remains 191.5 W each (about 201.6 W each when both −5%). At 65 V the both-low total is 473 W; that voltage is a fault/inhibit region, not an allowed operating target. Evaluate mismatch, hot resistance, inductance, overshoot, pulse width, switching loss, open/short resistor faults and transistor SOA independently. A PWM average below nameplate is not proof of a safe waveform.

## 5. Dedicated sink versus frame; wind-to-stop transition

For a uniform lumped node, `T(t)=Ta+P Rth+(T0-Ta-P Rth) exp(-t/(Rth Cth))`. This is a sensitivity calculator, NOT validated geometry, contact spreading, winding-to-case impedance or human-contact safety.

COMPUTED 300 W, initially 40°C ambient, Cth=900 J/K:

| Rth K/W (ASSUMPTION) | T at 60 s | T at 300 s | T at 600 s | Steady T |
|---:|---:|---:|---:|---:|
| .1 | 54.6°C | 68.9°C | 70.0°C | 70°C |
| .2 | 57.0°C | 88.7°C | 97.9°C | 100°C |
| .3 | 57.9°C | 100.4°C | 120.2°C | 130°C |
| .6 | 58.9°C | 116.7°C | 160.7°C | 220°C |

Thus a nominal 0.3 K/W sink cannot be called a cool 300 W bicycle accessory. For a **chosen engineering trial base limit of 80°C** at 40°C ambient, 300 W continuous needs **Rth ≤0.133 K/W**, before local interface rise and uncertainty. The same 0.3 K/W estimate at 100 W gives 70°C steady, still requiring a guard; **80°C is a test abort threshold, not a safe-touch standard**. At 300 W, 600 s deposits **180 kJ**; a 900 J/K mass alone rises **200 K** without cooling. Thermal mass delays overheating; it does not dispose of continuous heat.

| Option | Verdict / decisive limitation |
|---|---|
| Existing mechanical brakes only | Required fallback; no added electrical heat. Actual rotor/rim/pad limits and long-descent technique still need checking. |
| Dedicated guarded sink | Recommended trial: known replaceable parts, measurable contact and cooling; 100 W first, 300 W only conditional. Large industrial extrusion may be bulky; weight and mounting strength unmeasured. |
| Villiger frame as intentional sink | Not recommended now: alloy/steel/composite, wall thickness, paint, joints, tube contact area, rider touch points and clamp permissions unknown. Whole-frame mass is not instantly available thermal mass. No verified K/W to compare with the ≤0.133 requirement. |
| Parallel resistor pair / stronger dumping | Reject for current baseline: 1.53 kW at 60 V; changes sink, chopper and fault requirements, not a free 4× upgrade. |

A reversible, mechanically approved bracket holding an insulated/guarded dedicated assembly is not the same as deliberately conducting heat into a structural frame. Do not drill, weld, strip paint, glue permanently or apply unspecified clamp pressure. Frame thermal expansion, coatings, bonds and fatigue cannot be qualified by aluminium specific heat.

Moving air may reduce Rth but a stop removes it precisely when stored heat remains. Re-evaluate with natural convection and zero wind; **do not continue using the moving-air Rth after stopping**. With generation removed the simple node cools, but real resistor internals can cause delayed base/guard hot spots (heat soak). If the dump remains powered by a fault, use the worse stationary Rth with continued power. Never leave the source on to simulate this without independent interruption. No road-speed convection curve or natural-convection geometry is validated here.

## 6. Provisional bench qualification, isolated from unfinished powerboard

1. Obtain current resistor documentation and sink drawing first; verify mounting footprint, flatness, compound, terminal insulation, guards, sensor attachment and electrical clearances. Use a fused, isolated, current-limited laboratory source, independent temperature cutoff and emergency disconnect. No bicycle, traction battery or rider for this test.
2. Begin at **25 W total for 60 s**, then **50 W for 60 s**, then **100 W up to 600 s** only after cooling and inspecting each stage. Two resistors in series take approximately 15.3/21.7/30.7 V DC at these powers. These are conservative *test starting points*, not already proven safe. Log V, I, case/base/guard/ambient temperatures at least once per second and resistance cold/after cooling; measure both resistor cases and the mounting interface vicinity.
3. Abort source power at **80°C sink/base**, **100°C resistor case**, or **50°C accessible guard**, abnormal temperature divergence, smell, resistance drift or failed sensors. These are selected conservative trial limits, not datasheet maxima or human-contact compliance. Keep hot equipment isolated until measured cool; mechanical/electrical protection must fail off independently of software.
4. After the 100 W data shows adequate margin, step 150/200/250/300 W for at most 60 s each. Only if temperature trend and worst-case conditions permit, test **300 W for up to 600 s**; 53.1 V nominal DC is sufficient for 300 W in 9.4 Ω. This tests average heat path without exposing the unfinished chopper. Keep cutoffs active; reaching a cutoff is a useful failure, not an invitation to raise it.
5. Repeat stationary with guard installed, worst intended ambient (initial target 40°C if safely reproducible), installed orientation and obstruction. A fan test is supplemental, never stationary proof. Record cooling for at least 20 minutes after removing power; continue if temperature has not peaked/declined at every monitored point. If using airflow, remove it at source turnoff and monitor heat soak. No unattended runs.
6. For a continuous claim, run until thermal equilibrium (provisional criterion <1°C change over 10 min) and document ambient stability; a 600 s test alone gives only a bounded transient result. Inspect/measure resistance after cooling and repeated cycles. Independently qualify actual 60 V PWM current, switching transient and fault waveforms with manufacturer pulse limits; the DC heat test cannot establish these.
7. Only after the protection owner resolves supply-loss clamping, isolation and pack charge rejection, test loaded motor behavior on a guarded dynamometer, including loss of brake request, thermal cutback and sink unavailability. Electrical thermal cutback must never remove the rider's mechanical braking path. Do not extrapolate DC-load success to safe downhill operation.

## 7. Ranked risks and remaining inputs

Likelihood is unknown without testing; ranking is severity first, not invented probabilities.

| Priority | Failure | Consequence / disposition |
|---|---|---|
| 1 | Battery rejects charge; control/safety supply lost | Bus overvoltage, loss of electrical brake; sink architecture unresolved. Mechanical brakes remain necessary; does not excuse bus protection. |
| 1 | Mechanical brake overheating or inadequate traction | Loss of speed control; no mechanical descent rating established. |
| 2 | Dump/interface/guard hot spots; airflow stops | Burns, cable/tyre/pack damage; sensors, guarded dedicated sink and staged independent test. Installed geometry unverified. |
| 2 | Chopper short/open or resistor fault | Uncommanded load or missing sink; fault/current/voltage behavior outside thermal model, requires hardware qualification. |
| 2 | Motor/inverter overtemperature or low-speed torque shortfall | Electrical assistance disappears; map measured limits, never promise holding torque. |
| 3 | Frame mount damages structure | Do not use frame as heat sink; obtain approved reversible mounting constraints. |

**Exact information needed before freezing a descent-specific assistance rating:**

1. Villiger exact model/year, frame/fork material and photos of candidate mounting region; manufacturer's permitted accessory mounts, clamp loads and no-modification constraints.
2. Actual weighed complete bicycle (including battery, generator, motor, sink and all brackets), confirming **120 kg rider+luggage plus vehicle**, and maximum gross rating of frame/wheels/tyres.
3. Named descent or equivalent: maximum sustained grade AND steepest segment, vertical drop, distance, intended speed range, duration of continuous lever request, desired assist level/duty and expected cooling breaks. No unlimited requirement is assumed.
4. Highest ambient, altitude, realistic tailwind, sun exposure, rain/mud/debris and stationary heat-soak conditions; clothing/luggage/skin clearances around proposed guard.
5. Mechanical brake make/model, front/rear arrangement, rotor diameter/thickness or rim type, pad type and condition, manufacturer's gross-load/descent restrictions. Who verifies mechanical brake capacity and stopping distance under full electrical failure?
6. Actual motor winding/hub and controller, wheel circumference, braking torque/current/speed map, winding and inverter temperature sensors/limits; approved low-speed fallback. Measured regen efficiency or loss map, not motoring headline efficiency.
7. Battery chemistry/series count/BMS charge acceptance and disconnect behavior at full/cold state; electrical protection owner's confirmed supply-loss sink, isolation, thresholds, hysteresis, fault handling and energy bounds. User need not design these; they are technical freeze prerequisites.
8. Acceptable added sink/guard mass, envelope and reversible mounting points; measured assembly Rth, hotspot temperatures, hot-start pulse/PWM approval and repeated-cycle results.

Without a chosen descent, the useful deliverable remains a **rider-requested, temperature-limited supplemental brake with a qualified electrical W/time envelope**, not automatic downhill speed regulation. Recommendation flips towards a larger sink/forced cooling or lower assist limit if the measured guarded stationary heat path cannot meet trial cutoffs. It does **not** flip towards intentional heating of an unknown frame.
