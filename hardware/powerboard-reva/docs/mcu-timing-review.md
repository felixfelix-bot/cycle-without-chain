# Dual FOC pin allocation and timing review

**Research candidate, not implemented or bench-proven.** 2026-11-10. Select STM32G474VET6 (LQFP100) for this pin-budget proposal rather than assume the concept's LQFP64 fits. See `mcu-pin-allocation.csv`: 32 distinct GPIOs/physical pins, including twelve timer outputs, six current inputs, two break inputs, SPI and six Hall inputs. This is a functional allocation, NOT a complete MCU schematic: supply/decoupling, exposed analog references, SWD, reset/boot, clocks, driver fault/enable, watchdog heartbeat, bus voltage/current and temperature allocations still need completion.

## Primary evidence and retrieval qualification

ST **DS12288 Rev 5**, Table 12 physical pin/additional function table pp59–70 and Table 13 AF table pp73–77, downloaded as the original ST-authored PDF from a [mirror](https://kennedy-engr.github.io/Documents/g474xx_series_datasheet.pdf) and extracted using `pdftotext -layout`. Official [ST URL](https://www.st.com/resource/en/datasheet/stm32g474re.pdf) timed out; the .ve and ST China alternatives failed HTTP/2. This is primary-authored content hosted by a third party, **not verification against latest Rev 6**. PDF SHA256 `3322273ce08c4e50ff83409881d8624478d193b6adc4860155e368ad893b699d`. Scratch evidence: `$TMPDIR/g474.pdf`, `$TMPDIR/g474.txt` (temporary, not release artifacts). Recheck current ST revision and errata before freeze.

ST's [HAL ADC extension header](https://github.com/STMicroelectronics/stm32g4xx-hal-driver/blob/master/Inc/stm32g4xx_hal_adc_ex.h) was downloaded from ST's repository; it defines `ADC_EXTERNALTRIGINJEC_T1_CC4`, `T8_CC4`, `T1_TRGO2` and `T8_TRGO2`. These corroborate trigger availability, **not a completed register configuration**. The exact RM0440 timer interconnect/ADC sequencing and errata audit remains a blocker; no fabricated trigger register values are supplied.

## Selected mux strategy

- Generator: TIM1 CH1/1N, CH2/2N, CH3/3N on PE8–PE13 **AF2**.
- Hub: TIM8 CH1/2/3 on PC6/7/8 and CH1N/2N/3N on PA7/PB0/PB1, all **AF4**. Do not copy the common AF3 TIM8 assignment from a different STM32 family.
- Shared latched fault fans out to PE15 TIM1_BKIN AF2 and PD2 TIM8_BKIN AF4, and separately to both drivers' hardwired ENABLE path. Firmware break configuration is additional protection, not the sole inhibit.
- SPI1: PA5 SCK / PA6 MISO / PB5 MOSI AF5; GPIO CS per driver. PA7 is already PWM and cannot be SPI MOSI. Driver register reads/configuration do not run at PWM rate.
- Hall inputs: PD8–PD10 generator and PD11–PD13 hub, GPIO/EXTI with external signal conditioning. These use six distinct EXTI line numbers. Timestamp edges with a free-running timebase; process motor angle asynchronously, not by assuming one Hall update per current interrupt. Hall supply voltage, cable protection, open-wire detection and input filters remain circuit work.

## Explicit sampling proposal — sequential within each bridge

ADC1 injected ranks 1/2/3 = PA0 IN1, PA1 IN2, PA2 IN3 (generator). ADC2 injected ranks 1/2/3 = PC0 IN6, PC1 IN7, PC2 IN8 (hub). Configure **independent ADC mode**, not ADC1/2 dual simultaneous mode: each bridge requires its own trigger placement. All six phase signals have dedicated inputs, but the three phases on a bridge are sequential, NOT three simultaneous sample-and-holds.

Proposed initial operating point: two 20 kHz centre-aligned timers on the same 170 MHz timer clock, PSC=0 and ARR=4250 (50 us up/down period). Establish a hardware master/slave start/reset relationship; do not start two software counters and call them synchronized. Exact TIM1-to-TIM8 ITR selection and repetition-counter/update behavior must be checked against RM0440 and captured on a scope before claiming synchronization. Start aligned; interleaving is a later measured option.

Reserve CH4 internally on each timer for current sampling: TIM1_CC4 → ADC1 injected, TIM8_CC4 → ADC2 injected. No CH4 GPIO is consumed. Firmware must select exactly one intended event per full centre-aligned cycle; centre-aligned compare events can otherwise occur on both count directions. TRGO2/OC4REF edge gating is an alternative if required; routing/edge selection is NOT yet register-verified.

For an illustrative 42.5 MHz ADC clock, 24.5-cycle sample time and 12.5-cycle 12-bit conversion time, each rank consumes 37 cycles ≈0.871 us; three ranks consume ≈2.612 us, with ≈0.871 us aperture displacement between adjacent phases. These are arithmetic design assumptions, **not a validated ADC clock/source-impedance choice**. Verify allowable ADC clock/boost configuration and acquisition settling in DS12288/RM0440 for actual VDDA and input RC. Longer acquisition may be necessary.

Position the sequence within an all-low-side-conducting window:

`usable_window >= deadtime + switch/CSA settling + ADC trigger latency + 3*t_rank + end_guard`.

At high modulation this window disappears. Enforce a minimum zero-vector window/duty limit or implement reviewed two-shunt reconstruction with sector-dependent sampling; never consume invalid samples as real current. Quantify sequential-sample error against di/dt; if unacceptable, revise ADC allocation to concurrent converters and prove trigger routing rather than pretending the current allocation is simultaneous. DRV8353 CSA settling and RC acquisition budget, ADC regular/injected arbitration and overrun handling remain open.

Latch injected results on end-of-sequence, run each motor's current controller, then preload duties for a deterministic later PWM update. Both FOC loops must finish inside the selected deadline with worst-case interrupt/DMA load. No CPU benchmark exists. Provisionally put slower bus voltage/current/temperature measurements in scheduled regular conversions outside injected windows; prove they cannot delay injected acquisition. Hall edge events, SPI diagnostics and a proposed 1 kHz supervisory loop have independent cadence and lower priority than safety/current acquisition; external watchdog servicing must reflect successful control health rather than an unconditional periodic interrupt.

## Release blockers

1. Complete all MCU power/reset/debug and auxiliary signal pin assignments and cross-check against schematic/netlist; current CSV is not a full 100-pin wiring table.
2. Verify latest datasheet/errata, RM0440 ITR/JEXTSEL/edge/register configuration and ADC electrical limits; implement firmware and compile it.
3. Scope both six-PWM groups, deadtime, break polarity/latency, one trigger per cycle, sample placement, aperture skew and duty update latency under worst-case load.
4. Inject brake, MCU halt, stuck PWM, driver fault and invalid sensor conditions; demonstrate hardware inhibit and deliberate re-arm without relying on interrupt execution.
5. Complete independent protection in `safety-review.md`; no fabrication or riding approval follows from this pin feasibility review.
