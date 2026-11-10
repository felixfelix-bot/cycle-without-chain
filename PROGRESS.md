# Progress — pedal-by-wire powerboard

**Current state: design phase. Schematic and analysis only.** No PCB, routing,
fabrication, purchase or riding. Every design document is stamped *not safe to
energize*.

- [Open-gates register](docs/design/open-gates-register.md) is the authoritative
  list of what is proven and what is open: 109 gates (A 54, B 35, C 12, D 8).
- Storage chemistry frozen by the operator: **LTO** for energy, supercapacitor
  branch for power; 20s Toshiba SCiB direction —
  [decision](docs/design/storage-decision-lto.md). BMS part still open.
- Powerboard Rev A exists as generated KiCad schematic only —
  [`hardware/powerboard-reva/`](hardware/powerboard-reva/README.md).
- Braking is rider-requested only and supplemental to mechanical brakes, with a
  bounded dump-resistor target —
  [envelope](docs/design/downhill-braking-envelope.md).
- Navigation (GNSS + IMU + wheel speed, EKF) is specified for logging first and has
  no authority over propulsion or braking —
  [interface](docs/design/navigation-interface.md).
- Gyro balance is a separate research workstream, not part of this build —
  [feasibility](docs/design/gyro-balance-feasibility.md).

## Next

The remaining work is blocked on operator inputs and measurement, not on writing:

1. Weigh the bicycle; confirm frame material, dropout spacing, wheel circumference
   and tyre size (ARCH-03).
2. Select generator and wheel motor with datasheet maps at human power levels
   (ARCH-04).
3. Decide the bus maximum once the LTO pack ceiling is confirmed (CX-02).
4. Select the BMS and characterise charge acceptance, including cold (ARCH-06,
   STO-03).
5. Name a descent or duty cycle so braking and thermal bounds stop being assumptions
   (ARCH-05).
6. State permitted test energy and test sign-off before any B gate can start
   (ARCH-07).

A green check verifies documents and arithmetic, not safety.
