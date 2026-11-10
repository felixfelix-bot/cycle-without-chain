# Chainless (series-hybrid) bicycle: drivetrain + energy-buffer trade study

> **STATUS: CONSULTANT ANALYSIS — NOT A DECISION RECORD.** Not an ADR, not an
> operator decision, no authorisation to buy or build anything. Every number
> below is the printed output of `chainless_drivetrain_model.py` in this
> directory, or is labelled CITED / ESTIMATE / TODO(unverified).

| field | value |
|---|---|
| date | 2026-11-10 |
| author | Felix (Hermes manager) |
| lens | drivetrain efficiency, buffer sizing, excitation/bootstrap |
| not re-deriving | tyre/rolling-resistance physics, rider biomechanics beyond cadence, structural design of the frame |
| read first | this file, then `chainless_drivetrain_model.py` |
| question | series hybrid (pedal → generator → buffer → hub motor) vs chain drive; supercaps vs batteries vs both |

---

## §0 Answer first

**The drivetrain idea loses on physics; the buffer idea is right but points at
LTO, not supercapacitors.** Five findings carry that:

1. **The series hybrid throws away ~35 percentage points of the rider's power
   before it reaches the road.** Chain (derailleur, waxed) = **96.1 %**
   [CITED]. Series hybrid with a *good* PM generator = **61.3 %** [COMPUTED].
   Even with every single stage at its datasheet peak simultaneously the chain
   wins by **19.9 points** [COMPUTED]. To put 150 W on the road you must pedal
   at **244.6 W** instead of **150.5 W** — a +63 % tax on the rider.

2. **A car alternator is the wrong machine by a factor of two again.**
   Claw-pole Lundell alternators are **42 % efficient** over a real drive cycle
   and **53 % at best** [CITED: InTechOpen, Delcotron 22SI]. In the bike chain
   that yields **39.2 %** end-to-end, and **21.4 %** below 1500 rpm. Worse, they
   are *separately excited* — see finding 4.

3. **The energy you want to recover at the traffic light is tiny.** At 25 km/h
   with 94 kg, KE = **2267 J = 0.63 Wh**. Twenty stop-starts per 10 km commute =
   **12.6 Wh gross**, of which **7.9 Wh** is recoverable through the honest
   two-hop chain (see §12) — versus **55.6 Wh**
   of flat-road tractive energy for the whole trip. Real-world ebike regen
   recovery is **3–8 %**, up to ~14 % in dense stop-go [CITED: ebikes.ca].
   *(The 8.2 Wh printed here previously is **superseded** — §12 shows it used
   65 % as a single KE→battery hop.)*
   The prize is real but small, and a **normal e-bike with a DD hub already
   gets it** — no chain removal required.

4. **"No battery at all" fails on two independent grounds.** (a) A claw-pole
   alternator needs **84 W of field excitation** (6 A × 14 V [CITED]) before it
   produces any output — it cannot self-start from a dead bus. A PM machine
   *can* (residual flux → back-EMF → rectify), which is why the alternator is
   the wrong choice even if you insist on series hybrid. (b) The controller
   itself needs ~**3 W** of housekeeping whenever it is on; a cap bank at 0 V
   cannot bring up its own controller. **You need at least a small battery, or
   a pre-charge + keep-alive circuit and a hand-spin start ritual.**

5. **Supercapacitors are a power buffer, not an energy store — by 19×.**
   400 F / 2.7 V cells give **4.84 Wh/kg at pack level** vs **90 Wh/kg** for an
   LFP pack [COMPUTED]. A 500 Wh cap bank would weigh **103 kg**. And the
   buffer *function* needs almost nothing: **one 18-cell string (22.2 F at
   48.6 V, 1.12 kg, USD 293)** already covers **4.4×** the energy of one
   stop-start. So: if you want a buffer, it is small; if you want *range*, it
   cannot be a capacitor. **LTO is the honest answer to "I want it to last"** —
   20 000–50 000 cycles, 70 Wh/kg, in between on every axis.

**Recommendation: build the parallel hybrid** (chain stays, DD hub motor with
regen, one LFP or LTO pack). It delivers every benefit you actually asked for —
optimal cadence via the motor's gearing, energy recovery at lights, no chain
*torque* burden on the cranks — while protecting the rider's watts, which the
series hybrid does not.

---

## §1 Assumptions

| # | assumption | value | basis |
|---|---|---|---|
| A1 | rider mass | 78 kg | ASSUMPTION |
| A2 | bike + motor + pack mass | 16 kg | ESTIMATE |
| A3 | CdA, upright commuter | 0.50 m² | ESTIMATE (Cd 0.8 × A 0.62) |
| A4 | Crr, good tyre on asphalt | 0.006 | ESTIMATE (0.005–0.008) |
| A5 | cruise speed | 25 km/h | ASSUMPTION (EU L1e-A class) |
| A6 | rider continuous power | 150 W | ESTIMATE |
| A7 | regen capture efficiency — **withdrawn from the current figure** | 65 % | ESTIMATE; applied as a single KE→battery hop, which §12 corrected |
| A8 | off-cadence metabolic penalty | 4 % | ESTIMATE, ~20 rpm off optimum |
| A9 | battery round-trip incl. BMS | 92 % | ESTIMATE |
| A10 | supercap round-trip at bike currents | 97 % | ESTIMATE |
| A11 | controller (FOC inverter) | 95 % | ESTIMATE |
| A12 | 3-phase rectifier front end | 96 % | ESTIMATE |

Every A-row that is an ESTIMATE is pushed to its favourable end in §8.

### Cited efficiency figures

| item | number | source |
|---|---|---|
| single-speed chain drive | **99.71 %** | Casteel & Archibald, ASME IMECE2013-64507 |
| 7-speed derailleur | 97.7–99.4 % | same |
| derailleur, new + waxed (on-bike) | **96.1 %** | CyclingAbout drivetrain test |
| derailleur, worn chain | 90.6 % | same |
| belt drive | 98.0 % | Casteel |
| Rohloff Speedhub | 95.8–99.5 % | Casteel |
| Shimano Alfine 11 | 90.4–96.6 % | Casteel |
| recumbent, two idlers | 94.3–94.7 % | CyclingAbout |
| DD hub motor, *system* @ 31 km/h | **86 %** | Grin motor simulator |
| small geared hub, system peak | 81 % | Grin |
| MXUS 1.5 kW DD at half top speed | 75 % | sportdevices dyno note |
| RC outrunner (Hacker A20-22L) | 85 % max | datasheet |
| car alternator, drive-cycle average | **42.4 %** | InTechOpen Lundell paper |
| car alternator @ idle / 6000 rpm | 53 % / 42 % | same |
| car alternator generation-start speed | 910–1670 rpm | same |
| car alternator, peak-efficiency window | 30–40 % load, 2000–2500 rpm | Bosch/ADVISOR map |
| hub dynamo (SON delux, best case) | 78 % @ 10 km/h, 67–70 % @ 20–30 km/h | Fahrradzukunft / CyclingAbout |
| ebike regen recovery, real world | 3–8 % (≤14 % city, 20 % trike) | ebikes.ca |

---

## §2 Vehicle power and energy

```
P_flat = (Crr·m·g + ½·ρ·CdA·v²)·v
       = (5.53 N + 14.47 N) × 6.94 m/s
       = 138.9 W at the wheel at 25 km/h
```

```
KE(25 km/h) = ½·94·6.94² = 2267 J = 0.630 Wh
```

Ten kilometres at 25 km/h takes 24.0 min and **55.6 Wh** of tractive energy.
Twenty stop-starts contribute **12.6 Wh** of gross kinetic energy, of which
**7.9 Wh (14.2 %)** is recoverable once the chain is counted as two hops
(KE→battery 0.791, battery→wheel 0.791 — see §12). That agrees with
the cited 3–8 % flat / ≤14 % urban range — the model is not optimistic.

> **Superseded figure.** This section previously printed **8.2 Wh (14.7 %)**
> "at 65 % regen efficiency". 65 % (assumption A7) was applied as a *single*
> KE→battery hop, which omits the battery→wheel hop. The figure is withdrawn,
> not deleted: §12 *Correction to §3/§5* carries the current number, and
> `analysis/cx/regen_recovery.py` reproduces both from the committed model
> (`docs/analysis/chainless_drivetrain_model.py`, §14 output). 8.2 Wh must not
> be quoted as this study's result.

---

## §3 Series hybrid vs chain — the core comparison

```
η_series = η_gen × η_rect × η_buf × η_ctrl × η_motor
```

| variant | calculation | η |
|---|---|---|
| PM generator (good point) + LFP | 0.86 × 0.96 × 0.92 × 0.95 × 0.85 | **61.3 %** |
| PM generator (off-peak rpm) + LFP | 0.78 × 0.96 × 0.92 × 0.95 × 0.85 | **55.6 %** |
| PM generator + supercap only | 0.86 × 0.96 × 0.97 × 0.95 × 0.85 | **64.7 %** |
| car alternator (good window) | 0.55 × 0.96 × 0.92 × 0.95 × 0.85 | **39.2 %** |
| car alternator (<1500 rpm) | 0.30 × 0.96 × 0.92 × 0.95 × 0.85 | **21.4 %** |
| **chain, derailleur, waxed** | single stage | **96.1 %** |
| **chain, single-speed** | single stage | **99.7 %** |

At 150 W of pedalling, power arriving at the road:

| path | W at road | loss |
|---|---|---|
| chain, single-speed | 149.6 | 0.5 W |
| chain, derailleur | 144.2 | 5.9 W |
| chain, worn | 135.9 | 14.1 W |
| series hybrid, PM + battery | **92.0** | **58.0 W** |
| series hybrid, car alternator | **58.8** | **91.2 W** |

Inverted — pedal power needed to put 150 W on the road: chain **150.5 W**,
series hybrid **244.6 W**, car alternator **382.4 W**.

---

## §4 Does "always optimal cadence" pay for that?

The benefit of infinitely-variable gearing is bounded by the metabolic penalty
of riding *off* optimum. Optimal cadence rises with intensity — ~45 rpm at very
low power, 66 rpm at 100–200 W, 78 rpm at 300 W [CITED: Dunst et al. 2024;
ODU thesis]. A modern derailleur spans roughly 400–500 % ratio, which keeps a
rider within a few rpm of optimum across the whole useful speed range.

Taking a generous **4 %** penalty for being 20 rpm off optimum:

```
cost/benefit = (0.961 − 0.613) / 0.04 = 8.7×
```

**The transmission costs 8.7 times more than the gearing benefit it buys.**
You would have to believe cadence optimisation is worth ~35 % of your power
output for the trade to break even. Nobody believes that.

---

## §5 Buffer sizing — how much do you actually need?

Absorbing one stop into a capacitor bank between voltage limits:

```
E = ½·C·(Vmax² − Vmin²)  →  C = 2E/(Vmax² − Vmin²)
C = 2 × 2267 / (50² − 40²) = 5.04 F   (48 V bus, 40–50 V window)
```

One string of **18 × 400 F / 2.7 V cells** in series = **22.2 F at 48.6 V**,
which is **4.4× the single-stop requirement**. Cost: **1.12 kg of cells,
USD 293** (Eaton XV3560-2R7407-R at USD 16.27 qty-1), storing **7.29 Wh** at
full charge.

**So the buffer is trivially small — and therefore pointless as a design
driver.** Note what this sizing does *not* use: it absorbs one stop's raw
kinetic energy, so it is independent of the regen-chain correction in §12. The
only recoverable-energy figure this study publishes is **§12's 7.9 Wh**; the
8.2 Wh single-hop figure that used to be quoted in §0/§2 is **superseded** and
must not be reused for sizing (see §12, *Correction to §3/§5*).

The reason people reach for capacitors is *range*, and that is where
they collapse:

| target | supercap pack | LFP pack | LTO pack |
|---|---|---|---|
| 10 Wh | 2.1 kg | 0.11 kg | 0.14 kg |
| 50 Wh | 10.3 kg | 0.56 kg | 0.71 kg |
| 150 Wh | 31.0 kg | 1.67 kg | 2.14 kg |
| 300 Wh | 62.0 kg | 3.33 kg | 4.29 kg |
| 500 Wh | **103.3 kg** | **5.56 kg** | 7.14 kg |

Supercap pack energy density is **4.84 Wh/kg** (cell 6.53 Wh/kg ÷ 1.35 pack
factor) against **90 Wh/kg** LFP — a **19× mass ratio**.

---

## §6 Is the buffer needed at all?

```
250 W at 48 V = 5.2 A → 0.50 C on a 500 Wh pack
```

A 500 Wh LFP pack rated 1 C continuous / 3 C burst handles **10 A / 30 A**. The
motor current is **not** a stress on the pack. I²R at 5.2 A: **2.71 W** in the
battery vs **1.56 W** in a cap string — a **1.15 W** saving during braking
only. Negligible.

Cap leakage is the real cost of an always-connected bank: **5.2 mA × 48 V =
0.25 W**, i.e. **0.17 Wh** over a 40 min commute (**0.30 %** of trip energy).
Small, but it is a permanent tax the battery does not impose.

**Verdict on the buffer: not needed for power, cannot serve for energy.** It is
a solution to a problem that a correctly sized pack does not have.

---

## §7 Excitation — can it start with no battery?

This is the sharpest part of the question and the answer is a clean split:

**(a) PM machine: yes, it self-starts.** Residual magnet flux produces back-EMF
at any rpm. Rectify it and you have a DC bus. No excitation, no bootstrap
problem. This is why the alternator is the wrong machine regardless of
architecture.

**(b) Claw-pole alternator: no.** It needs **6 A × 14 V = 84 W** of field
current before it makes any output [CITED: InTechOpen], and its regulator needs
a supply rail to run at all. Below its **910–1670 rpm generation-start speed** it
produces nothing. A bicycle crank turns at **~75 rpm**, so you need a **20:1
step-up** — a belt or gearbox with its own losses and audible whine. The Mando
Footloose (the one production chainless e-bike, 22.7 kg) was criticised
specifically for being *"very loud (motor and pedaling generator system)"*.

**(c) Even a battery-less PM build needs a rail for the controller.** ~**3 W**
of housekeeping (MCU, gate drivers, hall sensors). A 22.2 F string at 48 V holds
7.11 Wh, so ~**142.2 min** of standby — but at *zero* volts it cannot bring its own
controller up. Practical answer: a pre-charge resistor and either a small
keep-alive pack, a supercap "seed" that is never fully drained by the BMS, or a
hand-spin start before the electronics wake. All three are extra failure modes
for no benefit.

**Conclusion: "no battery at all" is achievable only with a PM machine plus a
bootstrap circuit, and it buys nothing — it removes the one component that
handles the generator's speed-dependent output and keeps the bus stable.**

---

## §8 Sensitivity — push every ESTIMATE to its favourable end

```
best credible series hybrid = 0.90 gen × 0.98 rect × 0.98 buf × 0.98 ctrl × 0.90 motor
                            = 0.762  (76.2 %)
```

vs chain **96.1 %** → still **19.9 points worse**. And if the rider is a full
20 rpm off optimum on a derailleur (chain effective 92.3 %), the series hybrid
at its absolute best is *still* **16.0 points worse**.

**The conclusion survives the entire plausible parameter box.** There is no
combination of market parts and optimistic assumptions under which the series
hybrid beats a chain on rider power.

---

## §9 Failure modes

| # | failure | severity | likelihood | mitigation |
|---|---|---|---|---|
| F1 | rider power loss makes the bike feel dead / unrideable without assist | high | certain | none — inherent to the architecture |
| F2 | controller cannot boot from a drained cap bank | high | medium | small keep-alive pack; adds the battery you were avoiding |
| F3 | claw-pole alternator gives no output at low cadence | high | certain | 20:1 step-up + whine; or use a PM machine |
| F4 | cap bank self-discharges over a parked weekend | medium | medium | leakage 0.25 W → days, not hours; acceptable |
| F5 | bus voltage swings 40–50 V on every pedal stroke | medium | high | requires a battery to stiffen the bus |
| F6 | single point of failure: one controller kills all propulsion | medium | medium | none — *accepted* (this is why series hybrids are unpopular) |
| F7 | generator + motor + 2 controllers = 2× the electronics to fail | medium | medium | none — *accepted* |

---

## §10 Recommendation

**Build the parallel hybrid.** Concretely, this is a normal e-bike and that is
the point:

| item | part | kg | USD |
|---|---|---|---|
| hub motor, DD, regen-capable | Grin All-Axle / GMAC | 3.90 | 380 |
| motor controller, FOC, regen | Grin Phaserunner | 0.28 | 295 |
| battery, LFP 48 V 10 Ah | generic LFP pack, 480 Wh | 5.30 | 320 |
| torque sensor (BB) | Grin / Sempu | 0.25 | 150 |
| cycle analyst / display | Grin CA3 | 0.10 | 145 |
| chain + cassette + derailleur | existing, keep | 0.90 | 0 |
| **total (incremental)** | | **10.73** | **1290** |

What this actually delivers against your stated goals:

- **"Cyclist can always pedal at optimal speed/torque"** → the *motor's* gearing
  does the adapting; the rider's cadence stays free. You do not need to remove
  the chain to get this — you need a torque sensor and a controller that
  follows it.
- **"Recover energy at the traffic light"** → DD hub regen, **3–8 %** typical,
  up to 14 % urban [CITED]. Exactly the benefit, without the 35-point tax.
- **"Electronics handle the transmission/gears"** → a DD hub with a wide-ratio
  cassette already gives you electronic assist at any wheel speed while the
  rider picks their own cadence.

**Where the series hybrid genuinely wins** (and this is the honest carve-out):
- very long wheelbase, cargo, or velomobile layouts where the chain needs
  several idlers — already down to **94.3–94.7 %** and mechanically awkward
- independent left/right or two-wheel drive
- a design where you specifically *want* the crank decoupled from wheel speed
  (e.g. a constant-rpm generator feeding a variable-speed wheel)

**If you still want the chain gone** — cheapest honest version: PM generator at
the crank (belt, ~4:1, near its peak), 3-phase rectifier, **48 V LFP 5 Ah
(240 Wh, 2.7 kg)**, FOC controller, DD hub motor. Expect **61 %** at best and
**56 %** typical, versus **96 %** for the chain you removed. Use **LTO** if the
wear profile matters more than mass.

**Explicitly NOT recommended:** a car/motorbike alternator (39 % end-to-end,
separately excited, needs 20:1 step-up), and a capacitor-only buffer (19× the
mass for the same energy, and it cannot boot the controller).

**Worked numbers, plain-language part descriptions, and the production
precedent for this build are in §12 and §13.**

---

## §11 Reconciling with the two production systems

Two series-hybrid bikes reached production. **Neither publishes a generator
efficiency number** — which is itself informative — but one publishes a system
claim that looks like it contradicts this analysis, so it has to be reconciled
rather than ignored.

### Schaeffler / Heinzmann "Free Drive" (2021, in fleet production since 2023)

A Schaeffler representative told Electrek that Free Drive is **"approximately
5 % less efficient than chain drives"**, repeated by BikeRadar and New Atlas as
a 5 % range penalty [CITED]. Taken naively, that is 96 % end-to-end and would
demolish §3.

**It cannot be a drivetrain-efficiency claim.** Working backwards: 96.1 % −
5 % = 91.1 % required end-to-end. Allowing 97 % rectifier, 97 % buffer, 97 %
controller and 93 % motor leaves a required generator efficiency of **1.073** —
greater than unity. **91 % is thermodynamically impossible** for two machine
conversions plus a battery. The claim is not what it reads as.

It is a **vehicle-level range claim**, and it only holds on a vehicle where the
rider is a minority energy source:

```
penalty(r) = r·(1 − η_series/0.961) / (1 − r)      r = rider's share of traction energy
```

| r | vehicle class | battery penalty |
|---|---|---|
| 1.00 | rider does all the work (flat battery) | **57 % more pedal effort** |
| 0.60 | light commuter, strong rider | 54.3 % |
| 0.44 | cargo bike, 250 W motor + 150 W rider | 28.4 % |
| 0.30 | motor-dominant pedelec | 15.5 % |
| 0.12 | heavily motor-dominant | **4.9 %** ← reproduces the 5 % |

Reproducing 5 % requires **r = 0.121**, i.e. the rider supplies only **12 %** of
traction energy. That is a genuinely motor-dominant cargo vehicle. So the 5 %
is defensible *for a loaded cargo bike and cannot be generalised* — which
explains both why Schaeffler aimed Free Drive at cargo/velomobile rather than
commuters, and why the same architecture failed on a light city bike.

### The pedal generator itself: ≈ 42 %

Schaeffler's component is a **1:29 cycloid gearbox plus an alternator**
[CITED: Heinzmann Free Drive leaflet]. That ratio is a smart engineering choice
— 75 rpm cadence × 29 = **2175 rpm**, which lands the alternator exactly inside
the claw-pole sweet spot (2000–2500 rpm, 30–40 % load) where it is *least bad*.

| stage | η | basis |
|---|---|---|
| cycloid gearbox, 1:29 | 0.75–0.85 (use 0.80) | CITED: Rice Univ. 2018 compact cycloid peak 81 %; Matec 2019 experimental 0.61–0.75 at 150–850 rpm; Blagojević 2012 0.77 at µ=0.2 |
| alternator at 2175 rpm | 0.50–0.55 (use 0.52) | CITED: InTechOpen Lundell + Bosch/ADVISOR peak window |
| **pedal generator unit** | **≈ 0.42** (0.38–0.47) | COMPUTED |
| + rectifier/controller/motor | **0.322** | COMPUTED |

**So the answer to "what is the efficiency of these crank alternators" is
~40–45 % for the pedal-generator unit, and ~32 % from pedals to road.** That is
*below* my generic series-hybrid estimate (61.3 %) because both production
systems used automotive claw-pole machines rather than PM machines. My §3 PM
case was the *charitable* one.

### Mando Footloose (2015) — the natural experiment

Mando's own product page lists **"Alternator + Regulator"** and **"ECU"** as
automotive-derived parts [CITED: mandofootloose.co.kr], and describes the drive
as a 系列 하이브리드 시스템 (series hybrid): 250 W motor, 36 V 8.2 Ah, 21.5 kg,
20″ wheels.

Two owner reports are direct evidence for §7:

- **"Very loud (motor and pedaling generator system)"** [CITED:
  ElectricBikeReview] — exactly what a claw-pole spinning at a multiple of
  cadence does.
- **"Once the battery dies, the bike is rendered completely unrideable"**
  [CITED: idropnews] — **direct field confirmation of the bootstrap finding**.
  A separately-excited generator cannot self-start, and with no chain there is
  no mechanical fallback. The bicycle becomes a 21.5 kg scooter.

### What this changes in the analysis, and what it does not

- **Changes:** the generic series-hybrid number is *optimistic* for the two
  real systems. Actual production hardware is ~32 % pedals-to-road, not 61 %.
  The parallel-hybrid recommendation gets **stronger**, not weaker.
- **Does not change:** the direction of the verdict. The best-case PM series
  hybrid (76.2 % at every stage's peak) still loses to a chain by 19.9 points.
  The production systems, at ~32–42 %, are much further away.
- **Reconciles:** Schaeffler's 5 % is a *vehicle range* figure at r ≈ 0.12, not
  a drivetrain efficiency. Read it as marketing-of-a-real-result on a narrow
  vehicle class, not as a refutation of the physics.
- **Confirms the architecture's niche:** Schaeffler's own pivot to cargo,
  three- and four-wheelers and velomobiles is exactly the carve-out in §10 —
  where a chain needs several idlers and the rider is a minority power source.

---

## §12 The recommended build: how it works and what it costs

### The two paths

The parallel hybrid has **two independent power paths that meet at the rear
wheel**. They never convert into each other.

```
  your legs  ->  crank  ->  chainring  ->  CHAIN  ->  cassette  ->  rear wheel
                                                                        ^
  battery    ->  controller  ->  hub motor (inside the wheel)  ---------+
```

The motor sits *inside* the rear hub, so it adds torque directly at the wheel.
Your legs push through the chain; the motor pushes at the hub. Both spin the
same wheel. **Your 150 W never becomes electricity**, so it never pays the
conversion tax that kills the series hybrid.

### Measured efficiencies of each path

| path | η | basis |
|---|---|---|
| **rider path** — waxed derailleur | **96.1 %** | CITED: CyclingAbout on-bike measurement |
| rider path — single-speed chain | 99.7 % | CITED: Casteel & Archibald |
| **motor path** — battery → controller → wheel | **86.0 %** | CITED: Grin DD hub *system* @ 31 km/h |
| controller only | 95 % | ESTIMATE (motor = 86/95 = 90.5 %) |
| **regen round trip** (KE → battery → wheel) | **62.6 %** | COMPUTED 0.86² × 0.92 |
| coast drag, DD hub unpowered | **2 W** = 1.4 % of cruise | ESTIMATE 1–4 W |
| battery round trip, LFP | 92 % | ESTIMATE incl. BMS |

### The number that matters

```
rider 150 W at pedals × 0.961  =  144.2 W at the wheel
road demand at 25 km/h         =  138.9 W
surplus                        =   +5.3 W
```

**The rider covers 25 km/h on their legs alone, battery idle.** The series
hybrid with the same rider produces 92.0 W at the wheel and leaves a **46.9 W
hole** — the battery must supply **74.9 W just to match** the parallel bike on
flat ground. That is the whole argument in two lines.

### Correction to §3/§5 — the regen figure

The earlier 8.2 Wh — the **superseded** single-hop figure — used 65 % as a
*single* KE→battery hop. The honest chain is two hops (0.791 out, 0.791 back):

```
2267 J × 0.791 = 1793 J = 0.498 Wh stored
      × 0.791 = 1419 J = 0.394 Wh back at the wheel
20 stops        → 7.9 Wh usable = 14.2 % of the 10 km trip energy
```

**7.9 Wh is the current figure.** Same order of magnitude as the withdrawn one;
the 8.2 Wh single-hop figure is **superseded** and is now marked as such in
§0, §2 and §5 rather than left quotable. Both are single-digit Wh, and neither
justifies removing a chain.

Reproduce both: `analysis/cx/regen_recovery.py` prints 7.88 Wh for the two-hop
chain and 8.18 Wh for the withdrawn one-hop chain, and its tests assert they
agree with the committed model's own output
(`docs/analysis/chainless_drivetrain_model.py`, §14 `Regen at the traffic
light, honest round trip`).

### The honest tax, and the real trade-off

A direct-drive hub drags when coasting unpowered: **2 W at 25 km/h = 1.4 % of
cruise demand**. A geared hub freewheels with ~0 drag — **but then it cannot
regen**. That is the actual trade-off, not a myth. Grin states it plainly:
regen "only works on a direct-drive motor, not on a normal freewheeling geared
hub" [CITED: ebikes.ca].

### Range — and why the model is optimistic

| motor's share of traction energy | battery draw | range on 480 Wh |
|---|---|---|
| 30 % | 1.94 Wh/km | 248 km |
| 50 % | 3.23 Wh/km | 149 km |
| 70 % | 4.52 Wh/km | 106 km |
| 90 % | 5.81 Wh/km | 83 km |

**These are a ceiling, not a prediction.** Real 480 Wh commuter packs deliver
**25–40 km**. The model assumes flat, still air, constant 25 km/h, no hills, no
stops. Real commuting adds grades (each 1 % at 94 kg is +9.2 W per km/h),
stop-starts, headwind and cold cells. Expect **2–3× worse** than this table.

### The parts, in plain language

| part | what it is | why it is there |
|---|---|---|
| **Grin All-Axle** (3.9 kg) | direct-drive hub motor, laced into the rear wheel like a normal hub. No gears inside — the motor *is* the wheel | direct drive is what makes regen possible; a geared hub freewheels and cannot push power backwards |
| **Phaserunner** (280 g) | the controller: an inverter that turns battery DC into three-phase AC for the motor, and reverses it for regen | "FOC" (field-oriented control) keeps it efficient at part load. **This is the part that behaves like a gearbox** — it decides how much torque to add at any wheel speed, which is how the rider keeps a free cadence |
| **LFP pack, 48 V 10 Ah** (5.3 kg) | lithium iron phosphate, 480 Wh | 2000–3000 cycles vs 400–800 for NMC; chemically stabler. The "I want it to last" choice |
| **Torque sensor, bottom bracket** (250 g) | measures how hard *you* push | makes the motor *multiply* your effort instead of running off a throttle — this is what makes it feel like a bicycle, not a moped |
| **Cycle Analyst CA3** (100 g) | display and brain | speed, watts, Wh/km; sets assist level and regen strength |
| **chain, cassette, derailleur** (existing) | unchanged | your power stays on the 96 % mechanical path |

Total: **10.73 kg, ≈ USD 1290** incremental. Nothing is redundant — one motor,
one controller, one pack. The series hybrid needs a generator **plus** a motor
**plus** two controllers.

---

## §13 Has anyone built this?

**Yes — the parallel hybrid is not exotic. It is one of the two dominant
e-bike architectures in the world.** The chainless version is the rare one.

### Production bikes that are exactly this

**Stromer** (Swiss, since 2009) is the closest match and the best evidence:

- **TDCM direct-drive hub motor** in the rear wheel, up to 500 W / 40 N·m
  [CITED: Stromer Techbook]
- **TMM4 torque sensor** in the right dropout, plus a gyroscopic accelerometer,
  so assist follows rider torque and terrain incline
  [CITED: ElectricBikeReview ST3; stromer-tech.info]
- **Regenerative braking on both brake levers**, with five selectable recoup
  levels; the left lever gives ~1/3 and the right ~2/3 of the set effect
  [CITED: stromer-tech.info]
- **Stromer claims up to 20 % range gain from recuperation** [CITED:
  stromer-tech.info] — higher than the 3–8 % ebikes.ca figure because an
  S-Pedelec is heavier and faster, so there is more kinetic energy to recover.
  Both are consistent with §5's arithmetic: recovery scales with mass and v².
- Stromer's own marketing makes the same argument as this study: the rear-hub
  motor "eliminates energy losses that occur during transmission through the
  crank, sprockets and chain" and "operates independently of gear shifting"
  [CITED: eleway.net, Stromer distributor]

**That is the design you liked, shipping since 2009.** Nothing about it is
experimental.

### Documented DIY builds of exactly the BOM above

Grin's public project gallery contains real customer builds using the precise
combination in §10 — Grin All-Axle (or Max45) + Phaserunner + Cycle Analyst 3 +
T9/T17 torque sensor + 48 V pack, on cargo bikes (Surly Big Dummy long-tail),
RadWagon conversions, and a solar-car project running three All-Axle motors
[CITED: ebikes.ca/gallery.html].

Two data points from that gallery worth having:

- a customer with **over 50 000 km** on an All-Axle with no issues
  [CITED: ebikes.ca All-Axle product page]
- a recumbent-trike rider recovering **~20 %** of energy from regen and
  **8 000 km without changing a brake pad** [CITED: ebikes.ca/resources/learn/regen.html]

### Why you mostly see mid-drives instead

Mid-drive motors (Bosch, Shimano Steps, Brose) dominate the European market
because they drive through the bike's own gearing, which suits steep off-road
climbing and keeps unsprung mass low. **They have essentially no path to
regen** [CITED: ebikes.ca]. So the two architectures are chosen for different
reasons:

| | mid-drive | **DD hub (this design)** |
|---|---|---|
| regen | none | **yes** |
| gearing | uses the bike's cassette | motor has its own speed range |
| unsprung mass | low | ~4 kg in the wheel |
| coast drag | none (freewheel) | 2 W |
| hill climbing | better (torque multiplication) | adequate |
| brake wear | normal | much lower |

You are choosing the DD hub *precisely for* the two properties mid-drives lack:
regen, and independence from the gear train.

### The chainless version: two attempts, both niche

§11 covers these in full. Summary:

- **Mando Footloose** (2015) — series hybrid, automotive alternator, 21.5 kg,
  USD ~3000. Owner verdicts: "very loud (motor and pedaling generator system)";
  "once the battery dies, the bike is rendered completely unrideable."
  Commercially flopped.
- **Schaeffler / Heinzmann Free Drive** (2021, fleet production 2023) — 1:29
  cycloid + alternator, ~250 W system, aimed explicitly at **cargo bikes,
  three- and four-wheelers and velomobiles**, not commuters. Their "5 % less
  efficient than chain" is a vehicle-range figure that only holds where the
  rider supplies ~12 % of traction energy.

**So the honest answer to "has anyone built this": the thing you liked —
chain kept, DD hub with regen — has been in continuous production since 2009
and is one of the two mainstream e-bike architectures. The thing you originally
proposed — no chain — has been built twice, and both times was confined to a
niche (city novelty bike; cargo/velomobile) for exactly the efficiency reasons
this study computes.**

---

## §14 Open items

- **TODO(unverified)** — the regen chain's two hops are ESTIMATES/CITED, not measurements:
  0.86 (Grin All-Axle DD hub *system*) × 0.92 (LFP round trip incl. BMS) = 0.791 per hop.
  65 % (A7) is no longer used by the current figure. A bench measurement with a
  Phaserunner + All-Axle at 5–25 km/h would settle the one-hop number.
- **TODO(unverified)** — 4 % off-cadence metabolic penalty (A8) is an ESTIMATE
  read off the cited cadence literature, not measured on this rider.
- **TODO(unverified)** — the 3 W housekeeping figure is an ESTIMATE for a
  dual-controller build; an actual Phaserunner + CA3 idle draw should be
  measured.
- **TODO(unverified)** — no price/availability check on a PM generator sized
  for 250–400 W at 300 rpm (a direct-drive crank generator). Hub motors are
  cheap; a *low-kv* crank generator at bicycle rpm is the part that does not
  obviously exist off the shelf, and that is a real reason the series hybrid is
  hard to build even if it were efficient.

## §15 What this analysis is not

- Not a frame/structural design, not a mass budget for a specific build.
- Not a legal analysis (EU 250 W / 25 km/h L1e-A limits, throttle vs pedal-assist
  rules differ by jurisdiction and would constrain the controller choice).
- No prototype was built or measured. Every number is a calculation from cited
  component data, not a bench result — the model script is the credibility, and
  it is committed alongside this document.
