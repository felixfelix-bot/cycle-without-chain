> **STATUS: SCREENING BOUND — NOT AN AUXILIARY-POWER RELEASE.**
> This bounds a load the published ledger explicitly excludes. It does not
> qualify the chopper, choose a switching frequency, or demonstrate that the
> 1.1 W envelope is met at any real duty cycle.

# PROT-11: chopper gate charge against the 1.1 W auxiliary envelope

## 1. The omission

`docs/design/rail-partition-milestone.md` publishes the always-on auxiliary
ledger as **1.027108922 W** against a **1.1 W** early sink-input envelope, leaving
**0.072891078 W**. Its own SINK12 subtotal is annotated:

> | **Direct SINK12 subtotal** | excludes U4 cascade and active gate charge |

and `docs/design/precharge-power-sources.md` §3 states the missing term:

> Active gate charging adds `Pgate = Qg_total × 12 V × f_chop` and gate pulldown
> loss; neither chopper frequency nor worst-case Qg has been qualified here.

So **1.027108922 W is a lower bound**, and the 72.9 mW margin is an upper bound.
PROT-11 asks for the term to be added and the envelope re-checked.

## 2. The omitted term, computed

Q13 is a **CSD19532Q5B** (TI SLPS414 Rev. B) driven by U10 **UCC27511** from the
12 V SINK12 rail, with a **10 kΩ gate-source pulldown**.

- Qg total at 10 V: **48 nC typical, 62 nC max**
- gate charge: `P = Qg × 12 V × f_chop` → **0.744 mW per kHz** at Qg max
- pulldown: `0.5 × 12²/10 kΩ` at half duty = **7.2 mW**, independent of frequency

| f_chop | gate charge | pulldown (50 % duty) | ledger input | vs 1.1 W |
|---|---:|---:|---:|---|
| 1 kHz | 0.744 mW | 7.200 mW | 1.040349 W | fits |
| 10 kHz | 7.440 mW | 7.200 mW | 1.051509 W | fits |
| 20 kHz | 14.880 mW | 7.200 mW | 1.063909 W | fits |
| 40 kHz | 29.760 mW | 7.200 mW | 1.088709 W | fits |
| 60 kHz | 44.640 mW | 7.200 mW | 1.113509 W | **exceeds** |
| 100 kHz | 74.400 mW | 7.200 mW | 1.163109 W | **exceeds** |

The static pulldown, not the switching charge, is the larger term below about
**9.7 kHz**. Above that the switching term dominates.

## 3. Break frequency

Inverting the ledger for the frequency at which the envelope is exactly
exhausted, everything else held at its published value:

| Duty | Qg max | Qg typical |
|---|---:|---:|
| 0 % | 58.8 kHz | 75.9 kHz |
| 50 % | **49.1 kHz** | 63.4 kHz |
| 100 % | 39.4 kHz | 50.9 kHz |

In the optional **all-OC-on-safety** scenario (U4 input 0.149368546 W), half-duty
headroom falls to **27.4 kHz**.

## 4. The direction that makes it worse

Qg is specified at a **10 V** gate drive, but the driver runs from **12 V**. The
real gate charge is therefore *higher* than the datasheet limit used above, and
the break frequency shrinks in proportion:

- Qg × 1.10 → 44.6 kHz
- Qg × 1.25 → 39.3 kHz
- Qg × 1.50 → 32.7 kHz

This is not a correction applied in the model — it is a stated direction of error,
because interpolating Qg from a single 10 V point would be inventing data.

## 5. What this does and does not settle

**Settled:** the omission is now bounded. The chopper's auxiliary demand is
**0.7–45 mW** across a plausible 1–60 kHz range at half duty, not an unknown
quantity, and the envelope is exhausted at a computable frequency.

**Not settled — PROT-11 stays open with a condition:**

1. **No f_chop is specified anywhere in the corpus.** Until it is chosen and
   recorded, "fits" cannot be asserted. The design fits only below the break
   frequency at the real duty cycle.
2. **Q13's own switching loss and the dump-resistor thermal duty are separate
   gates** (BRK-*, PROT-01, PROT-07). This document accounts only for the
   auxiliary rail's share.
3. **The 1.1 W envelope itself is unqualified** — an acceptance figure, not a
   measured capability. A modest miss in conversion efficiency or logic load
   exhausts the margin regardless of the chopper.
4. **The 60 % conversion efficiency is assumed**, not measured.

## 6. Consequence for published figures

The ledger's **1.027108922 W** must not be quoted as the finished auxiliary total.
It is the total *excluding* the chopper. Any document restating it should say so,
or quote the range above alongside the frequency condition.

## 7. Reproduce

```sh
python3 analysis/cx/chopper_gate_charge.py
python3 -m pytest analysis/cx/test_chopper_gate_charge.py -q   # 23 tests
```

The module first reproduces **1.027108922 W** and **0.072891078 W** exactly, so
the addition is arithmetic on the published numbers rather than a parallel
calculation.

## Sources

- Q13 CSD19532Q5B: [TI SLPS414 Rev. B](https://www.ti.com/lit/ds/symlink/csd19532q5b.pdf) —
  Qg total 48 nC typ (10 V), 62 nC max; Qgd 8.7 nC; R_DS(on) 4.6 mΩ at 6 V, 4.0 mΩ at 10 V.
- U10 UCC27511, 10 Ω turn-on / 2.2 Ω turn-off, 10 kΩ gate-source pulldown:
  `docs/design/protection-milestone-report.md` §Circuit and primary-source identities.
- Ledger and envelope: `docs/design/rail-partition-milestone.md` §Actual load ledger.
- Gate-charge expression and statement that it is unqualified:
  `docs/design/precharge-power-sources.md` §3.
