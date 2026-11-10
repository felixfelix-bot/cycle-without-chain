# MCU integration review — UNSAFE partial design

2026-11-10. Reviewed MCU milestone `82d7b1bb15f1f4ce07e710b6eb342b7f3243991e` onto fetched GitHub master `445b340`. This accepts a bounded schematic/connectivity milestone, **not electrical approval, fabrication, energization, procurement or riding authorization**. No PCB/routing or new circuits added.

## Isolation and provenance

Fresh worktree: `~/worktrees/cycle-mcu-review`, branch `integration/mcu-reviewed`. The source `~/worktrees/cycle-mcu-completion` was dirty only at `hardware/powerboard-reva/exports/restart-old-held-reset-spice.log`: transient reference-value line changed from `4.53445e-03` to `4.64465e-03`. That edit was excluded, left untouched, and not discarded or stashed. Integration uses the committed milestone, not that working directory.

Read the actual exported netlist, MCU implementation, milestone and manufacturer source text. Rehashed complete source PDFs: DS12288 Rev5 `3322273ce08c4e50ff83409881d8624478d193b6adc4860155e368ad893b699d`; RM0440 Rev7 `1288859b194f3c8417195cfb5749f1112b9e760dfb183ddf5ae36452cec9133f`. URLs and recoverable excerpts are in [source evidence](../../hardware/powerboard-reva/docs/mcu-source-evidence.md). These older revisions do not discharge a current errata/revision audit.

## Electrical crosscheck (bounded static findings)

No material MCU wiring defect was found in the inspected scope; no wiring correction or invented RED test is claimed. The fixed-pin topology tests alone are insufficient source evidence, so physical identities and functions were compared to DS12288 Rev5 Figure 9 and Tables 12/13.

| Actual U17 physical pins | Source-supported assignment / result |
|---|---|
| 39/40, 41/42, 43/44 | PE8/9, PE10/11, PE12/13: TIM1 CH1N/1, CH2N/2, CH3N/3, AF2 (T12 p62; T13 p77). Low outputs reach GEN INLA/B/C; high outputs INHA/B/C. |
| 65/66/67; 29/32/33 | PC6/7/8 TIM8 CH1/2/3; PA7/PB0/PB1 TIM8 CH1N/2N/3N, AF4 (T12 pp60–65; T13 pp73–75). Correct HUB high/complementary pairs. |
| 20/21/22; 15/16/17 | PA0/1 ADC12_IN1/2, PA2 ADC1_IN3; PC0/1/2 ADC12_IN6/7/8 (T12 pp59–60). Six 100R/1nF filter paths reach the intended channels. Dedicated pins do not imply simultaneous three-phase sampling. |
| 46, 84 | PE15 TIM1_BKIN AF2 and PD2 TIM8_BKIN AF4 (T12 pp63/69; T13 pp76–77). Both receive TIMER_BREAK_OK. |
| 27/28/92; 62/45 | PA5/PA6/PB5 SPI1 SCK/MISO/MOSI AF5; PD15/PE14 separate GPIO chip selects. Shared MISO 10k and both CS pullups return to LOGIC3V3_EXT, not 5V. |
| 55–60; 93/94 | PD8–13 Hall GPIOs; PB6/7 TIM4 CH1/2 AF2 encoder option. 3V3-only interfaces remain unqualified for cable ESD and power-off injection. |
| 24/49/64/75/100, 6 | All five VDDs and VBAT at 3V3; six 100n decouplers plus 4.7u bulk present. |
| 23/48/63/74/99, 35; 37/36 | VSS/VSSA at PGND; VDDA/VREF+ separately linked to 3V3 by populated 0R and each bypassed with 100n + 1u. DS Fig16 and §3.11.1 support topology; physical decoupling placement and analog return remain unproved. |
| 14, 95; 76/77 | PG10-NRST 10k pullup/100n/reset header; PB8-BOOT0 10k pulldown; PA13/14 SWD. Retain NRST function and audit boot option bytes; physical BOOT0 does not override arbitrary nSWBOOT0 programming (RM flash option registers). |

### Break polarity and inhibit contract

Fresh KiCad netlist confirms U16 inputs 1=HEALTHY, 3=PERMIT, 6=ARM_CLEAN and output 4=TIMER_BREAK_OK. Thus **high means healthy/armed/permitted; low must break**, not high. U17 pins 46/84 and the two driver ENABLE resistor branches share that signal; MCU break is not the sole hardwired inhibit.

RM0440 Rev7 TIMx_BDTR (p1204) defines BKP=0 as active-low; TIMx_AF1 defines BKINP=0 as non-inverting and BKINE=1 to enable the external alternate-function input. Required firmware contract: AF2/AF4 on the respective pins, BKE=1, BKP=0, BKINP=0, BKINE=1; qualify input mode/filter latency and lock configuration. Do not enable bidirectional break output against the external logic driver. Deadtime, complementary output polarity, idle states, MOE/automatic re-enable policy and actual fault response are **not implemented or measured**. Net continuity is not timer safety configuration.

VREFBUF must remain in external-reference/high-impedance mode, not drive the hard-fed 3V3 VREF+ rail (RM VREFBUF CSR). VDDA/VREF supply tracking, startup/reset, back-power and partial-power conditions still require qualification. Shared open-drain MISO with 10k requires a bounded clock/capacitance budget: passive rise to 0.7 VDD is approximately 1.204 RC; no fast-SPI readiness is claimed.

## Reproduced verification

Copied the committed board into fresh isolated scratch `cycle-mcu-review-run/board`; ran `python3 export_artifacts.py`, then normal and optimized unittest discovery and strict native ERC. Regenerated drawings/netlist never overwrote the dirty source or committed historical logs.

- KiCad CLI **9.0.9**, export runner exit **0**: PDF plus **15 SVG pages**, **199 components, 138 connected nets, 642 connected endpoints, 45 explicit NC endpoints**. Fresh versus committed netlist endpoint mapping equals for all **687** endpoints.
- `python3 -m unittest discover -s tests -v`: **18/18 pass**, 7.786s.
- `python3 -O -m unittest discover -s tests -v`: **18/18 pass**, 9.907s.
- `kicad-cli sch erc --exit-code-violations --format json ...`: exit **5**, **4 errors / 0 warnings**. Exact undriven-power identities remain U1.24 VREF, U1.25 AGND, U3.1 IN, U17.37 VDDA. No PWR_FLAG, exemption, warning downgrade or false clean claim.
- Committed fresh logs: [exports/mcu-integration-review](../../hardware/powerboard-reva/exports/mcu-integration-review/). Export success recognizes partial-design consistency, not release readiness. PDF/SVG export does not establish visual legibility or layout quality.

## Reviewer qualification

The integration reviewer and a separate read-only supply/SPI reviewer expose only runtime model alias **`tier/delegation`**, provider custom; actual underlying model/family is unknown. Separate contexts are **not evidence of cross-family independence**. Metadata-verified cross-family electrical approval and dedicated PCB/spatial review remain **PENDING**. This document must not be cited as satisfying that approval gate.

## Concrete next circuit blockers — SOON, still unsafe

1. **Fast independent overcurrent trip (next bounded circuit milestone):** select the shunt/CSA or separate sense path and comparator, calculate worst-case trip threshold/hysteresis and propagation budget, wire fail-safe fault into the existing latch/inhibit without MCU dependence. Add failing exported-topology and fault-injection tests before wiring, then prove threshold/latency corners. Integrated DRV OCP and ADC samples are not that proof.
2. **Protected power entry:** fuse and reverse/source isolation, contactor/precharge/discharge with interrupt ratings and startup/fault states. Resolve DC_LINK source/ERC boundary from a real reviewed circuit, not a flag.
3. **Supply-loss energy sink:** specify a bus-powered autonomous clamp/sink that remains effective after AUX/logic loss and while PM machines charge through body diodes. Prove resistor/MOSFET pulse energy, thermal cutout and repeated braking at the conservative 120kg payload PLUS bicycle envelope.
4. **Storage/BMS acceptance:** bound bus voltage and allowable charge current, full/disconnected/cold storage behavior and what absorbs energy when BMS opens. A small buffer is not unlimited regenerative acceptance.
5. **Analog and sequencing qualification:** current-sense gain/range, RC acquisition settling, PWM sample windows, bus/current/thermal sensing, VDDA/VREF accuracy/tracking, cable injection/ESD and brownout/backfeed. Implement the logic supply boundary and close its ERC only with defensible source/return semantics.
6. **Firmware and review gate:** timer/ADC trigger startup, one sample sequence per cycle, deadtime, driver configuration/readback, watchdog health and latched recovery tests; current datasheet/errata audit; actual named cross-family cold reviewer. None authorizes layout until electrical gates close.

Integration publication is owned by the manager: fetch latest master, preserve concurrent commits, merge this review branch without force and verify the remote default-branch SHA. An integrated UNSAFE draft is the intended milestone, not a claimed finished controller.
