# Progress — pedal-by-wire powerboard

**Current state: schematic and analysis only.** No PCB, routing, fabrication,
purchase or riding. Every design document is stamped *not safe to energize*.

- [Open-gates register](docs/design/open-gates-register.md) is the authoritative
  list of what is proven and what remains open.
- Storage chemistry frozen: **LTO**, 20s direction, with an optional supercapacitor
  branch — [decision](docs/design/storage-decision-lto.md). BMS part still open.
- Powerboard Rev A exists as generated KiCad schematic only; see
  [`hardware/powerboard-reva/README.md`](hardware/powerboard-reva/README.md) for
  current component and ERC counts.
- Braking is rider-requested only, supplemental to mechanical brakes, with a
  bounded dump-resistor target — [envelope](docs/design/downhill-braking-envelope.md).
- Navigation (GNSS + IMU + wheel speed, EKF) is specified for logging first and has
  no control authority — [interface](docs/design/navigation-interface.md).
- Gyro balance is a separate research workstream, not part of this build —
  [feasibility](docs/design/gyro-balance-feasibility.md).

## Next

Blocked on operator inputs and evidence, not on further writing:

1. Weigh the bicycle; confirm frame material, dropout spacing, wheel circumference
   and tyre size (ARCH-03).
2. Select generator and wheel motor, with datasheet maps at human power levels
   (ARCH-04).
3. Decide the bus maximum once the LTO ceiling is confirmed (CX-02).
4. Select BMS and characterise charge acceptance, including cold (ARCH-06, STO-03).
5. Name a descent or duty cycle so braking and thermal bounds stop being
   assumptions (ARCH-05).

A green check verifies documents and arithmetic, not safety.
