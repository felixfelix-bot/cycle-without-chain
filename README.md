# cycle-without-chain

An **independent-cadence, chainless electric drivetrain for a bicycle**: the rider
pedals a generator, a power-electronic bus moves the energy, and hub motors drive
the wheels. Cadence is decoupled from road speed, so the rider can pedal at a
comfortable speed and torque while the electronics do the job a gear train would
otherwise do.

> **STATUS: DESIGN PHASE. NOT SAFE TO ENERGIZE. NOT FABRICATED. NOT ROAD LEGAL.**
> A schematic and a body of analysis exist. There is no PCB, no assembly, no
> energised hardware and no measured prototype performance. Nothing here
> authorises building, powering or riding anything. The safety architecture below
> is an intent backed by calculations, not a qualified design.

## What is being built

**pedals → generator → controlled DC bus → hub motor(s) → wheels.** There is no
chain to the rear wheel.

- **Two motor/generator bridges** driven by DRV8353 smart gate drivers, six 2 mΩ
  low-side shunts, a 29-MOSFET population. Generator and motor are electrically
  independent, which is what makes cadence independent of road speed.
- **Rider effort is a generator load**, not a mechanical coupling. Pedal
  resistance is set electrically; arbitrary cadence and arbitrary power cannot
  both be enforced simultaneously, and the rider/generator balance has to be
  managed.
- **Mechanical friction brakes remain mandatory and are not replaced** by
  electrical braking. Regeneration is only commanded by actual rider brake
  intent — never by a map, a predicted hill or a control loop.
- **Fault shutdown is separate from normal braking**, and must work whether or not
  the microcontroller has booted.

## Storage: LTO pack plus supercapacitor buffer

Chemistry is fixed by the operator: **lithium titanate (LTO) for usable energy, a
supercapacitor bank for power.** The split follows the duty this vehicle actually
has — a short-duration buffer for starts, stops and brief deficits, with no
powered-range target.

- Preferred string to evaluate: **20s Toshiba SCiB 2.9 Ah cells** — 56.0 V max,
  48.0 V nominal, 36.0 V min, ≈139 Wh and ≈3.0 kg cells only.
- **56.0 V sits inside the existing 36–58.4 V bus envelope**, so the bus voltage
  survives the LTO decision. This is a window fit, not a compatibility proof:
  loaded terminal voltage under pulse current, tolerance stack-up, fuse and
  disconnect behaviour, and cold/full charge acceptance all remain open.
- The supercapacitor branch (candidate: Eaton XV3550 20s, ≈1.24 kg, ≈3.9 Wh usable)
  is **not additive by default**. It is justified only if measured braking energy
  demonstrably exceeds LTO charge acceptance, or if cold operation requires it.

Record: [storage decision](docs/design/storage-decision-lto.md).

## What the trade study found

Why this project needs a careful design phase rather than a fast build:

- A waxed derailleur chain is roughly **96%** efficient. A series electrical path
  is not, and every conversion stage compounds.
- A realistic purpose-built PM generator path — generator × rectifier × controller
  × motor ≈ 93% × 97% × 98% × 90% — lands near **80%**, roughly a **20-point
  loss**. An automotive claw-pole alternator at bicycle cadence is far worse
  (≈21–39%) because those machines are built for 1500+ rpm.
- Consequence: at equal wheel output the rider must produce roughly **20% more
  pedal power** than with a chain. That is the price of independent cadence and
  the single number to decide against.
- Cases where a series drivetrain genuinely earns its losses: long-wheelbase cargo
  bikes, velomobiles with many idlers, and layouts where crank speed must be
  decoupled from wheel speed. A simple bicycle with a chain does not need this.

The study, its assumptions and its known accounting errors:
[docs/analysis/chainless-drivetrain.md](docs/analysis/chainless-drivetrain.md). Its
model is retained **unchanged** for audit, including the errors.

**Published correction:** earlier notes claimed Mando Footloose and Schaeffler Free
Drive use automotive claw-pole alternators and deliver ~32% pedals-to-road. No
verified generator-efficiency map exists for either product. Do not reuse that
figure as a product specification. See
[the illustrated guide](docs/analysis/parallel-hybrid-guide.md) for source boundaries.

## Schematics

`hardware/powerboard-reva/` is a Python generator that emits a hierarchical
**KiCad 9** schematic, native netlist, PDF and SVG. Current state:

- **382 components, 218 nets, 1129 connected pins, 51 explicit NCs, 32 pages.**
  These figures were re-measured from a fresh clone at `ae42054`, including what the
  net/NC split actually means: [schematic figure verification](docs/design/schematic-figures-verified.md).
- **45 hardware tests** pass, normally and under `python3 -O`.
- Strict ERC: **10 errors, 0 warnings, exit 5** — unsuppressed and unwaived.
  Enumerated, gate-enforced and treated as open work, not silenced.
- Blocks present: dual DRV8353 bridges; protected-entry *intent* (fuse, shunt
  reverse clamp, 22 Ω resistor precharge, back-to-back TPSI3052-driven MOSFET
  pairs); fast overcurrent comparators; dual FSR brake frontends; rail partition
  (pack→CTRL3V3, bus→SINK12 always-on safety chain, delayed DRIVE12→MCU3V3); and
  a pack-side control supply.
- **Inhibit resistors hold every switch off without firmware** — fitted 0 Ω ties,
  deliberately present, not to be removed.

**What does not exist:** no `.kicad_pcb`, no placement, no routing, no Gerbers, no
priced purchase BOM, no assembled board, no bench measurement of any kind.

## The definition of done

[Open gates register](docs/design/open-gates-register.md) states what is proven and
what is not: **109 gates**, each classified by the kind of evidence that closes it.

- **A — 54:** closable now by calculation, part selection, topology change or
  simulation, without hardware.
- **B — 35:** needs a built board (thermal, ripple, effective capacitance under DC
  bias, start-up sequencing, EMI, hot-plug, pulse/SOA, main-switch conduction).
- **C — 12:** needs an operator decision.
- **D — 8:** resolved, with the commit that closed it.

**The design phase is complete when every A gate is closed and every B and C gate
is explicitly deferred to a named phase with a named owner.** It is not complete
when the board works, because the board has never existed. Finishing the register
claims no electrical safety, no road legality and no manufacturing readiness.

That document is kept honest mechanically: `analysis/gates/register_check.py` fails
if a row has no bucket, no citation or a duplicate ID, or if the bucket counts
disagree with the summary table. It verifies the register is complete and
countable — not that any engineering claim inside it is true.

### Decisions still needed from the operator

Each is a C gate with its consequence recorded in the register:

1. **Architecture** — the study recommends the parallel hybrid; the chainless
   series version is an explicit overrule. Recording it matters because it sets the
   ~20-point rider-power cost and removes pedalling home on a flat battery.
2. **Road class and jurisdiction** — sets lawful power, speed and control topology.
3. **Motor and generator** — pole count, Kv, winding. Bus voltage, shunts, trip
   points, regen ceiling and body-diode energy all follow from it.
4. **Pack and BMS** — exact cell, series count, current limits, source impedance.
5. **Mass and frame** — weighed bicycle mass, frame and fork, permitted mounting.
6. **Duty and route** — descent grades, duration and ambient, which set the braking
   sink rating.
7. **Test authority** — what energy may be tested, in what guarded setup, signed
   off by whom. Every B gate is blocked until this exists.
8. **Independent reviewer** — no review in this corpus can claim cross-family
   independence.

## Quality gates

The board tooling was rebuilt after auditing a previous project where a failed DRC
subprocess reported zero violations — a fail-open check that reads as a clean board.
Those lessons are executable here, not documented intent:

- `tools/gates/native_reports.py` — KiCad export/DRC/ERC runner. A nonzero exit, a
  missing or unparsable report, a stale report, or a zero-object scan is
  **FAILURE**, never success.
- `tools/gates/netlist_parity.py` — exact `(reference, pin, net)` set comparison.
  Counts are never compared, because a gate/source swap keeps the count identical.
- `tools/gates/release_manifest.py` — manufacturing artifact inventory rejecting
  placeholder, truncated or missing outputs, including a requested inner layer that
  produced no file.
- `tools/gates/run_all_gates.py` — one nonzero status if any gate fails; a crashed
  or unwired gate reports **NOT RUN**, never green.

**198 gate tests pass**, normally and under `python3 -O`, with negative controls
proving each gate can actually fail.

## Use cases under investigation

These are **hypotheses to test, not market validation**. The series concept trades
conversion losses, added mass and control complexity for cadence independent of
road speed, controllable pedal resistance and chassis freedom. This is research,
not a certified product.

- **Cargo and urban logistics:** a comfortable cadence through stops and changing
  road speeds. Payload and hill capability remain bounded by motor torque,
  available power, storage state and thermal limits — not guaranteed.
- **Adaptive cycling and rehabilitation research:** adjustable pedal resistance
  could support experiments with different rider abilities. Suitability requires
  individual assessment; no medical safety or treatment claims.
- **Low-maintenance, clean commuters:** removing the wheel-drive chain could reduce
  chain grime and servicing, but does not guarantee lower total maintenance. The
  crank-to-generator gearing remains moving machinery and needs a guard.
- **Recumbent, velomobile and alternative-chassis designers:** electrical routing
  could replace long wheel-drive chains and free up layout, subject to generator
  packaging, structural loads, mass and heat rejection.
- **Stationary exercise and pedal charging:** controlled resistance could convert
  rider effort into stored energy — not free energy. Requires a safe, stable stand
  and wheel-propulsion inhibit. At full storage, useful charging stops; continued
  pedalling under load needs a safe energy sink and cooling.

### Balance assistance — research option, not a feature

An actively gimballed flywheel might assist stopping, starting and mounting for
riders with balance limitations. This is an accessibility hypothesis, not
demonstrated safety or fall prevention, and it is compared against mechanically
supported cycles including tricycles.

Energy scales with rotor speed squared; angular momentum only linearly. Discharging
the rotor reduces balancing authority. Two gimbal axes do not eliminate torque
coupling, travel limits, singularities or power-failure risk. The suggested 8–12 kg
mass and 30% range penalty are unverified examples, not specifications. Never claim
recovery from ice, potholes, collisions or arbitrary disturbances, and never claim
the rider cannot tip over. High-speed rotor safety needs specialist mechanical
engineering, not electrical PCB checks.

[Quantified feasibility study](docs/design/gyro-balance-feasibility.md) — calculations
and a source-backed shortlist, not a purchase BOM. No gyro hardware is selected, and
mechanical brakes and support are not replaced.

## Repository map

- `hardware/powerboard-reva/` — schematic generator, tests, committed netlist/PDF/SVG
  exports. The generator is the source of truth, not the exports.
- `docs/design/` — per-block milestone and review documents, the
  [open gates register](docs/design/open-gates-register.md), the
  [LTO storage decision](docs/design/storage-decision-lto.md), and the gyro study.
- `docs/analysis/` — drivetrain trade study, historical model, diagrams.
- `analysis/` — executable models with tests: precharge, braking, storage, gyro,
  navigation, FSR, register consistency.
- `tools/gates/` — the fail-closed release gates.
- `docs/evaluation/`, `docs/research/`, `docs/PLAN-parallel-hybrid.md` — **historical**
  concept and sourcing research from the parallel-hybrid baseline. Not validated
  purchasing evidence, and not the current implementation plan.

## Reproduce

```sh
# drivetrain trade study (stdlib only)
python3 docs/analysis/chainless_drivetrain_model.py

# schematic, netlist, PDF and SVG
cd hardware/powerboard-reva && python3 generate_schematic.py

# hardware test suite, both modes
cd hardware/powerboard-reva && python3 -m unittest discover -s tests
cd hardware/powerboard-reva && python3 -O -m unittest discover -s tests

# fail-closed release gates
python3 -m pytest tests/gates -q

# open-gates register consistency
python3 analysis/gates/register_check.py docs/design/open-gates-register.md
```

Passing tests prove the models and the generated connectivity behave as specified.
They do not prove the circuit is electrically safe, fabricable or rideable.

## License

Model and analysis code MIT; documentation separately licensed. See `LICENSE`.
