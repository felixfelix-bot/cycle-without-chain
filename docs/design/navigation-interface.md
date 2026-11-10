# Optional navigation interface — bounded design, not fabrication approval

2026-11-10. Base `d07bdb2292a5cddeebec529e0ec4a59fdd61bbd7` (github/master).
Core safety completion takes precedence. This adjunct changes no schematic, PCB,
README or firmware. First deployment is **logging only**, disabled by default.
Operator approval includes designing GNSS + six-axis IMU + wheel-speed EKF with
biases and uncertainty; it does not authorize road automation or completed EKF claims.

## Architecture and selected candidates

Prefer a separate navigation daughterboard/supervisor, away from switching bridges
and hot components, with its own bounded logging queues. Sensor silicon shortlist:
**LSM6DSOXTR** (SPI + INT1 data-ready), **MAX-M10S-00B** (UART + optional TIMEPULSE),
optional **BMP390** (SPI; not required for initial logging). The higher-range
LSM6DSO32TR is an upgrade candidate only if measured shocks clip the base IMU.
See [component evidence](navigation-component-evidence.md) and
[candidate CSV](navigation-bom-candidates.csv) for exact sourcing limitations.
ST product HTML confirms the candidate, but the primary ST PDF was inaccessible;
INT1 routing register, SPI mode/limits and VDDIO electrical conditions must be
verified from the current datasheet before hardware release. No unknown spec is a pass.
Only one price was retrieved; this is not a complete procurement total.

A remote supervisor can own sensors, storage and EKF; main MCU publishes a bounded,
read-only wheel-speed/time/status stream. It must not receive torque commands from
navigation. Supervisor MCU, connector, regulator and protocol are deliberately not
selected here. Long off-board SPI is not assumed reliable: keep SPI local to the
sensor host, use a reviewed physical transport for the mainboard/supervisor link.
If direct main-MCU acquisition is chosen instead, the following pins are candidates,
not an instruction to the concurrent hardware worker to wire them.

## Provisional reservation against actual RevA

Read `hardware/powerboard-reva/mcu_circuit.py`, `docs/mcu-pin-allocation.csv`,
`docs/mcu-timing-review.md`, `pin-net-map.csv` and exported `powerboard-reva.net`.
The older functional CSV is incomplete: MCU_ARM, WDI, reset, SWD, encoder and power
are also occupied. FSR branch inspected read-only: PE5/pin4 becomes
FSR_SAMPLE_ENABLE; PC3/PA3 are renamed FSR ADCs, not available pins. These are
reserved even before merge. Future bus/thermal inputs may still supersede navigation.

| Candidate net | GPIO / LQFP100 pin | Function | Status |
|---|---|---|---|
| NAV_SCK | PB13 / 52 | SPI2 AF5 | currently NC |
| NAV_MISO | PB14 / 53 | SPI2 AF5 | currently NC |
| NAV_MOSI | PB15 / 54 | SPI2 AF5 | currently NC |
| IMU_CS_N | PB12 / 51 | GPIO, external inactive pull-up | currently NC |
| IMU_DRDY | PD3 / 85 | EXTI3 | currently NC; no Hall EXTI collision |
| GNSS_RX at receiver | PC10 / 79 | USART3_TX AF7 | currently NC |
| GNSS_TX at receiver | PC11 / 80 | USART3_RX AF7 | currently NC |
| optional PPS | PE6 / 5 | EXTI6, software timestamp | currently NC |
| optional BARO_CS_N | PD4 / 86 | GPIO | currently NC |

**PPS caveat:** EXTI6 is free (PC6 PWM does not use EXTI), unlike PC9/EXTI9
which conflicts with GEN_HALL_2/PD9. PE6 interrupt-entry timestamps have jitter;
no precision hardware capture claim. For precision PPS, prefer supervisor-local
timer capture after a separate mux/timer review. IMU EXTI3 does not
conflict with analog PA3/PC3 because analog inputs do not use EXTI.

Pin/AF provenance: ST DS12288 Rev5 Tables 12/13 pp59–77, original ST-authored PDF
retrieved from https://kennedy-engr.github.io/Documents/g474xx_series_datasheet.pdf
(SHA256 recorded in existing `docs/mcu-timing-review.md`). Recheck latest revision,
DMA/DMAMUX and peripheral clock allocation during integration. No TIM1/TIM8 control
resources or encoder TIM4 are allocated to navigation. Hardware owner must remove
NC markers and approve routing; these reservations are not present in the schematic.
Run `python3 analysis/navigation/check.py` against regenerated merged exports;
checks detect occupied physical pins and pending PE5, not EXTI/AF correctness or PCB wiring.

### Alternate shared SPI1 (not preferred)

Existing PA5/27 SCK, PA6/28 MISO, PB5/92 MOSI are shared by both DRV8353 drivers;
PA7 is PWM, never an available MOSI. Keep separate PB12 IMU CS and PD4 barometer CS.
Every inactive slave must tri-state MISO; external CS pulls and power-off IO isolation
must prevent an unpowered daughterboard holding driver SPI. Check each device's
CPOL/CPHA, frequency and turnaround; change bus mode only with all CS high. No SPI
from FOC ISR. Driver fault protection must remain hardwired and independent of SPI.

Assumed 16-byte IMU burst (command + 12 axis bytes + overhead), 416 Hz, 4 MHz:
32 us wire time / 2.404 ms sample period = 1.3312% bus occupancy. Illustrative two
2-byte driver transactions each at 100 Hz add 0.08%; this is a workload assumption,
not measured firmware. One 256-byte transfer would block 512 us, despite low average
utilization. Bound every transaction and queue, prioritize diagnostics, prohibit SD
or arbitrary FIFO drains on this bus; prove total blocking = longest in-flight
transaction + arbitration + mode-switch/CS guards under worst-case DMA/IRQ load.
These figures alone cannot prove the 50 us dual-FOC deadlines. Separate SPI2 removes
bus arbitration, NOT CPU, memory-bus or DMA contention. Separate supervisor avoids
silently assigning navigation real-time budget to the FOC MCU.

## Physical/power interface

All proposed IO is 3.3 V; never connect RS-232 levels or assume 5 V tolerance. Use a
reviewed current-limited switched supply, local decoupling, cable ESD, strain relief,
keyed locking connector and default-disabled pins to avoid back-powering. The main
LOGIC3V3_EXT rail has no verified spare-current entitlement. Measure inrush, rail
ripple/droop and conducted/radiated emissions with both bridges switching before
sharing it. An added regulator/supervisor is outside the sensor-only budget below.

MAX-M10S needs an external GNSS antenna and controlled-impedance RF feed; choose
antenna/ground plane per u-blox integration guidance, with clear sky view. Keep RF
away from motor phase cables, buck inductors, clocks and GNSS UART edges. Place RF
protection/filtering at the entry; active antenna requires separately budgeted bias
and short protection. Do not assume VCC_RF is an antenna bias supply. Passive patch
is the initial cost/power candidate, not an already selected antenna MPN. Test C/N0,
fix dropouts and reacquisition with motor current swept, rather than specifying an
unsupported universal separation distance.

Rigidly attach IMU to known vehicle-body axes; record measured rotation/lever arms.
Keep it off flexible harnesses, fork vibration and regulator heat. Characterize
mount resonances and clipping; soft isolation can create new resonances/delay.
Log raw temperature and calibrated scale/bias; use anti-alias filtering validated
against actual vibration spectra. No magnetometer reliance near motors or steel.
Seal electronics against rain/splash/condensation with drainage, breathable membrane
where needed and corrosion protection. Do not coat a barometer port; protect it with
a characterized hydrophobic vent away from dynamic pressure and heat. No IP rating
is claimed without enclosure testing. GNSS radome must not shield its antenna.

## Power and one-hour energy — explicitly limited model

Exact primary source tables/conditions are in component evidence. GNSS currents are
specified at **3.0 V**; using them unchanged at **3.3 V** below is a planning proxy,
not a measured or guaranteed value. IMU 0.55 mA is a manufacturer headline typical,
not a verified worst-case at our sample rate. Barometer values apply only at 1 Hz
ultra-low-power ×1/×1, not faster updates.

| Load / condition | Current mA | 3.3 V proxy mW | one-hour Wh |
|---|---:|---:|---:|
| MAX-M10S default tracking VCC + V_IO, typical | 11.8 | 38.94 | 0.03894 |
| MAX-M10S acquisition VCC + V_IO, typical | 13.8 | 45.54 | 0.04554 |
| LSM6DSOX combo high-performance headline | 0.55 | 1.815 | 0.001815 |
| BMP390 1 Hz typical (optional) | 0.0032 | 0.01056 | 0.00001056 |
| BMP390 same mode maximum | 0.0074 | 0.02442 | 0.00002442 |
| tracking + IMU + optional barometer typical proxy | 12.3532 | 40.76556 | 0.04076556 |
| acquisition + IMU + barometer typical proxy | 14.3532 | 47.36556 | 0.04736556 |

GNSS startup supply capability **100 mA** is a transient requirement, not continuous
tracking current or duration-qualified energy. IMU maximum remains unverified; no
all-load worst-case total exists. A provisional 150 mA sensor-rail engineering
allowance would be 0.495 W / 0.495 Wh if sustained, NOT a sourced maximum and NOT
approval of the existing regulator. Add antenna, storage, supervisor, leakage and
conversion losses. At assumed 85% conversion, typical proxy battery energy is
0.04076556/0.85 = 0.0479595 Wh/h before those missing loads. Measure off leakage too.

## Acquisition, logging and resource contract

Assume IMU 416 Hz six-axis, GNSS 10 Hz only after verifying selected constellation
update capability, wheel summaries 50 Hz. Timestamp IMU at DRDY/captured FIFO sample
time, not completion of a delayed read. Detect FIFO overrun, missing sequence numbers
and sensor saturation. GNSS logs receiver measurement epoch, arrival timestamp,
fix flags, position/velocity uncertainty and PPS lock status. Configure bounded
binary messages rather than unbounded NMEA chatter; handle checksum failure and reset.

Assumed records: IMU 32 bytes ×416 + GNSS 100 ×10 + wheel 16 ×50 = **15,112 B/s**,
54.4032 MB/hour decimal, before file framing/metadata. Budget 20 kB/s sustained and
72 MB/hour as a planning allowance. GNSS 1,000 B/s on 115200 8N1 consumes 8.68% UART;
that is not the entire sensor log stream. A combined supervisor stream at 15,112 B/s
cannot fit 115200 8N1; use a separately verified higher baud/link or supervisor-local
storage. A 64 KiB queue lasts about 4.34 s at payload rate, then drop oldest/newest
by declared policy and record loss; never block FOC waiting for storage.

At 170 MHz and assumed 20 kHz dual FOC there are 8,500 CPU cycles per 50 us period
for **all** work, not per motor. No navigation cycle budget is claimed. EKF state
(16 float32 nominal values) + 15×15 float32 covariance alone use 964 bytes; working
matrices, stacks, replay history and drivers dominate beyond that. A 64 KiB log
buffer alone is significant. Measure worst-case cycles/stack/high-water RAM, DMA
contention and ISR latency with both FOC loops, Hall edges, serial burst, sensor
FIFO backlog and storage stall. If deadlines cannot be proved, keep supervisor
architecture; don't lower safety priority or hide load behind average CPU percentage.

## Implementable estimator contract (next stage, not delivered firmware)

Use local ENU world frame at a persisted WGS84 origin; body frame x forward, y left,
z up. Convert receiver geodetic coordinates to ECEF then ENU; do not mix MSL and
ellipsoid height. Quaternion q_WB rotates body vectors into world, scalar first,
unit norm. State x = [p_W(3), v_W(3), q_WB(4), b_g(3), b_a(3)] (16 nominal values),
15-dimensional error state [δp, δv, δθ, δb_g, δb_a] with full covariance P. Specify
right-multiplicative attitude error in implementation and test its Jacobians.

Propagate with calibrated gyro ω-b_g and specific force f-b_a: p_dot=v,
v_dot=R(q)(f-b_a)+[0,0,-g], q_dot=0.5 q⊗[0,ω-b_g]; biases random walks. Use measured
sample dt, calibrated sensor-noise densities, discrete process-noise covariance,
quaternion normalization, covariance symmetry and PSD checks. Gravity and Earth
model approximation limits must be documented for operating distances/durations.

GNSS updates position and velocity at the **measurement epoch**, including antenna
lever arm R*l and rotational velocity R*(ω×l); wheel speed predicts body-forward
velocity at the wheel reference with lever arm correction. Wheel circumference,
Hall pole counts, direction and pulse-to-speed uncertainty are calibrated inputs,
not GNSS-derived replacements for local speed safety. No unconditional zero lateral
or vertical velocity constraint: cornering, bumps and bicycle lean violate naive
nonholonomic assumptions. Standstill updates require independently validated motion
classification; yaw and biases may be unobservable at standstill. No magnetometer
means absolute yaw is weak/unobservable without motion/excitation; report it so.

All inputs carry monotonic acquisition time, sequence, unit/frame, quality and time
uncertainty; retain raw arrival times separately. PPS aligns host counter to receiver
time only when valid, with rollover/restart/discontinuity handling. UART arrival is
not GNSS epoch. Estimate fixed delays and clock drift; permit bounded delayed updates
via state-history rewind and IMU replay, or explicitly reject stale observations
when history is unavailable. Never apply an old fix to the present as if synchronous.

Innovation ν=z-h(x), S=HPHᵀ+R, NIS=νᵀS⁻¹ν. Gate using declared χ² threshold and
measurement degrees of freedom (e.g. 99%: 3D=11.345, 1D=6.635), in addition to fix,
accuracy, timestamp and physical-plausibility gates. Do not treat multipath-reported
accuracy as infallible. Log rejects and residuals. Inflate wheel R or exclude wheel
updates under acceleration/braking discrepancy or slip evidence; reject stale/missing
pulses and avoid making GNSS the safety wheel-speed source. Wheel-slip thresholds
and noise calibration need replay/bench evidence, not arbitrary fixed constants.

Modes: UNINITIALIZED → ALIGNED_LOGGING → GNSS_DEGRADED/IMU_DEGRADED/TIME_INVALID.
GNSS outage propagates covariance and drift; wheel helps distance but does not bound
heading/position indefinitely. IMU fault cannot be hidden by GNSS interpolation;
disable fused output validity and retain independent raw logs. Reacquisition is gated,
with explicit reset/reinitialization records instead of unreported jumps. Output
position/velocity/attitude, covariance, age, source-health bits, reject counters and
validity separately. There is no binary 'accurate' flag or promised metre accuracy.

Next bounded milestone: offline reference error-state EKF and replay schema, with
**synthetic truth fixtures explicitly labeled synthetic**, no claim of road evidence.
Test stationary, known turns, bias ramps, wheel slip, GNSS outliers/outages, delayed
packets, frame/units errors and timestamp resets. Monte Carlo NEES uses the observable
error-state subspace and consistent attitude error; NIS uses innovation dimension.
Apply confidence bounds over independent trials with correct degrees of freedom;
correlated/time-gated residuals invalidate naive independence tests. Report coverage,
RMSE, divergence, covariance PSD and rejection rates, then replay real logs without
claiming NEES when independent truth is absent. Validate analytical Jacobians against
finite differences before embedded port. No EKF implementation is included here.

## Safety and privacy boundaries

Navigation failure, resets, corrupt logs, stalled SPI or missing GNSS must not affect
braking, independent local speed sensing, or gyro balance. This navigation IMU is
**not a qualified balance-system sensor**; balance redundancy, independent sensing,
failure detection and safety validation are separate requirements. No shared safety
credit follows from using a six-axis sensor twice.

GNSS cannot predict terrain without a map or learned route profile; unknown turns,
route deviations, gradients, changed road surfaces and outages invalidate forecasts.
Any future profile display is advisory with uncertainty, never a route-forecast
 torque command. No unsolicited regenerative braking: rider intent remains required,
except the independently specified emergency overvoltage protection path. Navigation
must not control that path either.

Keep route history offline and user-controlled: logging opt-in, visible indication,
physical/software disable, configurable retention and explicit delete/export. No cloud
sync by default. Stop acquisition and discard queued records on disable; delete
indexes and exports as well as tracks. Ordinary flash deletion is not guaranteed
secure erasure; encrypted storage with key destruction is a later privacy option.
Avoid exact positions in public bug reports without explicit consent.

## Verification / integration gates

`python3 -m unittest discover -s analysis/navigation -v` and
`python3 analysis/navigation/check.py`. Five RED failures were observed before checker
implementation (missing implementation assertions). First GREEN attempt exposed a
hand-calculated expected log rate typo (14,680); corrected to 416×32+10×100+50×16 =
15,112, with no production formula change. These are arithmetic/pin tests, not hardware
or estimator qualification. Pending gates: merge FSR and regenerate exports; resolve
PPS capture; fetch complete ST datasheet; source antenna/passives/connector and actual
current maxima; independent design review; EMC/power/timing bench evidence. No balloon
component provenance is claimed: none was copied from balloon-fresh.
