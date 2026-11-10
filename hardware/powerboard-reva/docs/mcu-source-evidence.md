# MCU source evidence — STM32G474VET6 / LQFP100

Recovered 2026-11-10. **Source evidence only; not firmware, schematic sign-off, latest-revision validation, or bench proof.** Existing allocation and timing review were read but not edited.

## Provenance and recovery limits

Local-first searches of prior cycle worktrees found only `docs/research/controller/stm32g474re-proxy.txt` copies (ST product-page text, not a datasheet). No named G474/RM0440 PDF was found in manager scratch. Broader cache filename search failed; that is not proof of cache absence. The existing timing review supplied the datasheet mirror. Both complete PDFs below were successfully downloaded and converted with `pdftotext -layout`; page references below are printed PDF pages (also matching page-array indices). No repeated broken ST HTTP2 download attempts were made.

* DS12288 **Rev 5, October 2020**, 236 pages, ST-authored content on Kennedy Engineering mirror.[1]
* RM0440 **Rev 7, February 2022**, 2124 pages, ST-authored content on Czech Technical University mirror.[2]
* Search discovers RM0440 Rev 9 (March 2025) at `https://www.st.com/resource/en/reference_manual/dm00355726.pdf`; its full body was **not** used/validated here. These older recovered sources must be checked against current datasheet/manual/errata before release.
* `web_extract` also saved `/home/c08r4d0r/.hermes/profiles/manager/cache/web/kennedy-engr.github.io-e3fb77e85e.md`, but that extraction contained only 50,000 characters ending before pin tables. The complete downloaded PDF/layout text, not this partial extraction, supports the tables below.

### Complete local source artifacts

* `/home/c08r4d0r/.hermes/profiles/manager/cache/scratch/g474-source.pdf` — SHA256 `3322273ce08c4e50ff83409881d8624478d193b6adc4860155e368ad893b699d`
* `/home/c08r4d0r/.hermes/profiles/manager/cache/scratch/rm0440-source.pdf` — SHA256 `1288859b194f3c8417195cfb5749f1112b9e760dfb183ddf5ae36452cec9133f`

Layout text: `/home/c08r4d0r/.hermes/profiles/manager/cache/scratch/g474-source.txt` and `/home/c08r4d0r/.hermes/profiles/manager/cache/scratch/rm0440-source.txt`. Scratch is transient; this document embeds the usable table excerpts below.

## Pin / alternate-function / ADC allocation check

All **32 existing CSV rows** agree with DS12288 Rev 5 Table 12 physical LQFP100 pin numbers. Selected peripheral mappings agree with Table 13 AF columns and Table 12 additional ADC functions. No pin/AF correction was found. `ADC12_INn` means availability on ADC1 and ADC2, not a requirement to operate in dual mode. PA2 is specifically ADC1_IN3, unlike PA0/PA1 and PC0–PC2, which have ADC12 connectivity.[1]

| Signal | GPIO | LQFP100 pin | Selected function | AF | DS12288 Rev 5 evidence |
|---|---|---:|---|---|---|
| GEN_U_L | PE8 | 39 | TIM1_CH1N | 2 | T12 p62; T13 p77 |
| GEN_U_H | PE9 | 40 | TIM1_CH1 | 2 | T12 p62; T13 p77 |
| GEN_V_L | PE10 | 41 | TIM1_CH2N | 2 | T12 p62; T13 p77 |
| GEN_V_H | PE11 | 42 | TIM1_CH2 | 2 | T12 p62; T13 p77 |
| GEN_W_L | PE12 | 43 | TIM1_CH3N | 2 | T12 p62; T13 p77 |
| GEN_W_H | PE13 | 44 | TIM1_CH3 | 2 | T12 p62; T13 p77 |
| HUB_U_H | PC6 | 65 | TIM8_CH1 | 4 | T12 p65; T13 p75 |
| HUB_V_H | PC7 | 66 | TIM8_CH2 | 4 | T12 p65; T13 p75 |
| HUB_W_H | PC8 | 67 | TIM8_CH3 | 4 | T12 p65; T13 p75 |
| HUB_U_L | PA7 | 29 | TIM8_CH1N | 4 | T12 p60; T13 p73 |
| HUB_V_L | PB0 | 32 | TIM8_CH2N | 4 | T12 p61; T13 p74 |
| HUB_W_L | PB1 | 33 | TIM8_CH3N | 4 | T12 p61; T13 p74 |
| GEN_IU | PA0 | 20 | ADC1_IN1 | analog | T12 p59 |
| GEN_IV | PA1 | 21 | ADC1_IN2 | analog | T12 p59 |
| GEN_IW | PA2 | 22 | ADC1_IN3 | analog | T12 p60 |
| HUB_IU | PC0 | 15 | ADC2_IN6 | analog | T12 p59 |
| HUB_IV | PC1 | 16 | ADC2_IN7 | analog | T12 p59 |
| HUB_IW | PC2 | 17 | ADC2_IN8 | analog | T12 p59 |
| FAULT_TO_TIM1 | PE15 | 46 | TIM1_BKIN | 2 | T12 p63; T13 p77 |
| FAULT_TO_TIM8 | PD2 | 84 | TIM8_BKIN | 4 | T12 p69; T13 p76 |
| DRV_SCK | PA5 | 27 | SPI1_SCK | 5 | T12 p60; T13 p73 |
| DRV_MISO | PA6 | 28 | SPI1_MISO | 5 | T12 p60; T13 p73 |
| DRV_MOSI | PB5 | 92 | SPI1_MOSI | 5 | T12 p70; T13 p74 |
| GEN_CS_N | PD15 | 62 | GPIO | none | T12 p64 |
| HUB_CS_N | PE14 | 45 | GPIO | none | T12 p63 |
| BRAKE_SENSE | PD14 | 61 | GPIO | none | T12 p64 |
| GEN_HALL_1 | PD8 | 55 | GPIO/EXTI8 | none | T12 p64 |
| GEN_HALL_2 | PD9 | 56 | GPIO/EXTI9 | none | T12 p64 |
| GEN_HALL_3 | PD10 | 57 | GPIO/EXTI10 | none | T12 p64 |
| HUB_HALL_1 | PD11 | 58 | GPIO/EXTI11 | none | T12 p64 |
| HUB_HALL_2 | PD12 | 59 | GPIO/EXTI12 | none | T12 p64 |
| HUB_HALL_3 | PD13 | 60 | GPIO/EXTI13 | none | T12 p64 |

### Dedicated current inputs (Table 12 pp59–60)

| GPIO / pin | Datasheet additional function | Proposed ADC/rank |
|---|---|---|
| PA0 / 20 | ADC12_IN1 | ADC1 rank 1 channel 1 |
| PA1 / 21 | ADC12_IN2 | ADC1 rank 2 channel 2 |
| PA2 / 22 | ADC1_IN3 | ADC1 rank 3 channel 3 |
| PC0 / 15 | ADC12_IN6 | ADC2 rank 1 channel 6 |
| PC1 / 16 | ADC12_IN7 | ADC2 rank 2 channel 7 |
| PC2 / 17 | ADC12_IN8 | ADC2 rank 3 channel 8 |

This remains sequential sampling within each bridge; dedicated pins are not three simultaneous sample-and-holds.[2]

## RM0440 recovered register evidence

### Injected trigger selection — ADC1 **and** ADC2

Table 164 pp624–625 supplies these values; they are **unshifted JEXTSEL field values**, not complete register words. ADC_JSQR bits 6:2 hold JEXTSEL, bits 8:7 hold JEXTEN. JL bits 1:0 = `10` for three conversions (p706). Configure only when JADSTART=0 as required by that register description.[2]

| Source | JEXTSEL[4:0] | Decimal |
|---|---|---:|
| TIM1_TRGO | 00000 | 0 |
| TIM1_CC4 | 00001 | 1 |
| TIM8_CC4 | 00111 | 7 |
| TIM1_TRGO2 | 01000 | 8 |
| TIM8_TRGO | 01001 | 9 |
| TIM8_TRGO2 | 01010 | 10 |

JEXTEN `01` = rising, `10` = falling, `11` = both edges. `00` disables external triggering; its software-trigger behavior also depends on JQDIS. JADSTART must arm injected conversions; triggers arriving during an ongoing conversion are ignored (p622). JAUTO must be clear for externally triggered injection (p627); disable injected discontinuous mode if one trigger is intended to convert the whole sequence (p629).[2]

### TIM1/TIM8 synchronization and one-event-per-period distinction

Table 252 p1081: **TIM8 ITR0 = TIM1_TRGO**. Conversely TIM1 ITR5 = TIM8_TRGO. This closes the source-routing uncertainty, not the full startup/reset/repetition configuration.[2]

TIMx_CR2 MMS2[3:0] = `0111` selects **tim_oc4refc** as TRGO2 (p1171). `1010` generates pulses on **both rising and falling edges** of tim_oc4refc and is not a once-per-period substitute. A proposed route is CH4 PWM reference -> MMS2=0111 -> ADC JEXTSEL 8 (TIM1) / 10 (TIM8) -> one selected JEXTEN edge. This is an engineering proposal based on the retrieved routing, not implemented timing proof. Verify actual OC4REFC waveform, nondegenerate CCR4 range, initialization events, and exactly one chosen edge per full center-aligned period.[2]

CR1 CMS `01`/`10`/`11` describes **output compare interrupt flags** on down/up/both count directions (p1169). Do not infer that merely picking CMS filters every internal ADC trigger or OC reference transition. The direct CC4 path remains a candidate until its actual event behavior is demonstrated; selecting one ADC edge on a compare-event pulse is not the same as suppressing one of two compare matches.[2]

### Conversion time and latency budget

RM §21.4.12 p616 explicitly lists SMP=011 as 24.5 cycles and total 12-bit conversion time as sampling +12.5 cycles. Thus the prior 37-cycle rank / 111-cycle three-rank arithmetic is supported: at 42.5 MHz, rank 0.870588 us, three ranks 2.611765 us. This is **conversion duration excluding trigger latency**, and not an acquisition-settling proof.[2]

DS Table 66 p140 specifies maximum trigger latency in ADC clock periods:[1]

| CKMODE | No conversion abort, tLATR max | Injected aborting regular conversion, tLATRINJ max |
|---|---:|---:|
| 00 | 2.5 | 3.5 |
| 01 | 2.0 | 3.0 |
| 10 | 2.25 | 3.25 |
| 11 | 2.125 | 3.125 |

At 42.5 MHz, asynchronous CKMODE=00 gives 58.824 ns maximum without abort / 82.353 ns with abort. Three-rank duration plus those latencies is 2.670588 / 2.694118 us, before deadtime, CSA settling, input RC, and guard margins (arithmetic from cited values). Injected conversion resets an in-progress regular conversion; the interrupted regular conversion is resumed afterward (RM pp627–628). Therefore regular conversion arbitration is not zero-cost. RM p628 requires trigger spacing longer than the injected sequence (example: 30-cycle sequence requires at least 31 cycles); Figure 98 p629 refers maximum injection latency back to datasheet electrical characteristics.[1][2]

**Important qualification of the existing 42.5 MHz example:** DS Rev 5 Table 66 p139 specifies Range 1 all-ADC single-ended maximum 52 MHz at VDDA≥2.7 V, but only **42 MHz** under the VDDA≥1.62 V condition. Thus 42.5 MHz is not justified for the full low-voltage operating range. The 60 MHz figure is for single-ADC operation, not a blanket allowance for this dual-ADC design. Actual VDDA, regulator range, ADC clock mode and current revision limits must be pinned.[1]

## Usable verbatim source excerpts

The following preserve the primary-source wording, field encodings, and page numbers rather than relying on HAL macros. Whitespace is from `pdftotext -layout`.

### RM0440 Rev 7, p616

```text
Analog-to-digital converters (ADC)                                                            RM0440


21.4.12    Channel-wise programmable sampling time (SMPR1, SMPR2)
           Before starting a conversion, the ADC must establish a direct connection between the
           voltage source under measurement and the embedded sampling capacitor of the ADC. This
           sampling time must be enough for the input voltage source to charge the embedded
           capacitor to the input voltage level.
           Each channel can be sampled with a different sampling time which is programmable using
           the SMP[2:0] bits in the ADC_SMPR1 and ADC registers. It is therefore possible to select
           among the following sampling time values:
           •    SMP = 000: 2.5 ADC clock cycles
           •    SMP = 001: 6.5 ADC clock cycles
           •    SMP = 010: 12.5 ADC clock cycles
           •    SMP = 011: 24.5 ADC clock cycles
           •    SMP = 100: 47.5 ADC clock cycles
           •    SMP = 101: 92.5 ADC clock cycles
           •    SMP = 110: 247.5 ADC clock cycles
           •    SMP = 111: 640.5 ADC clock cycles
           The total conversion time is calculated as follows:
                TCONV = Sampling time + 12.5 ADC clock cycles
           Example:
                With Fadc_ker_ck = 30 MHz and a sampling time of 2.5 ADC clock cycles:
                TCONV = (2.5 + 12.5) ADC clock cycles = 15 ADC clock cycles = 500 ns
           The ADC notifies the end of the sampling phase by setting the status bit EOSMP (only for
           regular conversion).

           Constraints on the sampling time
           For each channel, SMP[2:0] bits must be programmed to respect a minimum sampling time
           as specified in the ADC characteristics section of the datasheets.

           Bulb sampling mode
           When the BULB bit is set in ADC register, the sampling period starts immediately after the
           last ADC conversion. A hardware or software trigger starts the conversion after the sampling
           time has been programmed in ADC_SMPR1 register. The very first ADC conversion, after
           the ADC is enabled, is performed with the sampling time programmed in SMP bits. The Bulb
           mode is effective starting from the second conversion.
           The maximum sampling time is limited (refer to the ADC characteristics section of the
           datasheet).
           The Bulb mode is neither compatible with the continuous conversion mode nor with the
           injected channel conversion.
           When the BULB bit is set, it is not allowed to set SMPTRIG bit in ADC_CFGR2.




616/2124                                    RM0440 Rev 7
```

### RM0440 Rev 7, p622

```text
Analog-to-digital converters (ADC)                                                                     RM0440


21.4.18    Conversion on external trigger and trigger polarity
           (EXTSEL, EXTEN, JEXTSEL, JEXTEN)
           A conversion or a sequence of conversions can be triggered either by software or by an
           external event (e.g. timer capture, input pins). If the EXTEN[1:0] control bits (for a regular
           conversion) or JEXTEN[1:0] bits (for an injected conversion) are different from 00, then
           external events are able to trigger a conversion with the selected polarity.
           When the Injected Queue is enabled (bit JQDIS = 0), injected software triggers are not
           possible.
           The regular trigger selection is effective once software has set bit ADSTART = 1 and the
           injected trigger selection is effective once software has set bit JADSTART = 1.
           Any hardware triggers which occur while a conversion is ongoing are ignored.
           •     If bit ADSTART = 0, any regular hardware triggers which occur are ignored.
           •     If bit JADSTART = 0, any injected hardware triggers which occur are ignored.
           Table 161 provides the correspondence between the EXTEN[1:0] and JEXTEN[1:0] values
           and the trigger polarity.

                   Table 161. Configuring the trigger polarity for regular external triggers
               EXTEN[1:0]                                        Source

                   00        Hardware Trigger detection disabled, software trigger detection enabled
                   01        Hardware Trigger with detection on the rising edge
                   10        Hardware Trigger with detection on the falling edge
                   11        Hardware Trigger with detection on both the rising and falling edges


Note:      The polarity of the regular trigger cannot be changed on-the-fly.

                   Table 162. Configuring the trigger polarity for injected external triggers
               JEXTEN[1:0]                                        Source

                             – If JQDIS = 1 (Queue disabled): Hardware trigger detection disabled, software
                               trigger detection enabled
                   00
                             – If JQDIS = 0 (Queue enabled), Hardware and software trigger detection
                               disabled
                   01        Hardware Trigger with detection on the rising edge
                   10        Hardware Trigger with detection on the falling edge
                   11        Hardware Trigger with detection on both the rising and falling edges


Note:      The polarity of the injected trigger can be anticipated and changed on-the-fly when the
           queue is enabled (JQDIS = 0). Refer to Section 21.4.21: Queue of context for injected
           conversions.
           The EXTSEL and JEXTSEL control bits select which out of 32 possible events can trigger
           conversion for the regular and injected groups.
           A regular group conversion can be interrupted by an injected trigger.



622/2124                                     RM0440 Rev 7
```

### RM0440 Rev 7, p624

```text
Analog-to-digital converters (ADC)                                                           RM0440


              Table 163. ADC1/2 - External triggers for regular channels (continued)
     Name                    Source                            Type                    EXTSEL[4:0]

  adc_ext_trg9            TIM1_TRGO              Internal signal from on-chip timers      01001
  adc_ext_trg10           TIM1_TRGO2             Internal signal from on-chip timers      01010
  adc_ext_trg11           TIM2_TRGO              Internal signal from on-chip timers      01011
  adc_ext_trg12           TIM4_TRGO              Internal signal from on-chip timers      01100
  adc_ext_trg13           TIM6_TRGO              Internal signal from on-chip timers      01101
  adc_ext_trg14           TIM15_TRGO             Internal signal from on-chip timers      01110
  adc_ext_trg15            TIM3_CC4              Internal signal from on-chip timers      01111
  adc_ext_trg16           TIM20_TRGO             Internal signal from on-chip timers      10000
  adc_ext_trg17          TIM20_TRGO2             Internal signal from on-chip timers      10001
  adc_ext_trg18            TIM20_CC1             Internal signal from on-chip timers      10010
  adc_ext_trg19            TIM20_CC2             Internal signal from on-chip timers      10011
  adc_ext_trg20            TIM20_CC3             Internal signal from on-chip timers      10100
  adc_ext_trg21          hrtim_adc_trg1          Internal signal from on-chip timers      10101
  adc_ext_trg22          hrtim_adc_trg3          Internal signal from on-chip timers      10110
  adc_ext_trg23          hrtim_adc_trg5          Internal signal from on-chip timers      10111
  adc_ext_trg24          hrtim_adc_trg6          Internal signal from on-chip timers      11000
  adc_ext_trg25          hrtim_adc_trg7          Internal signal from on-chip timers      11001
  adc_ext_trg26          hrtim_adc_trg8          Internal signal from on-chip timers      11010
  adc_ext_trg27          hrtim_adc_trg9          Internal signal from on-chip timers      11011
  adc_ext_trg28          hrtim_adc_trg10         Internal signal from on-chip timers      11100
  adc_ext_trg29            LPTIMOUT              Internal signal from on-chip timers      11101
  adc_ext_trg30           TIM7_TRGO              Internal signal from on-chip timers      11110
  adc_ext_trg31             reserved                              -                       11111


                   Table 164. ADC1/2 - External trigger for injected channels
     Name                    Source                            Type                    JEXTSEL[4:0]

  adc_jext_trg0           TIM1_TRGO              Internal signal from on-chip timers      00000
  adc_jext_trg1            TIM1_CC4              Internal signal from on-chip timers      00001
  adc_jext_trg2           TIM2_TRGO              Internal signal from on-chip timers      00010
  adc_jext_trg3            TIM2_CC1              Internal signal from on-chip timers      00011
  adc_jext_trg4            TIM3_CC4              Internal signal from on-chip timers      00100
  adc_jext_trg5           TIM4_TRGO              Internal signal from on-chip timers      00101
  adc_jext_trg6            EXTI line 15                     External pin                  00110
  adc_jext_trg7            TIM8_CC4              Internal signal from on-chip timers      00111
  adc_jext_trg8           TIM1_TRGO2             Internal signal from on-chip timers      01000


624/2124                                   RM0440 Rev 7
```

### RM0440 Rev 7, p625

```text
RM0440                                                              Analog-to-digital converters (ADC)


                 Table 164. ADC1/2 - External trigger for injected channels (continued)
     Name                       Source                            Type                    JEXTSEL[4:0]

 adc_jext_trg9               TIM8_TRGO              Internal signal from on-chip timers      01001
 adc_jext_trg10              TIM8_TRGO2             Internal signal from on-chip timers      01010
 adc_jext_trg11               TIM3_CC3              Internal signal from on-chip timers      01011
 adc_jext_trg12              TIM3_TRGO              Internal signal from on-chip timers      01100
 adc_jext_trg13               TIM3_CC1              Internal signal from on-chip timers      01101
 adc_jext_trg14              TIM6_TRGO              Internal signal from on-chip timers      01110
 adc_jext_trg15              TIM15_TRGO             Internal signal from on-chip timers      01111
 adc_jext_trg16              TIM20_TRGO             Internal signal from on-chip timers      10000
 adc_jext_trg17             TIM20_TRGO2             Internal signal from on-chip timers      10001
 adc_jext_trg18               TIM20_CC4             Internal signal from on-chip timers      10010
 adc_jext_trg19             hrtim_adc_trg2          Internal signal from on-chip timers      10011
 adc_jext_trg20             hrtim_adc_trg4          Internal signal from on-chip timers      10100
 adc_jext_trg21             hrtim_adc_trg5          Internal signal from on-chip timers      10101
 adc_jext_trg22             hrtim_adc_trg6          Internal signal from on-chip timers      10110
 adc_jext_trg23             hrtim_adc_trg7          Internal signal from on-chip timers      10111
 adc_jext_trg24             hrtim_adc_trg8          Internal signal from on-chip timers      11000
 adc_jext_trg25             hrtim_adc_trg9          Internal signal from on-chip timers      11001
 adc_jext_trg26             hrtim_adc_trg10         Internal signal from on-chip timers      11010
 adc_jext_trg27               TIM16_CC1             Internal signal from on-chip timers      11011
 adc_jext_trg28                reserved                              -                       11100
 adc_jext_trg29               LPTIMOUT              Internal signal from on-chip timers      11101
 adc_jext_trg30              TIM7_TRGO              Internal signal from on-chip timers      11110
 adc_jext_trg31                reserved                              -                       11111



                     Table 165. ADC3/4/5 - External triggers for regular channels
     Name                       Source                            Type                    EXTSEL[4:0]

  adc_ext_trg0                TIM3_CC1              Internal signal from on-chip timers      00000
  adc_ext_trg1                TIM2_CC3              Internal signal from on-chip timers      00001
  adc_ext_trg2                TIM1_CC3              Internal signal from on-chip timers      00010
  adc_ext_trg3                TIM8_CC1              Internal signal from on-chip timers      00011
  adc_ext_trg4               TIM3_TRGO              Internal signal from on-chip timers      00100
  adc_ext_trg5                EXTI line 2                      External pin                  00101
  adc_ext_trg6                TIM4_CC1              Internal signal from on-chip timers      00110
  adc_ext_trg7               TIM8_TRGO              Internal signal from on-chip timers      00111



                                              RM0440 Rev 7                                      625/2124
                                                                                                           720
```

### RM0440 Rev 7, p628

```text
Analog-to-digital converters (ADC)                                                               RM0440


                reset and the injected channel sequence switches are launched (all the injected
                channels are converted once).
           3.   Then, the regular conversion of the regular group of channels is resumed from the last
                interrupted regular conversion.
           4.   If a regular event occurs during an injected conversion, the injected conversion is not
                interrupted but the regular sequence is executed at the end of the injected sequence.
                Figure 98 shows the corresponding timing diagram.
Note:      When using triggered injection, one must ensure that the interval between trigger events is
           longer than the injection sequence. For instance, if the sequence length is 30 ADC clock
           cycles (that is two conversions with a sampling time of 2.5 clock periods), the minimum
           interval between triggers must be 31 ADC clock cycles.

           Auto-injection mode
           If the JAUTO bit in the ADC_CFGR register is set, then the channels in the injected group
           are automatically converted after the regular group of channels. This can be used to convert
           a sequence of up to 20 conversions programmed in the ADC_SQRy and ADC_JSQR
           registers.
           In this mode, the ADSTART bit in the ADC_CR register must be set to start regular
           conversions, followed by injected conversions (JADSTART must be kept cleared). Setting
           the ADSTP bit aborts both regular and injected conversions (JADSTP bit must not be used).
           In this mode, external trigger on injected channels must be disabled.
           If the CONT bit is also set in addition to the JAUTO bit, regular channels followed by injected
           channels are continuously converted.
Note:      It is not possible to use both the auto-injected and discontinuous modes simultaneously.
           When the DMA is used for exporting regular sequencer’s data in JAUTO mode, it is
           necessary to program it in circular mode (CIRC bit set in DMA_CCRx register). If the CIRC
           bit is reset (single-shot mode), the JAUTO sequence is stopped upon DMA Transfer
           Complete event.




628/2124                                     RM0440 Rev 7
```

### RM0440 Rev 7, p629

```text
RM0440                                                                      Analog-to-digital converters (ADC)


                                         Figure 98. Injected conversion latency


                 adc_ker_ck




              Injection event




                 Reset ADC



                                                       (1)
                                        max. latency
                       SOC


                                                                                                                 MSv43771V1

          1. The maximum latency value can be found in the electrical characteristics of the device datasheet.


21.4.20   Discontinuous mode (DISCEN, DISCNUM, JDISCEN)
          Regular group mode
          This mode is enabled by setting the DISCEN bit in the ADC_CFGR register.
          It is used to convert a short sequence (subgroup) of n conversions (n ≤ 8) that is part of the
          sequence of conversions selected in the ADC_SQRy registers. The value of n is specified
          by writing to the DISCNUM[2:0] bits in the ADC_CFGR register.
          When an external trigger occurs, it starts the next n conversions selected in the ADC_SQRy
          registers until all the conversions in the sequence are done. The total sequence length is
          defined by the L[3:0] bits in the ADC_SQR1 register.
          Example:
          •     DISCEN = 1, n = 3, channels to be converted = 1, 2, 3, 6, 7, 8, 9, 10, 11
                –     1st trigger: channels converted are 1, 2, 3 (an EOC event is generated at each
                      conversion).
                –     2nd trigger: channels converted are 6, 7, 8 (an EOC event is generated at each
                      conversion).
                –     3rd trigger: channels converted are 9, 10, 11 (an EOC event is generated at each
                      conversion) and an EOS event is generated after the conversion of channel 11.
                –     4th trigger: channels converted are 1, 2, 3 (an EOC event is generated at each
                      conversion).
                –     ...
          •     DISCEN = 0, channels to be converted = 1, 2, 3, 6, 7, 8, 9, 10,11
                –     1st trigger: the complete sequence is converted: channel 1, then 2, 3, 6, 7, 8, 9, 10
                      and 11. Each conversion generates an EOC event and the last one also generates
                      an EOS event.
                –     All the next trigger events relaunch the complete sequence.


                                                  RM0440 Rev 7                                                   629/2124
                                                                                                                              720
```

### RM0440 Rev 7, p706

```text
Analog-to-digital converters (ADC)                                                                          RM0440


           Bits 8:7 JEXTEN[1:0]: External Trigger Enable and Polarity Selection for injected channels
                      These bits are set and cleared by software to select the external trigger polarity and enable
                      the trigger of an injected group.
                      00: If JQDIS = 0 (queue enabled), Hardware and software trigger detection disabled
                      00: If JQDIS = 1 (queue disabled), Hardware trigger detection disabled (conversions can be
                      launched by software)
                      01: Hardware trigger detection on the rising edge
                      10: Hardware trigger detection on the falling edge
                      11: Hardware trigger detection on both the rising and falling edges
                    Note: The software is allowed to write these bits only when JADSTART = 0 (which ensures
                            that no injected conversion is ongoing).
                            If JQM = 1 and if the Queue of Context becomes empty, the software and hardware
                            triggers of the injected sequence are both internally disabled (refer to Section 21.4.21:
                            Queue of context for injected conversions)
           Bits 6:2 JEXTSEL[4:0]: External Trigger Selection for injected group
                      These bits select the external event used to trigger the start of conversion of an injected
                      group:
                      00000: Event 0
                      00001: Event 1
                      00010: Event 2
                      00011: Event 3
                      00100: Event 4
                      00101: Event 5
                      00110: Event 6
                      00111: Event 7
                      ...
                      11111: Event 31
                    Note: The software is allowed to write these bits only when JADSTART = 0 (which ensures
                           that no injected conversion is ongoing).
           Bits 1:0 JL[1:0]: Injected channel sequence length
                      These bits are written by software to define the total number of conversions in the injected
                      channel conversion sequence.
                      00: 1 conversion
                      01: 2 conversions
                      10: 3 conversions
                      11: 4 conversions
                    Note: The software is allowed to write these bits only when JADSTART = 0 (which ensures
                           that no injected conversion is ongoing).

Note:       Some channels are not connected physically and must not be selected for conversion.




706/2124                                          RM0440 Rev 7
```

### RM0440 Rev 7, p1081

```text
RM0440                                                 Advanced-control timers (TIM1/TIM8/TIM20)


                            Table 249. Interconnect to the tim_ti2 input multiplexer
                                                               Sources
            tim_ti2 inputs
                                         TIM1                    TIM8                       TIM20

         tim_ti2_in0                  TIM1_CH2                TIM8_CH2                TIM20_CH2
         tim_ti2_in[15:1]                                     Reserved


                            Table 250. Interconnect to the tim_ti3 input multiplexer
                                                                Sources
              tim_ti3 inputs
                                           TIM1                   TIM8                      TIM20

         tim_ti3_in0                    TIM1_CH3               TIM8_CH3               TIM20_CH3
         tim_ti2_in[15:1]                                       Reserved


                            Table 251. Interconnect to the tim_ti4 input multiplexer
                                                                Sources
              tim_ti4 inputs
                                           TIM1                   TIM8                      TIM20

         tim_ti4_in0                    TIM1_CH4               TIM8_CH4               TIM20_CH4
         tim_ti4_in[15:1]                                       Reserved


         Table 252 lists the internal sources connected to the tim_itr input multiplexer.

                                  Table 252. TIMx internal trigger connection
                TIMx                    TIM1                    TIM8                        TIM20

         tim_itr0                     Reserved                tim1_trgo                tim1_trgo
         tim_itr1                     tim2_trgo               tim2_trgo                tim2_trgo
         tim_itr2                     tim3_trgo               tim3_trgo                tim3_trgo
         tim_itr3                     tim4_trgo               tim4_trgo                tim4_trgo
         tim_itr4                     tim5_trgo               tim5_trgo                tim5_trgo
         tim_itr5                     tim8_trgo               Reserved                 tim8_trgo
         tim_itr6                    tim15_trgo               tim15_trgo               tim15_trgo
         tim_itr7                     tim16_oc1               tim16_oc1                tim16_oc1
         tim_itr8                     tim17_oc1               tim17_oc1                tim17_oc1
         tim_itr9                    tim20_trgo               tim20_trgo               Reserved
         tim_itr10                 hrtim_out_sync2         hrtim_out_sync2          hrtim_out_sync2
         tim_itr[15:11]                                       Reserved


         Table 253 lists the internal sources connected to the tim_etr input multiplexer.




                                           RM0440 Rev 7                                         1081/2124
                                                                                                            1220
```

### RM0440 Rev 7, p1169

```text
RM0440                                                                Advanced-control timers (TIM1/TIM8/TIM20)


28.6             TIM1/TIM8/TIM20 registers
                 Refer to Section 1.2 for a list of abbreviations used in register descriptions.

28.6.1           TIMx control register 1 (TIMx_CR1)(x = 1, 8, 20)
                 Address offset: 0x000
                 Reset value: 0x0000

 15      14         13     12      11     10      9       8      7       6      5      4      3       2      1      0
                          DITH   UIFRE
 Res.    Res.      Res.                  Res.      CKD[1:0]    ARPE      CMS[1:0]     DIR    OPM    URS    UDIS    CEN
                           EN     MAP
                           rw      rw             rw      rw     rw      rw    rw     rw      rw     rw      rw     rw



          Bits 15:13 Reserved, must be kept at reset value.
                 Bit 12 DITHEN: Dithering enable
                          0: Dithering disabled
                          1: Dithering enabled
                        Note: The DITHEN bit can only be modified when CEN bit is reset.
                 Bit 11 UIFREMAP: UIF status bit remapping
                          0: No remapping. UIF status bit is not copied to TIMx_CNT register bit 31.
                          1: Remapping enabled. UIF status bit is copied to TIMx_CNT register bit 31.
                 Bit 10 Reserved, must be kept at reset value.
                Bits 9:8 CKD[1:0]: Clock division
                          This bit-field indicates the division ratio between the timer clock (tim_ker_ck) frequency and
                          the dead-time and sampling clock (tDTS)used by the dead-time generators and the digital
                          filters (tim_etr_in, tim_tix),
                          00: tDTS=ttim_ker_ck
                          01: tDTS=2*ttim_ker_ck
                          10: tDTS=4*ttim_ker_ck
                          11: Reserved, do not program this value
                   Bit 7 ARPE: Auto-reload preload enable
                          0: TIMx_ARR register is not buffered
                          1: TIMx_ARR register is buffered
                Bits 6:5 CMS[1:0]: Center-aligned mode selection
                          00: Edge-aligned mode. The counter counts up or down depending on the direction bit
                              (DIR).
                          01: Center-aligned mode 1. The counter counts up and down alternatively. Output compare
                              interrupt flags of channels configured in output (CCxS=00 in TIMx_CCMRx register) are
                              set only when the counter is counting down.
                          10: Center-aligned mode 2. The counter counts up and down alternatively. Output compare
                              interrupt flags of channels configured in output (CCxS=00 in TIMx_CCMRx register) are
                              set only when the counter is counting up.
                          11: Center-aligned mode 3. The counter counts up and down alternatively. Output compare
                              interrupt flags of channels configured in output (CCxS=00 in TIMx_CCMRx register) are
                              set both when the counter is counting up or down.
                         Note: It is not allowed to switch from edge-aligned mode to center-aligned mode as long as
                                the counter is enabled (CEN=1)




                                                       RM0440 Rev 7                                           1169/2124
                                                                                                                           1220
```

### RM0440 Rev 7, p1171

```text
RM0440                                                           Advanced-control timers (TIM1/TIM8/TIM20)


         Bits 31:26 Reserved, must be kept at reset value.
             Bit 24 Reserved, must be kept at reset value.
         Bits 23:20 MMS2[3:0]: Master mode selection 2
                     These bits allow the information to be sent to ADC for synchronization (tim_trgo2) to be
                     selected. The combination is as follows:
                     0000: Reset - the UG bit from the TIMx_EGR register is used as trigger output (tim_trgo2).
                           If the reset is generated by the trigger input (slave mode controller configured in reset
                           mode), the signal on tim_trgo2 is delayed compared to the actual reset.
                     0001: Enable - the Counter Enable signal CNT_EN is used as trigger output (tim_trgo2). It
                           is useful to start several timers at the same time or to control a window in which a
                           slave timer is enabled. The Counter Enable signal is generated by a logic AND
                           between the CEN control bit and the trigger input when configured in Gated mode.
                           When the Counter Enable signal is controlled by the trigger input, there is a delay on
                           tim_trgo2, except if the Master/Slave mode is selected (see the MSM bit description in
                           TIMx_SMCR register).
                     0010: Update - the update event is selected as trigger output (tim_trgo2). For instance, a
                           master timer can then be used as a prescaler for a slave timer.
                     0011: Compare pulse - the trigger output sends a positive pulse when the CC1IF flag is to
                           be set (even if it was already high), as soon as a capture or compare match occurs
                           (tim_trgo2).
                     0100: Compare - tim_oc1refc signal is used as trigger output (tim_trgo2)
                     0101: Compare - tim_oc2refc signal is used as trigger output (tim_trgo2)
                     0110: Compare - tim_oc3refc signal is used as trigger output (tim_trgo2)
                     0111: Compare - tim_oc4refc signal is used as trigger output (tim_trgo2)
                     1000: Compare - tim_oc5refc signal is used as trigger output (tim_trgo2)
                     1001: Compare - tim_oc6refc signal is used as trigger output (tim_trgo2)
                     1010: Compare Pulse - tim_oc4refc rising or falling edges generate pulses on tim_trgo2
                     1011: Compare pulse - tim_oc6refc rising or falling edges generate pulses on tim_trgo2
                     1100: Compare pulse - tim_oc4refc or tim_oc6refc rising edges generate pulses on
                           tim_trgo2
                     1101: Compare pulse - tim_oc4refc rising or tim_oc6refc falling edges generate pulses on
                           tim_trgo2
                     1110: Compare pulse - tim_oc5refc or tim_oc6refc rising edges generate pulses on
                           tim_trgo2
                     1111: Compare pulse - tim_oc5refc rising or tim_oc6refc falling edges generate pulses on
                           tim_trgo2
                    Note: The clock of the slave timer or ADC must be enabled prior to receive events from the
                          master timer, and must not be changed on-the-fly while triggers are received from the
                          master timer.
             Bit 19 Reserved, must be kept at reset value.
             Bit 18 OIS6: Output idle state 6 (tim_oc6 output)
                      Refer to OIS1 bit
             Bit 17 Reserved, must be kept at reset value.
             Bit 16 OIS5: Output idle state 5 (tim_oc5 output)
                      Refer to OIS1 bit
             Bit 15 OIS4N: Output idle state 4 (tim_oc4n output)
                      Refer to OIS1N bit
             Bit 14 OIS4: Output idle state 4 (tim_oc4 output)
                      Refer to OIS1 bit



                                                  RM0440 Rev 7                                            1171/2124
                                                                                                                       1220
```

### DS12288 Rev 5, p139

```text
STM32G474xB STM32G474xC STM32G474xE                                                    Electrical characteristics


5.3.19       Analog-to-digital converter characteristics
             Unless otherwise specified, the parameters given in Table 66 are preliminary values derived
             from tests performed under ambient temperature, fPCLK frequency and VDDA supply voltage
             conditions summarized in Table 17: General operating conditions.
Note:        It is recommended to perform a calibration after each power-up.

                                   Table 66. ADC characteristics(1) (2)
  Symbol        Parameter          Conditions               Min              Typ              Max            Unit

             Analog supply
   VDDA                                   -                 1.62               -               3.6            V
             voltage
             Positive           VDDA ≥ 2 V                   2                 -              VDDA            V
   VREF+     reference
             voltage            VDDA < 2 V                                   VDDA                             V

             Negative
   VREF-     reference                    -                                  VSSA                             V
             voltage
             Input common                             (VREF++VREF-)/2      (VREF+ +    (VREF+ + VREF-)/2
   VCMIN                            Differential                                                              V
             mode                                          - 0.18          VREF-)/2         + 0.18
                                Range 1, single
                                                            0.14               -               60
                                ADC operation
                                Range 2                       -                -               26
                                Range 1, all ADCs
                                operation, single
                                                            0.14               -               52
                                ended mode
                                VDDA ≥ 2.7 V
             ADC clock
   fADC                                                                                                      MHz
             frequency          Range 1, all ADCs
                                operation, single
                                                            0.14               -               42
                                ended mode
                                VDDA ≥ 1.62 V
                                Range 1, all ADCs
                                operation,
                                                            0.14               -               56
                                differential mode
                                VDDA ≥ 1.62 V
                             For given
             Sampling rate,  resolution and                               fADC / (sampling time [cycles] +
        fs                                                 0.001                                             Msps
             continuous mode sampling time                                     resolution [bits] + 0.5)
                             cycles (ts)
                                Considering trigger
                                conversion latency
                                                              -                -
                                time (tLATR or
             External trigger   tLATRINJ)
   TTRIG                                                                                      1ms              -
             period
                                Resolution =
                                                      tconv + [tLATR or
                                12 bits,                                       -
                                                          tLATRINJ]
                                fADC=60 MHz
             Conversion
  VAIN (3)                                -                  0                 -             VREF+            V
             voltage range




                                                   DS12288 Rev 5                                             139/236
                                                                                                                       200
```

### DS12288 Rev 5, p140

```text
Electrical characteristics                                    STM32G474xB STM32G474xC STM32G474xE


                                 Table 66. ADC characteristics(1) (2) (continued)
  Symbol         Parameter            Conditions            Min              Typ               Max          Unit

              External input
   RAIN(4)                                  -                 -                -                50           kΩ
              impedance
              Internal sample
    CADC      and hold                      -                 -                5                -            pF
              capacitor
                                                                                                           conversi
    tSTAB     Power-up time                 -                                  1
                                                                                                           on cycle
                                   fADC = 60 MHz                              1.93                           µs
    tCAL      Calibration time
                                            -                                 116                          1/fADC
              Trigger              CKMODE = 00               1.5               2               2.5
              conversion
                                   CKMODE = 01                -                -               2.0
              latency Regular
    tLATR                                                                                                  1/fADC
              and injected         CKMODE = 10                -                -               2.25
              channels without
              conversion abort     CKMODE = 11                -                -              2.125

              Trigger              CKMODE = 00               2.5               3               3.5
              conversion
                                   CKMODE = 01                -                -               3.0
              latency Injected
  tLATRINJ    channels             CKMODE = 10                -                -               3.25        1/fADC
              aborting a
              regular              CKMODE = 11                -                -              3.125
              conversion
                                   fADC = 60 MHz           0.0416              -             10.675          µs
      ts      Sampling time
                                            -                2.5               -              640.5        1/fADC
tADCVREG_S ADC voltage
TUP        regulator start-up               -                 -                -                20           µs
           time

              Total conversion     fADC = 60 MHz
              time                 Resolution =             0.25               -             10.883          µs
   tCONV                           12 bits
              (including
              sampling time)                -            ts[cycles] + resolution [bits] +0.5 = 15 to 653    1/fADC
              ADC                  fs = 4 Msps                -              590               730
              consumption
 IDDA(ADC)                         fs = 1 Msps                -              160               220           µA
              from the VDDA
              supply               fs = 10 ksps               -               16                50
           ADC                     fs = 4 Msps                -              110               140
           consumption
IDDV_S(ADC                         fs = 1 Msps                -               30                40
           from the VREF+                                                                                    µA
     )
           single ended
                                   fs = 10 ksps               -               0.6               2
           mode
           ADC               fs = 4 Msps                      -              220               270
IDDV_D(ADC consumption
                             fs = 1 Msps                      -               60                70           µA
     )     from the VREF+
           differential mode fs = 10 ksps                     -               1.3               3
1. Guaranteed by design




140/236                                            DS12288 Rev 5
```

## Sources

[1] https://kennedy-engr.github.io/Documents/g474xx_series_datasheet.pdf

[2] https://embedded.fel.cvut.cz/sites/default/files/procesory/STM32/RM0440_STM32G4__Reference_Manual_Rev_7.pdf
