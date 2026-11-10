# Powerboard concept report

Summary of where the design stands. The authoritative record is the
[open-gates register](docs/design/open-gates-register.md); the architecture is in
the [README](README.md) and the [evaluation plan](docs/pedal-by-wire-evaluation-plan.md).

## What exists

- Bounded [concept and candidate BOM](docs/evaluation/custom-powerboard-concept.md),
  block diagram and reproducible arithmetic model — architecture and sizing
  screening only.
- Generated KiCad 9 schematic for Powerboard Rev A under
  [`hardware/powerboard-reva/`](hardware/powerboard-reva/README.md): two DRV8353
  bridges, six 2 mΩ phase-current shunts plus one bus shunt, a twelve-comparator
  fast-overcurrent path, protected-entry intent and an autonomous
  protection chain. **No `.kicad_pcb`, no placement, no routing, no fabrication data.**
- Analysis models with tests: `analysis/storage`, `analysis/precharge`,
  `analysis/braking`, `analysis/brake_intent`, `analysis/fsr`, `analysis/gyro`,
  `analysis/navigation`, `analysis/gates`.

## Findings that constrain the design

- The 80% crank-to-wheel target is a **goal, not a measurement**; at 250 W crank it
  allows only 50 W of aggregate loss across gears, both machines, converters and
  auxiliaries.
- Generator selection at human power levels is the hardest open problem. No verified
  efficiency map has been obtained for a candidate at a ~300 rpm shaft speed.
- The DRV8353 is a 75 V *supply* part with a 100 V *drain* rating — the headline
  voltage is not an operating limit.
- Gate-off does not stop a PM machine rectifying through MOSFET body diodes, so a
  spinning machine can charge the bus with the pack open. A sustained-energy sink is
  a protection requirement, not a firmware behaviour.
- Zero-speed balance support would need a very high precession authority: both
  wheels are rigidly journalled, so gyroscopic reaction appears as frame load rather
  than as a steering force that could restore uprightness. This is why the gyro
  branch stays separate and unpromised.

## Validation performed

Arithmetic models run and their unit tests pass; the open-gates register passes its
consistency check; schematic exports are checked for structure. **No hardware test
has been performed, nothing has been energized, and no outdoor trial is authorised.**
Passing checks means the documents and arithmetic are organised — not that the
machine is safe, legal or buildable.
