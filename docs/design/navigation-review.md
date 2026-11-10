# Optional navigation independent review

2026-11-10. Design/model review only, not hardware or EKF qualification.

## Integration and disposition

Integration branch starts at GitHub master `aebd795` (including gyro review),
then merges navigation `2890447f49bab541166becc29ca4ff4dd68d5b98` without
replacing concurrent files. Master advanced during review to `c1216a6`; it was
merged without conflicts, preserving both FSR and precharge reviews.
FSR `44d3d9fc` was initially not an ancestor; its actual exported netlist and MCU
source were read separately, then the merged master export passed the same
five tests normally and optimized plus the checker. No schematic,
README, precharge, FSR or gyro files are changed by this review.

Optional daughterboard logging remains the cost/safety-first architecture;
DSOX + MAX-M10S with passive antenna, barometer DNP is a candidate baseline,
not a demonstrated cheapest quote. Supervisor, storage, antenna and support
BOM remain unselected. Navigation must not block core bicycle safety work.

## Independent pin/source audit

Re-downloaded ST-authored DS12288 Rev5 from the mirror linked in the interface;
SHA256 `3322273ce08c4e50ff83409881d8624478d193b6adc4860155e368ad893b699d`
matches existing evidence. Tables 12/13 confirm:

| Reserved pin | LQFP100 | Function checked | FSR export status |
|---|---:|---|---|
| PB13 | 52 | SPI2_SCK AF5 | unconnected |
| PB14 | 53 | SPI2_MISO AF5 | unconnected |
| PB15 | 54 | SPI2_MOSI AF5 | unconnected |
| PB12 | 51 | GPIO chip select, no AF | unconnected |
| PD3 | 85 | GPIO interrupt EXTI3, no peripheral AF | unconnected |
| PC10 | 79 | USART3_TX AF7 | unconnected |
| PC11 | 80 | USART3_RX AF7 | unconnected |
| PE6 | 5 | GPIO interrupt EXTI6, no capture claim | unconnected |
| PD4 | 86 | GPIO chip select, no AF | unconnected |

The checker read 61 connected U17 pins in the actual FSR export and returned
zero reserved-pin conflicts. It found PE5/pin4=FSR_SAMPLE_ENABLE,
PC3/pin18=LEFT_FSR_ADC and PA3/pin25=RIGHT_FSR_ADC. Hall inputs PD8–PD13
consume EXTI8–13; PD9/pin56=GEN_HALL_2 excludes PC9/EXTI9 as PPS.
PD3/EXTI3 and PE6/EXTI6 do not duplicate those lines. Analog PA3/PC3 do not
consume EXTI3; TIM8 PWM PC6 and encoder TIM4 PB6 do not consume EXTI6.
This validates the stated reservation, not actual firmware EXTI routing:
firmware, DMA assignments and current ST revision/errata remain release gates.
No reservation conflict was found; no invented conflict regression is claimed.

## Arithmetic, power boundary and resource findings

- 12.3532 mA × 3.3 V = 40.76556 mW; one hour = 0.04076556 Wh.
  This is a sensor-only typical proxy, not subsystem maximum or battery draw.
  Acquisition proxy is 47.36556 mW. The 100 mA GNSS startup supply requirement
  has no duration here and cannot establish one-hour consumption.
- Material clarification: sourced GNSS current is at **1 Hz**, whereas the
  logging scenario assumes **10 Hz**. The interface now expressly forbids
  applying that proxy to 10 Hz without rate/constellation/current verification.
  Antenna amplifier/bias, regulator losses, supervisor, log storage and support
  loads are absent. Passive antenna means no amplifier draw, not a complete RF
  design. VCC_RF output capability is not the receiver's consumption budget.
- 416×32 + 10×100 + 50×16 = 15,112 B/s = 54.4032 decimal MB/hour.
  115200 8N1 carries 11,520 B/s: GNSS-only 1,000 B/s uses 8.68056%; the
  combined stream cannot fit. 20 kB/s / 72 MB/hour remain planning allowances.
  Added UART-capacity regression assertions to the existing five-test suite.
- 64 KiB / 15,112 = 4.3367 s, not sustained storage. The interface now names
  the MCU's 128 KiB SRAM partition (80+16+32 KiB), CCM DMA alias restriction,
  linker/high-water requirements, and 512 KiB flash capacity limit (~34.69 s
  even with no firmware). No storage device or retention guarantee exists.
- 16-byte SPI transfer at 4 MHz = 32 us. 964 bytes covers nominal state and
  covariance only; it excludes EKF workspace/history and control firmware.

## Actual execution

Before changes: all five navigation unittests passed normally and with `-O`.
After review fixes and added assertions:

- `python3 -m unittest discover -s analysis/navigation -v`: 5 tests, OK.
- `python3 -O -m unittest discover -s analysis/navigation -v`: 5 tests, OK.
- `python3 analysis/navigation/check.py`: exit 0, conflicts `[]`, proxy
  `0.04076555999999999` Wh, burst `32.0` us, logging `15112` B/s.
- Separate `netlist_pins()` / `conflicts()` invocation on the `git show
  44d3d9fc:hardware/powerboard-reva/exports/powerboard-reva.net` output:
  61 populated pins, conflicts `[]`.

These are executed arithmetic/netlist checks, not physical tests. No EKF code
was added: the approved error-state EKF remains an implementation contract.
Braking, local speed sensing and balance safety remain independent of GNSS.

## Pending, explicitly not qualified

The detailed LSM6DSOX datasheet was not retrieved by the feature work and has
not been retrieved by this review. Product-page current/IO/DRDY statements
remain unqualified electrical evidence; no release credit is added. MAX-M10S
and BMP390 source-table claims remain the feature's recorded evidence, not
newly re-fetched PDFs in this review. Full BOM/quotes, current maxima at the
chosen rates, RF/EMC, rail transients, connector/isolation, memory/timing tests,
physical storage and EKF replay/bench validation are still open. No keys,
hook bypasses, procurement or physical tests were used.
