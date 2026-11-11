> **STATUS: EXTENDED SCREENING BUDGET — STILL NOT A QUALIFICATION.**
> This adds rated temperature, ageing, hysteresis and load regulation to the OV
> trip band. It closes three of the four items PROT-07 named. The fourth — a
> guaranteed comparator VOL at ~0 V overdrive — cannot be closed from any
> datasheet, so the band remains a screening number. Nothing was measured.

# PROT-07: OV threshold at rated temperature, ageing and load

## 1. What the gate asked for

> That the 59.315–61.226 V band is qualification, when it covers only a ±50 K
> excursion from calibration, assumes the datasheet VOL limit (specified at
> VID = −1 V, ISINK ≤ 4 mA) also holds at the ~0 V overdrive of the threshold,
> and leaves resistor tracking, aging and reference load regulation open
>
> Closes by: extend the corner analysis to rated temperature plus aging and load
> regulation, and get a VOL bound at small overdrive

`analysis/cx/ov_threshold.py` states the same limitation about itself. This
document does the four things asked, in order, and is explicit about the one that
cannot be done.

## 2. Defect one: the temperature excursion was understated by 30 %

CX-01 uses **±50 K**. The parts are rated **−40…+85 °C** and calibrated at
25 °C, so the real worst case is **65 K** (to −40 °C):

| | Value |
|---|---|
| Calibrated at | 25 °C |
| To −40 °C | **65 K** |
| To +85 °C | 60 K |
| CX-01 assumed | 50 K |
| Understatement | **1.30×** |

This is not an assumption I introduced. The **LM4040 datasheet defines its own
overtemperature tolerance at max ΔT = 65 °C**, and prints the resulting grade
figures explicitly — corroborating 65 K independently of this repository.

## 3. Defect two: the reference tolerance was understated for the fitted grade

CX-01 used `0.1 % + 100 ppm/K × 50 K = 0.600 %`. The **fitted part is
LM4040AIM3-2.5, A grade**, and TI publishes the combined overtemperature figure
directly rather than requiring derivation:

> A-grade: ±0.75 % = ±0.1 % ±100 ppm/°C × 65 °C

So the real tolerance is **1.25×** what CX-01 budgeted.

## 4. Defect three: ageing and hysteresis were absent

Both are published and were simply not in the budget:

- **Long-term stability: 120 ppm** after 1000 h at 25 °C
- **Thermal hysteresis: 0.08 %** over −40…125 °C

Hysteresis is the larger term and the one that matters on a vehicle that sees
frost and summer sun. Summing magnitudes gives a derived reference tolerance of
**0.842 %** — deliberately more pessimistic than the 0.75 % datasheet grade
figure, because it adds ageing and hysteresis on top rather than assuming they
are already included.

## 5. The band, built up step by step

Each row adds one term to the row above, so the cost of each is visible:

| Case | turn-on min | turn-on max | Δ vs published |
|---|---:|---:|---:|
| CX-01 as published (50 K, no ageing) | 59.315 V | 61.226 V | — |
| + rated 65 K excursion | 59.183 V | 61.361 V | −0.133 V |
| + reference long-term drift | 59.175 V | 61.368 V | −0.140 V |
| + reference thermal hysteresis | 59.127 V | 61.417 V | −0.188 V |
| + load-regulation bound | **59.108 V** | **61.398 V** | **−0.207 V** |

**The model reproduces CX-01's published 59.315 V exactly before adding
anything**, so every subsequent difference is arithmetic on the published
number rather than a parallel calculation.

Final screening band: **turn-on 59.108–61.398 V**, **turn-off 57.150–59.229 V**.

## 6. What that means against the selected pack

After CX-02 the 58.4 V contract figure is not a real limit for this pack; the
**charge ceiling is 56.0 V** for the selected 20s LTO string. That is the
binding comparison, because the safety question is whether the threshold can
walk *below what the pack can actually be charged to*:

| Comparison | Limit | Margin | Verdict |
|---|---:|---:|---|
| Charge ceiling, 20s LTO (CX-02) | 56.0 V | **+3.108 V** | PASS |
| Old 58.4 V contract figure | 58.4 V | +0.708 V | PASS |

Both pass. The margin against the *real* limit is **larger** than the margin
against the retired figure, which is the opposite of the intuitive direction and
worth noting: correcting CX-02 made this threshold look safer, not less safe.

## 7. Two errors made and fixed while doing this

Recorded because both would have produced a plausible-looking wrong answer.

**Error 1 — wrong polarity on turn-on.** My first version swept the output-low
level as an independent dimension and partitioned results by whether it was zero.
That is backwards: turn-on occurs while the output is *still low*, and a *higher*
VOL pushes the trip *lower*, so the minimum turn-on corner is at `vol = vol_max`,
not at zero. The corrected model reproduces CX-01's 59.315 V; the wrong one gave
59.689 V. A tenth of a volt, in the unsafe direction.

**Error 2 — testing hysteresis on global extrema.** I asserted
`off_max < on_min`, which fails: 59.229 V vs 59.108 V. That is not a defect — the
two extrema come from *different* component corners, while every individual
circuit has positive hysteresis. Comparing global maxima and minima across a
corner sweep is not a hysteresis test at all. Hysteresis is now evaluated at
**matched** corners: **1.776–1.975 V**, matching the closed form
`(VOH_min − VOL_max) × Rt_min/Rh_max = 1.776 V` to 1 mV.

## 8. The one item that cannot be closed

> get a VOL bound at small overdrive

**TI publishes no guaranteed LM339B VOL at ~0 V overdrive.** The 550 mV limit is
specified at VID = −1 V and ISINK ≤ 4 mA. At the actual trip point the overdrive
is ~0 V, where a comparator's output-low level is not bounded by that number.

I did **not** invent a bound. Instead the sensitivity is quantified, so the size
of the exposure is known rather than unknown:

| VOL assumption | turn-on min | Margin vs 56.0 V |
|---|---:|---:|
| 400 mV (25 °C only — optimistic) | 59.210 V | +3.210 V |
| 550 mV (full temperature — used) | 59.108 V | +3.108 V |
| 700 mV (legacy LMx39 row — wrong part) | 59.006 V | +3.006 V |

The cost of the full-temperature assumption versus the optimistic 25 °C figure is
**0.102 V**. Even the wrong-part 700 mV figure leaves 3.006 V of margin, so the
*conclusion* is robust to the assumption even though the *number* is not
qualified. That is the honest form of the answer.

## 9. Consequence for the gate

Three of the four PROT-07 items are now done:

- ✅ rated temperature (65 K, not 50 K)
- ✅ ageing (120 ppm long-term, plus 0.08 % hysteresis)
- ✅ reference load regulation (bounded from the published ΔVR/ΔIR curve)
- ❌ **VOL at small overdrive — not obtainable from a datasheet**

PROT-07 therefore stays **OPEN**, but its scope is now a single, precisely named
gap rather than an open-ended list. The remaining evidence that could close it is
either a vendor characterisation curve, a bench measurement of VOL at threshold,
or a design change that removes the dependency — for example a comparator with a
specified VOL at zero overdrive, or adding hysteresis so the circuit never sits
at the threshold. None of those is a document I can write.

## 10. Reproduce

```sh
python3 analysis/cx/ov_qualification.py
python3 -m unittest analysis.cx.test_ov_qualification   # 27 tests
```

## Sources

- **LM4040-N** (TI): A-grade combined overtemperature tolerance ±0.75 % =
  ±0.1 % ±100 ppm/°C × 65 °C; long-term stability 120 ppm/1000 h; thermal
  hysteresis 0.08 % over −40…125 °C; ΔVR/ΔIR 0.3/0.8 mV typ/max at low current.
- **LM339B** (TI, §6.7 "Electrical Characteristics for LM339B"): VOL max 400 mV
  at 25 °C, **550 mV over −40…85 °C**, at ISINK ≤ 4 mA and VID = −1 V; VIO
  ±5.5 mV; IB −50 nA. *(The 700 mV full-range row in the same PDF is the legacy
  LMx39 table, §6.10 — not this part.)*
- **ERA-6A** (Panasonic): size code 6A = 0805, tolerance code B = ±0.1 %,
  temperature coefficient code **E = ±25×10⁻⁶/K**.
- Network, divider and prior band: `protection-milestone-report.md` §OV
  thresholds and timing; `analysis/cx/ov_threshold.py`.
- Charge ceiling 56.0 V: [cx02-bus-maximum.md](cx02-bus-maximum.md) §3.
