> **STATUS: RESEARCH / CONSULTANT ANALYSIS — NOT A DECISION RECORD.** No medical benefit, fall prevention, rider safety or purchasable bicycle gyro is validated. No hardware change or purchase is authorized.

# Gyroscopic balance assistance: bounded feasibility study

| Record | Value |
|---|---|
| Date | 2026-11-10 |
| Branch / worktree | `pr/gyro-feasibility` / `~/worktrees/cycle-gyro-study` |
| Base | `d07bdb2` (already includes the accessibility research use case) |
| Scope | First-order roll torque, momentum, energy and sourcing; not a dynamic bicycle simulation |
| Reproduce | `python3 analysis/gyro/model.py`; `python3 -m unittest discover -s analysis/gyro -v` |
| Read alongside | [Current plan](../PLAN-parallel-hybrid.md), [parts evidence](gyro-parts-sources.md), [candidate BOM](gyro-candidate-bom.csv) |

## 0. Answer and recommended next step

**Physically possible to exchange a bounded roll impulse; not established as a safe or economical bicycle accessory.** Keep the current small electrical buffer unchanged. Treat gyro research as a separately costed option, not a new prerequisite for pedal-by-wire or its FSR circuitry.

1. **COMPUTED:** at 150 kg total and 1 m COM height, gravity alone demands 25.672 Nm at 1° and 128.206 Nm at 5°. Arresting an already falling bicycle needs additional dynamic torque/impulse.
2. **COMPUTED:** the earlier 25 km/h stopping-energy example is 3616.898 J and only 1.151294 Nms at 60,000 rpm. At a hypothetical 1 rad/s gimbal rate this gives at most 1.151294 Nm, not 128 Nm.
3. **Correction:** 1 Wh *usable* storage does **not** bound total stored energy if reserve speed is retained. With 60,000→48,000 rpm, 1 Wh usable requires 10,000 J full energy, retaining 6400 J; momentum falls from 3.183 to 2.546 Nms.
4. **CITED sourcing result:** no qualified bicycle-scale contained module established in this bounded search. Seakeeper 1 is a 165 kg marine comparator, not a bicycle candidate; Lit Motors is a vehicle/preorder lead, not a verified standalone module supplier. See vendor references and gaps in the linked evidence ledger.
5. **Recommendation:** compare mechanically supported adaptive cycles/trikes first; pursue only software and a separately risk-reviewed, guarded low-energy bench demonstration of bounded impulse. No vulnerable-rider testing, road trial or high-speed rotor construction.

This recommendation changes if a supplier offers a documented bicycle-suitable assembly with momentum envelope, containment/crash qualification, mounting loads, losses, service life and a complete installed quote. A video of a balanced prototype is not that evidence.

## 1. Inputs and evidence boundaries

| Input | Value / provenance |
|---|---|
| Rider plus luggage | 120 kg, operator-confirmed |
| Total mass | ASSUMPTION: 140 / 150 kg, including bicycle and any equipment; not weighed. Adding a gyro must not silently exceed this mass budget |
| Combined COM height | ASSUMPTION: 0.8 / 1.0 m above the ground contact-line pivot; unmeasured |
| Lean | ASSUMPTION: 0.5 / 1 / 3 / 5 degrees, stationary rigid-body screening cases |
| Gravity | 9.80665 m/s² standard gravity |
| 60,000 rpm | Hypothetical arithmetic case only, **not an approved operating speed or rotor specification** |
| Gimbal rates / travel | Hypothetical 1 / 3 / 10 rad/s, and ±45° example; no actuator rating implied |
| Bicycle tyres | Operator recalls thin road tyres at 9 bar; size, actual pressure and ratings unconfirmed. No load, grip or cooling conclusion follows |
| Budget | Cheapest feasible baseline, priced quality/performance upgrades; no fixed cap. Unknown costs remain unknown |

Every calculated figure below is from the stdlib model. Vendor claims are cited in the separate ledger, not treated as independent qualification. No rotor fabrication, carbon layup or safe-speed design is provided. The pasted 8–12 kg, 30% range loss, carbon rotor and medical guarantees are **unverified**, not inputs.

## 2. Gravity torque and dynamic limits

For a stationary rigid assembly pivoting about its tyre contact line:

`tau_gravity = m*g*h*sin(lean)`.

| Total kg | COM m | 0.5° Nm | 1° Nm | 3° Nm | 5° Nm |
|---:|---:|---:|---:|---:|---:|
| 140 | 0.8 | 9.585 | 19.169 | 57.483 | 95.727 |
| 140 | 1.0 | 11.981 | 23.961 | 71.854 | 119.659 |
| 150 | 0.8 | 10.269 | 20.538 | 61.589 | 102.565 |
| 150 | 1.0 | 12.837 | 25.672 | 76.986 | 128.206 |

These are not recovery ratings. A dynamic model also needs roll inertia, roll rate, steering geometry and speed, rider motion, tyre forces, road profile and controller latency. Holding a lean against gravity does not correct it. During a steady turn, appropriate lean follows lateral acceleration; forcing vertical can destabilize the bicycle. Tyre slip removes available contact-force authority: no gyro promise covers ice, arbitrary slides, potholes or collisions.

## 3. Angular momentum, geometry and finite authority

For rotor inertia `I`, speed `omega = rpm*2*pi/60`:

`E = I*omega²/2`, `H = I*omega = 2E/omega`.

Ideal CMG torque vector magnitude is bounded by `H*|gimbal_rate|`; it comes from redirecting rotor momentum. Roll torque is a projection, not always the whole magnitude. For one favorable orientation, `tau_roll = H*cos(delta)*delta_dot`; the available roll moment vanishes at the corresponding singular orientation. Reaction on the chassis has opposite sign to rotor momentum change. Bearing, friction, acceleration and actuator limits further constrain it.

A single dual-axis gimbal cannot provide arbitrary independent three-axis torque: at fixed H, its instantaneous momentum derivative is perpendicular to H. Two motors do not imply universal controllability or removal of singularities. Coupled pitch/yaw reactions and reachable trajectories must be modeled.

**Earlier example checked:** `E=.5*150*(25/3.6)²=3616.898 J`; at 60,000 rpm `H=1.151294 Nms`. Producing 128.206 Nm would require a best-case 111.358 rad/s gimbal rate. This is a mathematical ratio, **not** an achievable actuator recommendation.

At fixed rotor speed an absolute momentum-change bound is `|delta H| <= 2H`. Under constant 128.206 Nm torque, that example permits at most 0.017960 s of unidirectional impulse even if the entire vector reversal were usable. Real usable travel/geometry is less. This is not time-to-fall and does not imply an actual controller can realize that bound.

For a hypothetical H=10 Nms and ideal ±45° sweep, roll impulse is `H*(sin45°-sin(-45°))=14.142 Nms`. At 25.672 Nm this is 0.551 s. **Short disturbances differ from sustained imbalance.** A CMG can redirect momentum briefly; it cannot indefinitely oppose a constant external roll moment. Desaturation needs a feasible external torque/contact-force path (steering/motion, rider/support action), with its own stability constraints. Simply rewinding the gimbal returns an opposite impulse. Travel stops, singularities and reset scheduling belong in the control envelope.

Illustrative sizing at 150 kg, 1 m, 5° and **60,000 rpm**:

| Assumed gimbal rate rad/s | Required H Nms (best case) | Total rotor energy Wh |
|---:|---:|---:|
| 1 | 128.206 | 111.881 |
| 3 | 42.735 | 37.294 |
| 10 | 12.821 | 11.188 |

These are not component selections. At a fixed required H, lower rotor speed reduces E but increases required inertia; package/mass/stress cannot be inferred without a qualified rotor design. No mass is estimated here.

## 4. Usable energy is not total energy

For a fixed inertia and reserve ratio `r=omega_min/omega_max`:

`E_usable=E_full*(1-r²)`; `H_min=r*H_full`.

For **1 Wh usable** and 60,000 rpm maximum:

| Reserve speed ratio | Full energy J | Reserved energy J | Full H Nms | Minimum H Nms |
|---:|---:|---:|---:|---:|
| 0.5 | 4800.000 | 1200.000 | 1.528 | 0.764 |
| 0.8 | 10000.000 | 6400.000 | 3.183 | 2.546 |
| 0.9 | 18947.368 | 15347.368 | 6.031 | 5.428 |

As reserve approaches maximum speed, total energy for a fixed usable Wh grows without bound in this ideal equation. Thus dismissing every 1 Wh usable system as a 1 Wh total rotor is incorrect. Conversely, reserving more energy increases containment/startup obligations and still does not eliminate gimbal saturation. Balance guarantees must be sized at **minimum** momentum, not full speed.

Ideal spin-up lower bound is `t=E/P`, or `E/(efficiency*P)` neglecting other losses. At a hypothetical 100 W, 3616.898 J takes 36.169 s; 10,000 J takes 100.000 s. Actual time needs measured torque-speed limits, conversion efficiency and losses; support is needed during startup and shutdown.

## 5. Parasitic-energy sensitivity, not a drain prediction

Total additional input includes bearing/windage/vacuum-system losses if applicable, power electronics, sensing/control and gimbal operation. Mechanical support during startup and stopped operation is separate. None of these losses has been measured for a bicycle module.

For one hour, `E_extra_Wh=P_extra_W*1 h`:

| Assumed extra average W | 1 | 5 | 10 | 25 | 50 | 100 |
|---|---:|---:|---:|---:|---:|---:|
| Extra Wh | 1 | 5 | 10 | 25 | 50 | 100 |

This is a sensitivity sweep, **not guessed actual drain**. Range impact additionally requires baseline Wh/km, battery usable energy, duty cycle, added mass, terrain and starts. The alleged 30% penalty cannot be inferred from these numbers. Marine module operating consumption is not transferable to a bicycle.

## 6. Architecture and complete-cost comparison

| Option | What it buys / limits | Complete-system cost status |
|---|---|---|
| Existing electrical buffer, no gyro | Cheapest *unchanged* project baseline; no added balance assistance | No incremental gyro expenditure; baseline costs remain in the existing project, not re-estimated here |
| Appropriately specified adaptive tricycle / mechanical supports | Ground reaction can support at rest without spinning energy; still has turning/tipping, width, fit and deployment hazards | **Unknown** installed supplier quote; include cycle/support, fit assessment, installation, transport and service. Cannot claim cheaper total until comparable quotes exist |
| Dedicated balance-only CMG | Can maintain a reserved speed independently of drivetrain energy requests; finite impulse and startup/power risks persist | **Unknown**: qualified rotor enclosure, bearings, drive, gimbal, sensors/controller, fail-safe supports, mounting, qualification and service required |
| Combined storage + balance | Shares rotating hardware but energy discharge reduces H; priority arbitration and minimum reserve compulsory | **Unknown**: all dedicated costs plus bidirectional power conversion, energy reserve/control integration and additional validation; no demonstrated saving |

No fixed budget cap is assumed. Recommend cheapest **feasible and qualified** baseline first, then price quality/performance upgrades with documented complete scope. Individual electronics prices would not be a gyro-system price. No comparable complete quotes were obtained; no fabricated totals or stock claims are supplied. Mechanical support is the preferred comparison, not a declaration that an unassessed retrofit is safe.

The [candidate CSV](gyro-candidate-bom.csv) is a **research shortlist, not an approved purchase BOM**: Seakeeper scale comparator; Adafruit BNO085 sensing board; Teensy 4.1 controller; DYNAMIXEL XM430-W350 bench-actuator lead; educational gyro lead on HOLD; Lit Motors supplier inquiry. The servo's stall torque is not continuous torque and not equal to useful gyro roll authority. No demonstrated low-energy guarded rotor assembly was qualified; software/controller work can proceed without spinning one.

## 7. Risk and release gates

Likelihoods are unknown without a design, so a numerical severity×likelihood ranking would be fabricated. Severity-first priorities:

| Priority / failure | Consequence | Required evidence / mitigation |
|---|---|---|
| Critical: rotor burst, bearing seizure, overspeed or crash damage | Projectile/impact energy, sudden chassis torque | Specialist containment/overspeed/bearing/rotordynamic/crash engineering and independent qualification; raw motor plus carbon disc is not a safe module |
| Critical: depleted spin, power loss, startup/shutdown | Loss of assistance; fall | Mechanically supported safe state with verified deployment/availability; never promise stopping upright without power/spin |
| Critical: singularity, saturation, sensor/controller/actuator fault | Wrong or unavailable corrective torque | Bounded envelope, saturation prediction, diagnostics, fault injection, independent restraint in tests |
| High: frame clamp load/fatigue, gimbal reaction | Frame failure, handling changes | Reversible fit only; no drilling/welding. Clamp fatigue and thin-tube/local loads need frame-specific approval; reversibility alone is not structural safety |
| High: turning or tyre slip | Loss of traction, inappropriate torque | Contact/steering model, dry restrained trials only after review; no recovery guarantee |
| High: heat/electrical faults | Burns/fire/control shutdown | Measured thermal/electrical limits, isolation, safe power inhibit and guards |

No mitigation is claimed implemented. Neither numerical tests nor an enclosure photograph certify safety. Vulnerable-rider trials are out of scope. There is no medical benefit/suitability assertion and no guarantee of never tipping. Calling the idea an accessibility use case does not establish medical-device classification; country, intended claims and applicable legal rules remain unknown, so no legal conclusion is made.

## 8. Bounded progression and decision inputs

1. **Now:** retain electrical baseline; preserve the five prior use cases and accessibility research wording. Review these calculations and sources independently before merging.
2. **Low-risk experiment:** simulate roll/contact dynamics and faults; evaluate IMU latency/bias on a static fixture and actuator limits without a high-energy rotor. A guarded low-energy demonstrator requires documented maximum stored energy and guard/fixture review first; educational branding alone does not establish this.
3. **Supplier inquiry:** ask for complete qualified-module data and installed quote, not a motor/disc shopping list. Compare mechanical supports/adaptive-cycle options using equivalent fit, stopping, mounting and failure requirements.
4. **Before any bicycle experiment:** weigh the actual assembly, measure COM/roll inertia, identify tyre size/rating and frame load permissions, define disturbance torque/impulse and support requirements. No inference from the recalled 9 bar.

Needed operator inputs are desired assistance scenario (mounting, starts, brief low-speed disturbance, or supported stationary waiting), acceptable added mass/space/startup delay, bicycle identity/fit dimensions and country of use. These refine requirements; they do not authorize purchases. Needed supplier evidence is minimum-H torque/travel envelope, containment/crash test scope, continuous actuator capability, measured losses and complete installed cost. Until then the feasible baseline remains unchanged and gyro research remains separate.

## Verification record

The stdlib script ran successfully and **8 unit tests passed**: gravity limits/sign, independent inertia-to-energy identity, prior stopping-energy example, reserve conservation/scaling, reserve divergence, travel impulse bound, spin-up and invalid inputs. These verify arithmetic, not rider safety, hardware or closed-loop vehicle performance. No hardware, FSR circuitry or existing board files changed.
