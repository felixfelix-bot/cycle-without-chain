# cycle-without-chain

Trade study and reproducible model for a **chainless / series-hybrid bicycle
drivetrain** (pedal → generator → energy buffer → hub motor), evaluated against
a conventional chain drive on measured component efficiencies.

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

Two production systems are reconciled in §11: Mando Footloose (2015) and
Schaeffler/Heinzmann Free Drive (2021, fleet production 2023). Both use
automotive claw-pole alternators, giving ~40–45 % at the pedal generator and
**~32 % pedals-to-road**. Schaeffler's widely-quoted "5 % less efficient than a
chain" is shown to be a *vehicle range* figure that only holds at a rider
energy share of ~12 % — not a drivetrain efficiency, and not reproducible on a
light commuter.

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
