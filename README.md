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

Read: [`docs/analysis/chainless-drivetrain.md`](docs/analysis/chainless-drivetrain.md)

## Reproduce

```sh
python3 docs/analysis/chainless_drivetrain_model.py
```

stdlib only, no dependencies. Every figure in the document is that script's
printed output.
