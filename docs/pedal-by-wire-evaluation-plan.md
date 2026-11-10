# Plan: evaluate a bicycle with independent pedalling

Status: proposed engineering evaluation; no component purchase or build approved.

## Goal and decision to make

Evaluate the original chainless, series-electric bicycle on its intended benefit:
independent control of pedal cadence and resistance, with temporary energy storage
and regenerative braking. Determine whether those capabilities justify conversion
losses, additional mass, cost and complexity for the intended rider and route.

Do not substitute a conventional electrically assisted bicycle and claim that it
meets the same requirements. Do not assume that the original idea must win or lose.

## Corrected requirements

- Pedal cadence is independent of wheel speed, including the possibility of
  pedalling while stopped to store energy.
- Electronics regulate pedal resistance and wheel torque separately, within
  generator, motor and storage limits.
- Storage absorbs surplus rider power and braking energy and supplies launch or
  short-duration power deficits.
- A depleted store has a defined startup procedure. Battery-free startup is an
  option to investigate, not a requirement already demonstrated.
- Durability, serviceability and storage aging matter alongside mass and price.

Cadence and torque set rider power: P = torque × angular velocity. Decoupling does
not create energy. A buffer cannot sustain a long climb if demand continuously
exceeds rider generation plus any permitted external energy input.

## Architecture and comparison baseline

Candidate:

```
pedals -> optional speed-increasing gears/belt -> generator -> controlled DC bus
                                                            |
                                                     bidirectional storage
                                                            |
                                     motor controller <-> hub motor <-> wheel
```

Generation feeds the motor bus directly when possible; only surplus/deficit energy
needs to cycle through storage. Battery assistance does not pass through the pedal
generator. Include gearbox, converter and housekeeping losses without double-counting
stages integrated into commercial units.

Compare against a chain-and-gears bicycle with the same class of hub motor and
regen capability. It preserves an efficient mechanical rider path but DOES NOT
provide independent cadence: while the chain drives the wheel, cadence is fixed by
road speed and selected gear. Automatic shifting is a separate intermediate option,
not a substitute for fully decoupled stationary pedalling.

## Phase 1 — specify the use case

Record rider and bicycle mass, sustainable and short-burst pedal power, preferred
cadence/torque range, target speed, hills and route profile, stop frequency, ambient
temperature, budget and allowed additional mass. Decide whether charging from the
mains is allowed or this must be energy-autonomous over a ride.

Define buffer duties in seconds and watts: launch, one stop, repeated stops,
pedalling at a light, and descents. Agree acceptable wheel-power loss, storage mass,
cost and ride duration before selecting parts. Numerical acceptance limits remain
open until the use case is agreed.

Deliverable: requirements and repeatable route/duty-cycle definitions.

## Phase 2 — audit evidence and shortlist real parts

- Identify purchasable pedal-generator modules and suitable permanent-magnet
  machines; request crank-to-DC efficiency maps versus cadence and torque.
- Evaluate any speed-increasing transmission explicitly. A fixed 3:1 or 4:1 ratio
  is not validated merely because a hub motor can generate electricity.
- Keep automotive and motorcycle alternators distinct: construction and excitation
  differ. Permanent-magnet machines need no field excitation, but their controller
  and DC bus still need a tested startup path.
- Obtain motor/controller maps, low-speed thermal limits, regen behavior and charge
  voltage/current limits, along with mechanical mounting requirements.
- Record dated supplier quotes, availability, mass, continuous/peak ratings, and
  datasheet URLs. Distinguish cell data from protected, enclosed pack data.

Evidence correction: previous chat/repository estimates are not measured results.
No verified Mando or Free Drive generator-efficiency map has been established here.
The word 'alternator' does not establish automotive claw-pole construction. A
reported battery-range difference cannot establish generator efficiency without a
defined duty cycle. Figures such as 61% or 71% are scenarios, not universal limits.

Deliverable: evidence-tagged shortlist and explicit missing-data list.

## Phase 3 — compare storage fairly

Compare (a) supercapacitors only, (b) battery only, and (c) a hybrid. Battery
candidates include LFP and LTO, plus a conventional lithium-ion reference where
appropriate. Do not select chemistry before power, energy and environmental duties
are established.

For each candidate calculate:

- Usable energy, peak/continuous charge and discharge power, and voltage window.
- Total installed mass, volume and cost including protection, balancing, enclosure,
  converters, wiring, fusing and precharge.
- Losses, self-discharge, standby power, low-temperature behavior and startup delay.
- Calendar and cycle aging under equivalent energy throughput and pulse duties.
  A traffic-light pulse is not automatically a full battery cycle.
- Regeneration with a full or cold store and a safe response to charge rejection.

Use E_kinetic = 0.5*m*v², E_height = m*g*h and
E_cap_usable = 0.5*C*(V_max² - V_min²), with joules divided by 3600 for Wh.
Include air/rolling losses and achievable braking torque before estimating captured
energy. Compare stores sized for the SAME buffer duty, not a large range battery
against an equally energetic capacitor bank unless long-range storage is required.

Do not simply parallel a large capacitor bank with a battery and assume controlled
power sharing. Evaluate inrush, voltage compatibility and whether a bidirectional
DC/DC stage is needed.

Deliverable: storage trade study with sensitivity analysis; no automatic preference
for caps, LFP, LTO or a hybrid.

## Phase 4 — time-resolved system model

Simulate flat cruise, launch/stop, urban traffic, sustained climbing and descent.
Track pedal mechanical input, electrical generation, wheel work, buffer state,
conversion/housekeeping losses and thermal limits. Account for initial and final
storage energy so stored battery power cannot masquerade as transmission efficiency.

Report separately:

1. Crank-to-DC efficiency and crank-to-wheel efficiency.
2. Battery-terminal-to-wheel efficiency where external battery energy is used.
3. Recovered energy and round-trip reuse, not just gross gravitational energy.
4. Rider cadence, torque and power variability; ride time and required rider work.
5. Installed mass, cost and state-of-charge feasibility over repeated routes.

Test optimistic and conservative component maps. Do not assume a fixed human
metabolic-efficiency gain from constant cadence: comfort, fatigue and physiological
benefit require separate evidence and eventually rider testing.

Deliverable: reproducible model, input provenance and balanced energy accounting.

## Phase 5 — instrumented bench prototype

Start with a guarded pedal-generator rig and load, not a road vehicle. Measure
crank torque/cadence and DC voltage/current simultaneously over the required operating
range. Verify calibration, uncertainty, heating and controller consumption.

Then integrate the motor and selected buffer on a stand. Exercise startup from
minimum stored energy, repeated acceleration/braking, full-store regen rejection,
sensor faults and shutdown. Mechanical brakes, fuses, torque reaction hardware,
current/voltage limits, precharge and safe fault handling are prerequisites to riding.
A PM generator can produce voltage without a battery, but successful automatic
controller boot and stable torque at low cadence must be demonstrated.

Deliverable: measured maps and logged startup, thermal and fault tests.

## Phase 6 — compare rides and decide

Use a closed-course comparison before public-road operation. Match route, speed or
trip-time target, rider effort protocol, payload, weather and storage start/end
conditions. Separate hardware losses from rider comfort and fatigue observations.
Check vehicle classification and local regulations for the final configuration.

Proceed only if the independent-pedalling benefit meets the agreed requirements
within measured energy, thermal, mass, cost and safety limits. Otherwise revise the
generator, storage sizing or intended use case, or explicitly accept a mechanically
geared alternative and its different capabilities.

## Work checklist

- [ ] Agree use case and numerical acceptance limits.
- [ ] Audit existing assertions and identify unverified component data.
- [ ] Obtain generator and motor maps and supplier quotes.
- [ ] Size and compare all three storage architectures.
- [ ] Run duty-cycle and sensitivity models with energy balance checks.
- [ ] Validate generator, buffer startup and regen on the bench.
- [ ] Complete safety/legal checks and controlled ride comparison.
- [ ] Publish evidence-backed design decision and remaining limitations.

## Related documentation

- [Illustrated parallel-hybrid baseline and limitations](analysis/parallel-hybrid-guide.md)
- [Earlier trade study (read with the evidence corrections above)](analysis/chainless-drivetrain.md)

This plan supersedes earlier blanket recommendations to retain the chain as if it
provided the same cadence freedom. It does not supersede physical energy accounting
or establish an efficiency result before components and duties are validated.
