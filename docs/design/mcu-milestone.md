# STM32G474 MCU circuit milestone — UNSAFE DRAFT

2026-11-10. Base 445b340, branch pr/mcu-completion. Not safe to energize, fabricate or ride. No PCB routing.

## Implemented circuit

Actual U17 STM32G474VET6 LQFP100 replaces MCU PWM/SPI/ADC boundary connectors. Four new pages implement five VDD decouplers plus VBAT bypass and bulk, VDDA/VREF 0R links with 100n/1u bypass, NRST pullup/cap/button, BOOT0 pulldown, SWD target-reference header, HSI16/PLL internal-oscillator option with oscillator pins explicitly NC. VREFBUF must stay disabled; boot/reset option bytes need firmware/provisioning review.

TIM1 PE8–13 and TIM8 PC6–8/PA7/PB0/PB1 connect twelve real PWM driver inputs. Shared SPI1 PA5/PA6/PB5 connects both drivers with separate chip selects. Six CSA outputs reach ADC1/2 via 100R/1nF candidate filters. Six conditioned 3V3-only Hall inputs and optional PB6/PB7 TIM4 quadrature interface have pullups/series resistors/caps. Cable ESD and power-off injection are not qualified. Brake status is sensed via 10k series/100k pulldown/1nF; it does not replace the hardware brake path.

PE2/3/4 connect ARM/WDI/RESET_REQUEST to existing default-low hardware circuitry. TIMER_BREAK_OK reaches both real timer BKIN pins (PE15/PD2); firmware must configure active-low break. Separate hardwired driver ENABLE gating remains unchanged. This is connectivity, not proof of fault latency or functional control.

## Source evidence

[Recovered manufacturer-authored evidence](../../hardware/powerboard-reva/docs/mcu-source-evidence.md) includes original DS12288 Rev5 and RM0440 Rev7 mirror URLs, PDF SHA256 hashes, physical pin/AF/ADC and trigger table excerpts. Vendor KiCad symbol is used for CAD representation, not sole pin evidence. Latest revisions and errata still need audit.

RM evidence verifies TIM8 ITR0=TIM1_TRGO and injected JEXTSEL CC4/TRGO2 choices. It does NOT prove implemented timer synchronization, one conversion sequence per PWM cycle, ADC settling, WCET or deadline behavior. The timing review now qualifies 42.5MHz against VDDA limits and includes trigger latency.

## Executed verification

Canonical `python3 export_artifacts.py` generated 15 pages, 199 components, 642 connected manifest endpoints, 138 connected nets plus 45 explicit NC singleton nets. PDF, 15 SVG pages, BOM, pin map and netlist regenerated. Read-only checker validates exact manifests plus fixed NC identities/markers; topology tests independently demand physical pin endpoints and ADC/Hall/filter/hardware-inhibit connections. Corrupted endpoints and filter returns are rejected.

Normal and optimized full unittest discovery each pass 18 tests. Genuine RED logs: `exports/mcu-tests-red.txt` and `mcu-checker-red.txt`; GREEN logs: `mcu-tests-green.txt` and `mcu-tests-optimized.txt` under hardware/powerboard-reva. This is consistency/topology validation, not electrical qualification; no coverage percentage claimed.

Native `kicad-cli sch erc --exit-code-violations --format json` returns **5**, with **4 errors / 0 warnings**: U1.24 VREF external logic rail, U1.25 AGND/PGND, U3.1 IN/DC_LINK and U17.37 VDDA behind passive link. No PWR_FLAG, waiver or hidden severity flag was introduced. Checker success recognizes an incomplete-state signature and is NOT release approval.

## Still open / review handoff

Firmware is absent: no build, deadtime configuration, driver OCP/CSA readback, watchdog health logic or ADC acquisition demonstrated. Bus-voltage/current/thermal sensing still incomplete. Fast independent overcurrent trip, protected power entry, source isolation/precharge/discharge, supply sequencing/backfeed, auxiliary-loss bus clamp, sink energy/thermal design and storage/BMS charge acceptance remain release blockers. Passive values and many footprints/order codes are candidates, not procurement approval.

Dedicated PCB reviewer/consultant and metadata-verified cross-family cold review remain owed; parent owns review and merge. No spatial or independent electrical approval claimed. Root page enlarged to A1 to fit all hierarchy boxes; full visual legibility review remains open.

Operator mass envelope: conservatively 120kg payload (rider plus luggage) PLUS bicycle until clarified. Human-powered system with a small buffer, not an electrical-range requirement. Neither changes this MCU wiring milestone.
