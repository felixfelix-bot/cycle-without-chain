# cycle-without-chain

A **pedal-by-wire bicycle**: the rider's legs drive a generator at the crank, the
electrical output drives a hub motor, and there is no chain to the wheel. The point
is not to beat a chain on efficiency — it is to make **pedal cadence independent of
road speed**, with electronically controlled pedal resistance.

**Status: schematic and analysis only. No PCB, no routing, no fabrication, no
purchase, no riding.** Every design document is stamped *not safe to energize*.
The [open-gates register](docs/design/open-gates-register.md) is the single place
that states what is proven and what is not.

## What is being built

```
cranks → removable gear → clamped PM generator → active rectifier
                                                        │
                                            protected shared DC bus (36–58.4 V)
                                                        │            │
                                              hub inverter/motor   storage branch
                                                        │            │
                                                     rear wheel   LTO pack
                                                                  (+ optional
                                                                   supercap buffer)
```

- **Independent cadence.** A controller sets generator current, which sets pedal
  resistance, independently of wheel speed. Stationary pedalling is possible.
  Cadence and power cannot both be forced — the rider supplies what the load draws.
- **Generator at the crank**, driven by a small gear from a bolt-on crank ring.
  Reversible: no drilling, welding or grinding of the donor frame.
- **Two custom three-phase bridges on one board** — generator active rectifier and
  hub inverter — sharing a protected DC link. Not an off-the-shelf controller.
- **Storage is a short buffer**, not a powered-range battery: starts, stops and
  brief power deficits. Chemistry frozen as **LTO**, with an optional supercapacitor
  branch for power peaks — see [the storage decision](docs/design/storage-decision-lto.md).
- **Rider-requested braking only.** Electrical braking follows brake-lever intent
  via force-sensitive pads plus an independent activation signal; it never brakes
  because a map, a slope or an energy target says so. It supplements the mechanical
  brakes, which remain mandatory and independent.
- **Resistor dump** for kinetic energy when storage is full or refuses charge.
- **Navigation** (GNSS + IMU + wheel speed, fused by an extended Kalman filter) is
  for energy budgeting and route logging only, starting in logging-only mode. It
  has no authority over propulsion or braking.

**Not selected:** generator model, wheel motor, BMS part, pack build, gimbal
actuators. See [machine candidates](docs/research/machines/candidates.md) for what
has been screened and what is missing.

## Accepted targets and their status

| Target | Value | Status |
|---|---|---|
| Crank-to-wheel efficiency at cruise | **80%** (150 W in → 120 W at wheel) | Accepted by operator; **never measured** |
| Rider + luggage mass | **120 kg** (bicycle and hardware extra) | Operator-confirmed; total mass unweighed |
| Bus voltage | 36–58.4 V, 100 V devices | Provisional; the selected pack may lower the ceiling |
| Electrical braking | Supplemental, thermally limited | Bench target 100 W first, 300 W max average |
| Frame modification | None | Design rule; mounting not yet assessed |

The 80% figure is a design goal that costs roughly 20% more pedal power than a
97%-efficient chain would. It is not a demonstrated result, and generator efficiency
maps at human power levels are the main missing evidence.

## Repository map

| Area | Where |
|---|---|
| **What is proven vs open** | [open-gates register](docs/design/open-gates-register.md) — start here |
| Powerboard schematic (generative KiCad) | [`hardware/powerboard-reva/`](hardware/powerboard-reva/README.md) |
| Storage decision and analysis | [storage decision](docs/design/storage-decision-lto.md), [short-buffer analysis](docs/design/short-buffer-storage.md) |
| Braking envelope and dump sizing | [downhill braking envelope](docs/design/downhill-braking-envelope.md) |
| Brake-intent (FSR) sensing | [FSR frontend evaluation](docs/design/fsr-frontend-evaluation.md) |
| Navigation and sensor fusion | [navigation interface](docs/design/navigation-interface.md) |
| Gyro balance (separate research option) | [gyro feasibility](docs/design/gyro-balance-feasibility.md) |
| Machine and controller candidates | [research index](docs/research/README.md) |
| Evaluation plan and staging | [pedal-by-wire evaluation plan](docs/pedal-by-wire-evaluation-plan.md) |
| PCB release gates | [PCB quality gates](docs/design/pcb-quality-gates.md), [`tools/gates/`](tools/gates/README.md) |

## Potential audiences

Hypotheses to test, not market validation. What is being offered is **independent
cadence and controllable resistance**, not efficiency.

- **Cargo and urban logistics:** a comfortable cadence through stops and changing
  road speeds, without long chain runs and idlers. Bounded by motor torque,
  available power, storage state and thermal limits.
- **Adaptive cycling and rehabilitation research:** adjustable pedal resistance for
  different abilities. Requires individual assessment; no medical claims.
- **Low-maintenance commuters:** no wheel-drive chain to clean or adjust — but the
  crank gear is still moving machinery, and electronics add their own servicing.
- **Recumbent, velomobile and alternative chassis:** electrical routing replaces
  long chain paths and frees layout, subject to generator packaging, structural
  loads and heat rejection.
- **Stationary exercise and pedal charging:** controlled resistance and stored
  energy. Needs a stable stand and propulsion inhibit; at full storage, charging
  stops and load must be reduced or dumped.
- **Balance assistance (research only):** an actively gimballed flywheel as a
  low-speed aid for riders with balance limitations. Not part of the current build;
  no fall-prevention claim, and a tricycle is the honest comparison. See
  [gyro feasibility](docs/design/gyro-balance-feasibility.md).

## Historical material — do not use for decisions

This repository began as a trade study asking whether a chainless drivetrain could
*beat* a chain. That question was answered — it cannot, on efficiency — and the
project moved on to the architecture above, chosen for different reasons.

The older documents are **retained for audit only**:

- [`docs/analysis/chainless-drivetrain.md`](docs/analysis/chainless-drivetrain.md)
  and its model: historical efficiency scenarios, including known energy-accounting
  errors and unsupported product claims about Mando Footloose and Schaeffler Free
  Drive. No verified crank-generator efficiency map was found for either, so
  earlier figures attributed to them are not product facts.
- [`archive/`](archive/): the earlier separate repository, preserved rather than
  deleted.
- [`docs/analysis/parallel-hybrid-guide.md`](docs/analysis/parallel-hybrid-guide.md)
  and the parallel-hybrid diagrams: a **comparison baseline**. A retained chain
  still couples cadence to road speed through the selected gear, so it does not
  provide what this project exists to provide. Those figures compare a chain-coupled
  bike to a serial drivetrain; they do not describe the bicycle being built here.

Where a historical document and a current design document disagree, **the current
design documents and the open-gates register win**.

## Reproduce the checks

```sh
python3 analysis/gates/register_check.py docs/design/open-gates-register.md
python3 -m unittest discover -s analysis/gates/tests -v
python3 analysis/storage/model.py
python3 -m unittest discover -s analysis/storage -v
python3 analysis/gyro/model.py
```

These check that documents are well-formed and that the arithmetic models run and
pass their physics checks. **They do not prove the design is safe, legal or
buildable.** A green run means the paperwork is organised, not that a bicycle works.

The powerboard schematic is generated from Python, not hand-drawn KiCad; see
[`hardware/powerboard-reva/README.md`](hardware/powerboard-reva/README.md) for the
current component and ERC counts and the generator commands.

## Licence

MIT — see [`LICENSE`](LICENSE).
