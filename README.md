# cycle-without-chain

Trade study and reproducible model for a **chainless / series-hybrid bicycle
drivetrain** (pedal → generator → energy buffer → hub motor), evaluated against
a conventional chain drive on measured component efficiencies.

## Illustrated parallel-hybrid design

[Parts, efficiency, limitations and existing bicycles](docs/analysis/parallel-hybrid-guide.md)

![Parallel hybrid](docs/analysis/parallel-hybrid-explainer.png)

![Efficiency examples](docs/analysis/parallel-hybrid-blend.png)

**Correction:** a retained chain still couples cadence to road speed through the
selected gear. Motor assistance does not replace shifting or provide pedal-by-wire.

## Current evaluation plan

[Evaluate independent pedalling / pedal-by-wire](docs/pedal-by-wire-evaluation-plan.md):
requirements, evidence audit, generator selection, fair storage comparisons,
duty-cycle modelling, bench tests and decision criteria. The chain-and-hub design
is a comparison baseline, not a substitute for independent cadence.

## Question

Would a bicycle that generates electricity at the pedals (using a car or
motorbike alternator) and drives the wheels with hub motors — buffering energy
in supercapacitors — beat a chain? Should the buffer be supercapacitors,
batteries, or both? And how does a battery-less version bootstrap its
generator?

## Answer in one line

The drivetrain loses ~35 percentage points of the rider's power, and even with
every stage at its datasheet peak it is still ~20 points worse than a waxed
derailleur. Supercapacitors are a power buffer, not an energy store (19× the
mass of LFP for the same energy). LTO is the honest answer to "I want the wear
profile of a capacitor."

## What is in here

- `docs/analysis/chainless-drivetrain.md` — the full study: assumptions,
  cited efficiencies, buffer sizing, the battery-less bootstrap question,
  failure modes, sensitivity analysis, and a BOM.
- `docs/analysis/chainless_drivetrain_model.py` — stdlib-only model that
  re-derives every number in the document.

**Evidence correction for §11:** no verified crank-generator efficiency map
was found for Mando Footloose or Schaeffler Free Drive. Earlier claims that both
use automotive claw-pole alternators and deliver ~32% pedals-to-road are not
established. Do not use them as measured product specifications. See the
[illustrated guide](docs/analysis/parallel-hybrid-guide.md) for source boundaries.

## Sections of the study

- §0 answer first — §1 assumptions — §2 vehicle power — §3 series vs chain
- §4 cadence — §5 buffer sizing — §6 is a buffer needed — §7 bootstrap
- §8 sensitivity — §9 failure modes — §10 recommendation
- §11 the two production systems (Mando, Schaeffler) reconciled
- **§12 the recommended build, worked numbers, parts explained**
- **§13 has anyone built this? (Stromer, Grin builds, mid-drive comparison)**
- §14 open items — §15 scope limits

## Reproduce

```sh
python3 docs/analysis/chainless_drivetrain_model.py
```

stdlib only, no dependencies. Every figure in the document is that script's
printed output.
