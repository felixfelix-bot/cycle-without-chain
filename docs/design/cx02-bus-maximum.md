> **STATUS: CONTRADICTION RESOLVED BY SEPARATION — NOT A BUS-LIMIT RELEASE.**
> This shows that 58.4 V was two different quantities and is wrong for both
> roles. It does not select the stress ceiling, which is an operator decision
> because it sets TVS clamp, capacitor class and a leak clamp that does not
> exist. Nothing here was measured, and no PCB exists.

# CX-02: the bus maximum is two numbers, not one

## 1. The contradiction as recorded

> The release contract freezes **58.4 V** maximum normal charge; storage review
> says real series ceilings are 13×4.2 = **54.6 V** and 16×3.6 = **57.6 V**, not
> generic 58.4 V LFP charging
>
> Risk: charge control and clamp thresholds set against a voltage the chosen
> pack cannot reach
>
> Closes by: reconcile the bus maximum with the selected pack ceiling after
> ARCH-06

ARCH-06 is now decided ([storage decision](storage-decision-lto.md)): **20s
Toshiba SCiB LTO**, 2.4 V nominal, 2.8 V maximum.

## 2. Where 58.4 V came from

**58.4 V is a 16s LFP string at 3.65 V/cell.** It was the top of a provisional
"screening range" that also named 13s Li-ion at 55.6…54.6 V. **Neither string is
the storage that was selected.** The number survived because it was a convenient
round top-of-range figure, not because any chosen pack reached it.

## 3. The resolution: two roles, not one value

The contradiction cannot be closed by picking a winner, because 58.4 V was doing
**two different jobs**, and it is wrong for both.

**Role 1 — CHARGE ceiling.** The highest voltage the pack may be charged to.
For 20s LTO this is **56.0 V**. Commanding 58.4 V at this pack would be a
**+2.4 V / +4.3 % overcharge command**. So the charge ceiling becomes **56.0 V**.

**Role 2 — STRESS ceiling.** The highest voltage the DC-link components must
survive. This is **not** the pack ceiling, and never was, because the pack cannot
bound the bus:

- a spinning PM machine rectifies through MOSFET body diodes with the pack open,
  so the machine charges the bus regardless of pack state;
- the chopper can only *sink* current, so it deliberately holds the bus **above**
  the pack. During a full-pack descent the bus sits at the chopper's hold level,
  not at pack voltage.

The binding number is the CX-01 trip band: **turn-on 59.315–61.226 V**,
**turn-off 57.356–59.058 V**. Components must survive the top of that band plus
overshoot. **58.4 V is below the chopper's own regulation point**, so it cannot
serve as the stress ceiling either.

| | Value | Status |
|---|---|---|
| Charge ceiling (20s LTO) | **56.0 V** | determined by cell max × series count |
| Nominal | 48.0 V | 20 × 2.4 |
| Floor | 36.0 V | 20 × 1.8 |
| Chopper turn-on | 59.315–61.226 V | CX-01, 0.55 V corner |
| Chopper turn-off | 57.356–59.058 V | CX-01 |
| Stress ceiling | **≥ 61.226 V before overshoot** | floor only; not yet chosen |

## 4. The consequence that actually matters

Chopper turn-off floor is **57.356 V**; a full LTO pack is **56.0 V**. Once the
chopper has conducted it holds the bus **1.356 V above** what the pack can
accept.

| Pack voltage | Headroom to chopper | Chopper holds above pack | Pack absorbs regen? |
|---:|---:|---:|---|
| 36.0 V | +23.315 V | +21.356 V | yes |
| 44.0 V | +15.315 V | +13.356 V | yes |
| 48.0 V | +11.315 V | +9.356 V | yes |
| 52.0 V | +7.315 V | +5.356 V | yes |
| **56.0 V** | +3.315 V | +1.356 V | **NO** |

**At full charge the dump resistor carries 100 % of regen and the pack carries
none.** That is the primary path on a descent, not a fallback. Any design
narrative that says "the battery absorbs the downhill" is wrong for this pack,
and it means the dump resistor's thermal rating and BRK-01/PROT-09 are
load-bearing rather than contingency.

An easy error worth naming: **bus headroom is not pack acceptance.** At 56.0 V
the bus still has 3.315 V of room to rise, yet the pack at its ceiling accepts
nothing. Conflating the two would have produced "it fits" from a true premise.
The model keeps them as separate functions and a test pins the distinction; a
negative control (removing the ceiling check) fails exactly the two boundary
tests.

## 5. What this does not do

1. **Does not choose the stress ceiling.** "≥ 61.226 V before overshoot" is a
   floor derived from the chopper's top corner, not a selection. Choosing it
   fixes the TVS clamp voltage, the capacitor class and the leak-clamp level, and
   none of those exist yet.
2. **Does not add a leak clamp.** Without one, a runaway machine with the pack
   open has only the chopper between it and the capacitor rating. PROT-01
   remains open.
3. **Does not quantify overshoot.** Cable inductance, ringing, BMS-open energy
   and switching transients are PROT-04/PROT-08 territory.
4. **Does not touch the 44 files that cite 58.4 V.** Propagating 56.0 V as the
   charge ceiling and a new stress ceiling is a separate, mechanical but
   wide-reaching edit that must follow the operator's stress-ceiling decision —
   doing half of it now would create a new contradiction in place of the old one.

## 6. Consequence for the gate

CX-02's stated risk — *"charge control and clamp thresholds set against a
voltage the chosen pack cannot reach"* — is now precisely characterised rather
than present as one undifferentiated wrong number. The charge ceiling is a
**decided fact** (56.0 V from the selected 20s LTO pack). The stress ceiling is a
**bounded open decision** (≥ 61.226 V), and it is no longer confused with the
charge ceiling.

CX-02 therefore moves from *"no winner chosen"* to **charge role resolved, stress
role bounded and awaiting an operator decision** — one decision, with its
consequences spelled out, instead of an unresolved contradiction.

## 7. Reproduce

```sh
python3 analysis/cx/bus_maximum.py
python3 -m unittest analysis.cx.test_bus_maximum   # 23 tests
```

## Sources

- 20s LTO cell limits and the 56.0 V ceiling: `storage-decision-lto.md` §D1.
- Chopper trip bands: `protection-milestone-report.md` §OV thresholds and timing;
  recomputed in `analysis/cx/ov_threshold.py`.
- 58.4 V as a 16s LFP figure: `custom-powerboard-concept.md` §DC bus.
- Refusal to justify a 63 V capacitor by "full charge is 58.4 V":
  `custom-powerboard-concept.md` §DC-link capacitors — the same distinction,
  stated earlier and never applied to the bus maximum itself.
