#!/usr/bin/env python3
"""PROT-07: qualify the OV threshold at rated temperature, ageing and load.

WHY THIS EXISTS
---------------
``analysis/cx/ov_threshold.py`` (CX-01) recomputes the OV trip band and is
correct as far as it goes. It states its own limits at the top:

    Not electrical qualification, not a temperature test... Two limits this
    script deliberately does NOT invent:
    * LM339B VOL ... at the threshold the overdrive is ~0 V, and TI publishes no
      guaranteed VOL at small overdrive
    * Resistor tracking, ageing and reference load regulation are outside this
      budget, as the milestone report itself states.

PROT-07 asks for exactly those: "extend the corner analysis to rated
temperature plus aging and load regulation, and get a VOL bound at small
overdrive". This module does the parts that arithmetic can actually settle, and
says plainly where a datasheet is silent rather than filling the gap with a
guess.

THREE DEFECTS IN THE EXISTING BUDGET
------------------------------------
1. **Temperature excursion is understated by 30 %.** CX-01 uses a ±50 K
   excursion from calibration. The parts are rated -40...+85 C and calibrated at
   25 C, so the true worst case is **65 K** (to -40 C). The LM4040 datasheet
   itself defines its overtemperature tolerance at **max dT = 65 C**, which
   confirms the figure independently of this repository's assumptions.
   Sensitivity: every ppm/K term scales by 65/50 = 1.3.

2. **The reference tolerance is understated for the fitted grade.** CX-01 uses
   0.1 % + 100 ppm/K x 50 K = 0.6 %. The fitted part is LM4040AIM3-2.5, which is
   **A grade**. TI publishes the combined overtemperature tolerance directly:
   A-grade **+/-0.75 % = +/-0.1 % +/-100 ppm/C x 65 C**. Using 0.6 % understates
   it, and the datasheet number needs no derivation.

3. **Long-term drift and thermal hysteresis are absent.** Both are published:
   long-term stability **120 ppm** after 1000 h at 25 C, and thermal hysteresis
   **0.08 %** over -40...125 C. The hysteresis term is the larger of the two and
   is the one that matters on a vehicle that sees frost and summer sun.

WHAT IS STILL NOT CLOSED, AND WHY
---------------------------------
- **VOL at small overdrive.** TI publishes the LM339B VOL limit at VID = -1 V
  and ISINK <= 4 mA. At the trip point the overdrive is ~0 V. There is no
  datasheet bound there, and inventing one would be fabrication. The budget
  therefore keeps the -1 V limit as an explicitly optimistic assumption and
  records that the resulting band is *not* datasheet-guaranteed.
- **Reference load regulation** is bounded below from the published
  deltaVR/deltaIR curve rather than assumed to be zero.
- Nothing here is measured.

WHAT CHANGED IN THE COMPARISON
------------------------------
CX-01 compares its band against the frozen 58.4 V contract figure. After CX-02
that number is split: the **charge ceiling is 56.0 V** for the selected 20s LTO
pack, and 58.4 V is not a real limit for this pack. The threshold's safety
question is "can it walk below the pack's charge ceiling", so this module
compares against **56.0 V** and reports the 58.4 V margin separately for
continuity with the existing record.
"""

from __future__ import annotations

import itertools

# --- network, identical to analysis/cx/ov_threshold.py --------------------
RT_NOM = 225_000.0   # 112k + 113k
RB_NOM = 10_000.0
RH_NOM = 330_000.0
VREF_NOM = 2.5
VOH_NOM = 3.3

# --- chosen temperature model --------------------------------------------
T_CAL = 25.0
T_MIN = -40.0
T_MAX = 85.0
# CX-01 assumed +-50 K. The real excursion from 25 C calibration to the rated
# extremes is 65 K down / 60 K up; the LM4040 datasheet also uses 65 C.
DELTA_T_CX01 = 50.0
DELTA_T_RATED = max(T_CAL - T_MIN, T_MAX - T_CAL)

# --- resistor tolerance: ERA-6AEB = 0805, TCR code E = +-25 ppm/K, B = +-0.1 %
R_TOL_INITIAL = 0.001
R_TCR_PPM = 25.0

# --- reference: LM4040AIM3-2.5, A grade -----------------------------------
REF_TOL_INITIAL = 0.001
REF_TCR_PPM = 100.0
REF_LONG_TERM_PPM = 120.0     # 1000 h at 25 C
REF_HYSTERESIS = 0.0008       # 0.08 % over -40...125 C
# Published deltaVR/deltaIR: 0.3 mV typ / 0.8 mV max per uA-class change at
# low current, 2.5/6 mV typ/max over 1-15 mA. The sense divider draws well
# under 1 mA, so the 0.8 mV max figure is the relevant bound on 2.5 V.
REF_LOAD_REG_V = 0.0008

# --- comparator -----------------------------------------------------------
VOS_MAX = 5.5e-3   # -40...85 C
IB_MAX = 50e-9
VOL_25C = 0.40
VOL_FULL_T = 0.55

TOL_VOH = 0.04

# --- comparison targets ---------------------------------------------------
CHARGE_CEILING_LTO_20S = 56.0   # CX-02, selected pack
CONTRACT_BUS_MAX = 58.4         # retained for continuity only


def divider_gain(rt: float, rb: float, rh: float) -> float:
    if rt <= 0 or rb <= 0 or rh <= 0:
        raise ValueError("divider legs must be positive")
    return 1.0 + rt / rb + rt / rh


def trip(vref: float, vout: float, rt: float, rb: float, rh: float) -> float:
    if rt <= 0 or rb <= 0 or rh <= 0:
        raise ValueError("divider legs must be positive")
    if vout < 0:
        raise ValueError("output level cannot be negative")
    return vref * divider_gain(rt, rb, rh) - vout * rt / rh


def resistor_tol(delta_t: float, initial: float = R_TOL_INITIAL,
                 tcr_ppm: float = R_TCR_PPM) -> float:
    """Fractional resistance tolerance at a temperature excursion."""
    if delta_t < 0:
        raise ValueError("excursion must be non-negative")
    return initial + (tcr_ppm * 1e-6) * delta_t


def reference_tol(delta_t: float, include_ageing: bool = True,
                  include_hysteresis: bool = True,
                  initial: float = REF_TOL_INITIAL,
                  tcr_ppm: float = REF_TCR_PPM) -> float:
    """Fractional reference tolerance, summed as worst-case magnitudes.

    Summing magnitudes is conservative: it does not assume independence, which
    a root-sum-square would require and which nothing here establishes.
    """
    if delta_t < 0:
        raise ValueError("excursion must be non-negative")
    total = initial + (tcr_ppm * 1e-6) * delta_t
    if include_ageing:
        total += REF_LONG_TERM_PPM * 1e-6
    if include_hysteresis:
        total += REF_HYSTERESIS
    return total


def reference_tol_datasheet_grade() -> float:
    """A-grade combined overtemperature tolerance, straight from TI.

    A-grade: +/-0.75 % = +/-0.1 % +/-100 ppm/C x 65 C.
    Offered alongside the derived figure so the two can be compared rather
    than one silently replacing the other.
    """
    return 0.0075


def band(vol_max: float, delta_t: float, include_ageing: bool = True,
         include_hysteresis: bool = True, use_datasheet_ref: bool = False,
         provide_load_reg: bool = True) -> dict:
    """Worst-case turn-on / turn-off extrema over all sign combinations.

    Polarity matters and is easy to get backwards:

    * **Turn-on** happens while the comparator output is still low, so the
      output-low level is subtracted from the divider sum. A *higher* VOL makes
      the trip *lower*, so the minimum turn-on corner occurs at ``vol = vol_max``
      — not at zero. Sweeping both is what makes the limit honest.
    * **Turn-off** happens after the output has released, so the pullup rail
      VOH is the subtracted level, not VOL.

    Each leg varies by its own fractional tolerance; the reference by its own;
    comparator offset and bias fold into an equivalent reference shift.
    """
    tol_r = resistor_tol(delta_t)
    tol_ref = (reference_tol_datasheet_grade() if use_datasheet_ref
               else reference_tol(delta_t, include_ageing, include_hysteresis))

    on, off = [], []
    for s_rt, s_rb, s_rh, s_ref, s_vos, s_voh in itertools.product(
            (-1, 1), (-1, 1), (-1, 1), (-1, 1), (-1, 1), (-1, 1)):
        rt = RT_NOM * (1 + s_rt * tol_r)
        rb = RB_NOM * (1 + s_rb * tol_r)
        rh = RH_NOM * (1 + s_rh * tol_r)
        vref = VREF_NOM * (1 + s_ref * tol_ref)
        if provide_load_reg:
            vref -= REF_LOAD_REG_V
        vref_eff = vref + s_vos * (VOS_MAX + IB_MAX * RB_NOM)
        # the pullup rail has its own tolerance and only affects turn-off
        voh = VOH_NOM * (1 + s_voh * TOL_VOH)

        # turn-on: output still low, so sweep the low level across its corners
        for vlow in (0.0, vol_max):
            on.append(trip(vref_eff, vlow, rt, rb, rh))
        # turn-off: output released to the pullup rail
        off.append(trip(vref_eff, voh, rt, rb, rh))

    return {
        "on_min": min(on), "on_max": max(on),
        "off_min": min(off), "off_max": max(off),
        "tol_r": tol_r, "tol_ref": tol_ref,
    }


def hysteresis_at_corners(vol_max: float = VOL_FULL_T,
                         delta_t: float = DELTA_T_RATED,
                         include_ageing: bool = True,
                         include_hysteresis: bool = True,
                         provide_load_reg: bool = True) -> dict:
    """Hysteresis evaluated at *matched* corners, which is the only valid way.

    Comparing the global turn-off maximum against the global turn-on minimum
    mixes two different component combinations and is not hysteresis at all --
    they can overlap even though every individual circuit has positive
    hysteresis. This walks the same corner set for both levels.
    """
    tol_r = resistor_tol(delta_t)
    tol_ref = reference_tol(delta_t, include_ageing, include_hysteresis)
    hs = []
    for s_rt, s_rb, s_rh, s_ref, s_vos, s_voh in itertools.product(
            (-1, 1), (-1, 1), (-1, 1), (-1, 1), (-1, 1), (-1, 1)):
        rt = RT_NOM * (1 + s_rt * tol_r)
        rb = RB_NOM * (1 + s_rb * tol_r)
        rh = RH_NOM * (1 + s_rh * tol_r)
        vref = VREF_NOM * (1 + s_ref * tol_ref)
        if provide_load_reg:
            vref -= REF_LOAD_REG_V
        vref_eff = vref + s_vos * (VOS_MAX + IB_MAX * RB_NOM)
        voh = VOH_NOM * (1 + s_voh * TOL_VOH)
        on = trip(vref_eff, vol_max, rt, rb, rh)
        off = trip(vref_eff, voh, rt, rb, rh)
        hs.append(on - off)
    return {"min": min(hs), "max": max(hs)}


def hysteresis_closed_form(vol_max: float = VOL_FULL_T,
                           voh_min: float | None = None,
                           delta_t: float = DELTA_T_RATED) -> float:
    """Minimum hysteresis in closed form, at the Rt/Rh corners.

    Hysteresis is (VOH - VOL) * Rt/Rh. The minimum is achieved with the lowest
    pullup rail, the highest output-low level, and the smallest Rt/Rh ratio --
    all of which can coincide because nothing couples them:
        Rt_min = Rt * (1 - tol),   Rh_max = Rh * (1 + tol)
    """
    voh = VOH_NOM * (1 - TOL_VOH) if voh_min is None else voh_min
    tol_r = resistor_tol(delta_t)
    rt_min = RT_NOM * (1 - tol_r)
    rh_max = RH_NOM * (1 + tol_r)
    return (voh - vol_max) * rt_min / rh_max


def main() -> None:
    print("PROT-07  OV threshold at rated temperature, ageing and load")
    print("=" * 76)
    print()
    print("1. Temperature excursion")
    print(f"   calibrated at {T_CAL:.0f} C, rated {T_MIN:.0f}...{T_MAX:.0f} C")
    print(f"   to {T_MIN:.0f} C: {T_CAL - T_MIN:.0f} K    to {T_MAX:.0f} C: "
          f"{T_MAX - T_CAL:.0f} K")
    print(f"   CX-01 assumed      {DELTA_T_CX01:.0f} K")
    print(f"   actual worst case  {DELTA_T_RATED:.0f} K  "
          f"({DELTA_T_RATED / DELTA_T_CX01:.2f}x understatement)")
    print("   LM4040 datasheet itself defines its overtemperature tolerance at")
    print("   max dT = 65 C, corroborating the figure independently.")
    print()
    print("2. Component drift at that excursion")
    print(f"   resistor ERA-6AEB  {R_TOL_INITIAL:.2%} + {R_TCR_PPM:.0f} ppm/K"
          f" x {DELTA_T_RATED:.0f} K = {resistor_tol(DELTA_T_RATED):.4%}")
    print(f"   same at 50 K (CX-01)                          = "
          f"{resistor_tol(DELTA_T_CX01):.4%}")
    print()
    print(f"   reference LM4040A  {REF_TOL_INITIAL:.2%} + {REF_TCR_PPM:.0f} ppm/K"
          f" x {DELTA_T_RATED:.0f} K + {REF_LONG_TERM_PPM} ppm long-term"
          f" + {REF_HYSTERESIS:.2%} hysteresis")
    print(f"   derived total                                 = "
          f"{reference_tol(DELTA_T_RATED):.4%}")
    print(f"   TI A-grade datasheet figure                   = "
          f"{reference_tol_datasheet_grade():.4%}")
    print(f"   CX-01 used (0.1 % + 100 ppm x 50 K)           = 0.6000%")
    print(f"   -> the fitted A-grade part is {reference_tol_datasheet_grade() / 0.006:.2f}x"
          f" the tolerance CX-01 budgeted")
    print()
    print("3. Trip band comparison")
    rows = [
        ("CX-01 as published (50 K, no ageing)", 0.55, DELTA_T_CX01, False, False, False),
        ("+ rated 65 K excursion", 0.55, DELTA_T_RATED, False, False, False),
        ("+ reference long-term drift", 0.55, DELTA_T_RATED, True, False, False),
        ("+ reference thermal hysteresis", 0.55, DELTA_T_RATED, True, True, False),
        ("+ load regulation bound (PROT-07)", 0.55, DELTA_T_RATED, True, True, True),
    ]
    print("   case                                    on_min   on_max   d(on_min)")
    base = None
    for label, vol, dt, age, hyst, load in rows:
        b = band(vol, dt, age, hyst, False, load)
        if base is None:
            base = b["on_min"]
        print(f"   {label:<38} {b['on_min']:7.3f}  {b['on_max']:7.3f}"
              f"   {b['on_min'] - base:+7.3f}")
    final = band(0.55, DELTA_T_RATED, True, True, False, True)
    print()
    print(f"   final qualified-screening band: turn-on "
          f"{final['on_min']:.3f}-{final['on_max']:.3f} V")
    print(f"                                   turn-off "
          f"{final['off_min']:.3f}-{final['off_max']:.3f} V")
    print()
    h = hysteresis_at_corners()
    print(f"   matched-corner hysteresis: {h['min']:.3f}-{h['max']:.3f} V"
          f" (closed form min {hysteresis_closed_form():.3f} V)")
    print(f"   Global off_max ({final['off_max']:.3f} V) exceeds on_min"
          f" ({final['on_min']:.3f} V) because those extrema come from")
    print(f"   different corners; that is not hysteresis and is not a fault.")
    print()
    print("4. What that means for the selected pack")
    for name, limit in (("charge ceiling, 20s LTO (CX-02)", CHARGE_CEILING_LTO_20S),
                        ("old 58.4 V contract figure", CONTRACT_BUS_MAX)):
        m = final["on_min"] - limit
        verdict = "PASS" if m > 0 else "FAIL"
        print(f"   {name:<36} {limit:5.1f} V -> margin {m:+6.3f} V  {verdict}")
    print()
    print("   The binding comparison is now 56.0 V, not 58.4 V: the threshold's")
    print("   safety question is whether it can walk below what the pack can")
    print("   actually be charged to.")
    print()
    print("5. Sensitivity: how much does the VOL assumption actually cost?")
    for vol, label in ((0.40, "VOL at 25 C only (optimistic)"),
                       (0.55, "VOL full temperature (used)"),
                       (0.70, "VOL 700 mV (legacy LMx39 row, wrong part)")):
        b = band(vol, DELTA_T_RATED, True, True, False, True)
        m = b["on_min"] - CHARGE_CEILING_LTO_20S
        print(f"   {label:<42} on_min {b['on_min']:6.3f} V"
              f"  margin {m:+6.3f} V")
    b025 = band(0.40, DELTA_T_RATED, True, True, False, True)
    b055 = band(0.55, DELTA_T_RATED, True, True, False, True)
    print(f"   cost of using the full-temperature VOL instead of the 25 C one:"
          f" {b025['on_min'] - b055['on_min']:.3f} V")
    print()
    print("VERDICT: the threshold remains above the selected pack's charge")
    print("ceiling at rated temperature with ageing, hysteresis and load")
    print("regulation included. The band widens materially versus CX-01 -- the")
    print("65 K excursion and the A-grade reference tolerance are the drivers --")
    print("and the result is still a SCREENING number, not a qualification,")
    print("because TI publishes no guaranteed VOL at the ~0 V overdrive where")
    print("the threshold actually sits. PROT-07 stays open on that one point.")


if __name__ == "__main__":
    main()
