# Powerboard status report

Where the design actually stands. The authoritative record is the
[open-gates register](docs/design/open-gates-register.md); the architecture is in
the [README](README.md).

## What exists

- Bounded [concept and candidate BOM](docs/evaluation/custom-powerboard-concept.md),
  block diagram and reproducible arithmetic model — architecture and sizing
  screening only, historical to the parallel-hybrid baseline.
- Generated KiCad 9 schematic for Powerboard Rev A under
  [`hardware/powerboard-reva/`](hardware/powerboard-reva/README.md): dual DRV8353
  bridges, six 2 mΩ low-side shunts, protected-entry intent, fast overcurrent
  comparators, dual FSR brake frontends, rail partition and a pack-side control
  supply. **No `.kicad_pcb`, no placement, no routing, no Gerbers.**
- Executable models with tests under `analysis/`: precharge, braking, storage, gyro,
  navigation, FSR, brake intent and register consistency.

## Findings that constrain the design

- The 80% crank-to-wheel target is a **goal, not a measurement**. At 250 W crank it
  allows only 50 W of aggregate loss across gears, both machines, converters and
  auxiliaries.
- Generator selection at human power levels is the hardest open problem. No verified
  generator efficiency map has been obtained at a ~300 rpm shaft speed, and an
  automotive claw-pole alternator at bicycle cadence is far worse.
- The DRV8353 is a 75 V *supply* part with a 100 V *drain* rating — the headline
  voltage is not an operating limit.
- Gate-off does not stop a PM machine rectifying through MOSFET body diodes, so a
  spinning machine can charge the bus with the pack open. A sustained-energy sink is
  a protection requirement, not a firmware behaviour, and the current design's sink
  is not yet independent of its own auxiliary supply (PROT-01).
- Zero-speed balance support would need very high precession authority; the gyro
  branch stays separate and unpromised.

## Validation performed

Models and their unit tests pass; the open-gates register passes its consistency
check; schematic exports are checked for structure; the fail-closed release gates
have negative controls proving each can actually fail. **No hardware test has been
performed, nothing has been energized, and no trial is authorised.** Passing checks
means the documents, arithmetic and tooling are organised — not that the machine is
safe, legal or buildable.
