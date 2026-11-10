#!/usr/bin/env python3
"""CX-01: recompute the LM339B OV trip band with the full-temperature VOL limit.

WHY THIS EXISTS
---------------
``docs/design/protection-milestone-report.md`` §"OV thresholds and timing"
publishes a minimum turn-on of 59.417 V from a corner sweep whose comparator
output-low limit was 0-0.4 V.
``docs/design/protection-integration-review.md`` §"P1 -- LM339B VOL budget is
understated" says 0.4 V is the 25 C limit, that the LM339B datasheet limit over
-40...85 C is 550 mV, and that the associated turn-on corner moves down by
about 0.102 V.  Both documents are still published.

This module is the recomputation, not a vote.  It reproduces the published
59.417 V corner from the same network and the same tolerance budget, then
evaluates the same sweep with the 0.55 V limit, so the difference between the
two is arithmetic rather than prose.

THE NETWORK (read from hardware/powerboard-reva/protection_circuit.py, R41-R45)
------------------------------------------------------------------------------
    DC_LINK --[112k]-- OV_MID --[113k]-- OV_SENSE --[10k]-- PGND
    OV_CMD (comparator output, 1k pullup to SAFETY3V3) --[330k]-- OV_SENSE
    IN- = 2.5 V reference (LM4040AIM3-2.5)

    Rt = 112k + 113k = 225k,  Rb = 10k,  Rh = 330k,  Vref = 2.5 V

    Vbus_trip = Vref * (1 + Rt/Rb + Rt/Rh) - Vout * Rt/Rh

WHAT THIS IS NOT
----------------
Not electrical qualification, not a temperature test, not vendor transistor
modelling.  It is a corner arithmetic on datasheet limits.  Two limits this
script deliberately does NOT invent:

* LM339B VOL is specified at ISINK <= 4 mA and VID = -1 V.  At the threshold the
  overdrive is ~0 V, and TI publishes no guaranteed VOL at small overdrive; the
  sweep below therefore assumes the 4 mA / -1 V limit also holds at threshold,
  which is an assumption, not a datasheet guarantee (see PROT-07).
* Resistor tracking, ageing and reference load regulation are outside this
  budget, as the milestone report itself states.

Run:  python3 analysis/cx/ov_threshold.py
"""

from __future__ import annotations

import itertools
import json

# --- network, from the generator -------------------------------------------
RT_NOM = 225_000.0   # 112k + 113k, ERA-6AEB 0.1 %
RB_NOM = 10_000.0    # ERA-6AEB103V 0.1 %
RH_NOM = 330_000.0   # ERA-6AEB334V 0.1 %
VREF_NOM = 2.5       # LM4040AIM3-2.5/NOPB, 0.1 % initial
VOH_NOM = 3.3        # SAFETY3V3, the pullup rail

# --- datasheet limits ------------------------------------------------------
# TI LM339B, SLCS006Z §6.7 Electrical Characteristics for LM339B:
#   VOL max 400 mV at 25 C, 550 mV over -40...85 C, both at ISINK <= 4 mA,
#   VID = -1 V.  VOH is not specified; the output is an open collector, so the
#   high level is the pullup rail and only its tolerance matters.
VOL_25C = 0.40
VOL_FULL_T = 0.55
VOL_ISINK_MAX = 4e-3
#   VIO max +-5.5 mV over -40...85 C; IB max -50 nA (flows out of the pin, so
#   through the 10k lower leg it is 50 nA x 10k = 0.5 mV).  The milestone
#   report budgets them as one +-5.5 mV + 50 nA x 10k term.
VOS_MAX = 5.5e-3
IB_MAX = 50e-9
#   Resistors: 0.1 % initial + 25 ppm/K over a +-50 K excursion from
#   calibration = 0.225 %.  Reference: 0.1 % + 100 ppm/K x 50 K = 0.6 %.
TOL_R = 0.00225
TOL_REF = 0.006
TOL_VOH = 0.04

# The frozen release-contract bus maximum.  CX-02 keeps this number contested
# (a 13s LFP pack tops out at 54.6 V, a 16s at 57.6 V); this script does not
# choose a side there and only reports the margin against the number the
# release contract currently prints.
BUS_MAX_CONTRACT = 58.4


def divider_gain(rt: float, rb: float, rh: float) -> float:
    """Vbus multiplier on Vref: 1 + Rt/Rb + Rt/Rh."""
    if rt <= 0 or rb <= 0 or rh <= 0:
        raise ValueError("divider legs must be positive")
    return 1.0 + rt / rb + rt / rh


def trip(vref: float, vout: float, rt: float, rb: float, rh: float) -> float:
    """Bus voltage at which OV_SENSE crosses Vref, for a given output level."""
    if rt <= 0 or rb <= 0 or rh <= 0:
        raise ValueError("divider legs must be positive")
    if vout < 0:
        raise ValueError("output level cannot be negative")
    return vref * divider_gain(rt, rb, rh) - vout * rt / rh


def low_corner_shift(rt: float, rh: float, delta_vol: float) -> float:
    """Closed form for how much a change in the low output level moves turn-on."""
    if rt <= 0 or rh <= 0:
        raise ValueError("divider legs must be positive")
    if delta_vol < 0:
        raise ValueError("shift is defined for a rising output-low limit")
    return rt / rh * delta_vol


def sink_current(voh: float, vol: float, r_pullup: float = 1_000.0) -> float:
    """Current the comparator sinks when it pulls OV_CMD down."""
    if r_pullup <= 0 or voh < vol:
        raise ValueError("invalid pullup or output level")
    return (voh - vol) / r_pullup


def band(vol_max: float, coupled: bool = False) -> dict:
    """Sweep every independent limit; return the turn-on/turn-off extrema.

    Six independent binary limits: Rt, Rb, Rh, Vref, Vos+Ib, VOH.  `vol_max` is
    swept as its own independent dimension (0 and the limit) because nothing in
    the circuit couples the output-low level to the sign of the pullup-rail
    corner.  `coupled=True` reproduces the published code's coupling
    (``.55 if f > 0 else 0``) so a test can show it does not move the minimum.
    """
    if vol_max < 0:
        raise ValueError("output-low limit cannot be negative")
    on_min = off_min = None
    on_max = off_max = float("-inf")
    worst = None
    corners = 0
    offset = VOS_MAX + IB_MAX * RB_NOM

    for a, b, c, d, e, f in itertools.product((-1, 1), repeat=6):
        rt = RT_NOM * (1 + a * TOL_R)
        rb = RB_NOM * (1 + b * TOL_R)
        rh = RH_NOM * (1 + c * TOL_R)
        vref = VREF_NOM * (1 + d * TOL_REF) + e * offset
        voh = VOH_NOM * (1 + f * TOL_VOH)
        if coupled:
            lows = (vol_max if f > 0 else 0.0,)
        else:
            lows = (0.0, vol_max)
        off = trip(vref, voh, rt, rb, rh)
        for vol in lows:
            on = trip(vref, vol, rt, rb, rh)
            corners += 1
            if on_min is None or on < on_min:
                on_min = on
                worst = dict(rt=rt, rb=rb, rh=rh, vref=vref, voh=voh, vol=vol,
                             signs=(a, b, c, d, e, f))
            on_max = max(on_max, on)
            off_min = off if off_min is None else min(off_min, off)
            off_max = max(off_max, off)

    return dict(on_min=on_min, on_max=on_max, off_min=off_min, off_max=off_max,
                corners=corners, worst_on=worst)


def margin(on_min: float, bus_max: float = BUS_MAX_CONTRACT) -> float:
    """Headroom between the qualified minimum turn-on and the bus maximum."""
    if bus_max <= 0:
        raise ValueError("bus maximum must be positive")
    return on_min - bus_max


def evaluate() -> dict:
    nominal_on = trip(VREF_NOM, 0.2, RT_NOM, RB_NOM, RH_NOM)
    nominal_off = trip(VREF_NOM, VOH_NOM, RT_NOM, RB_NOM, RH_NOM)
    four = band(VOL_25C)
    full = band(VOL_FULL_T)
    worst = full["worst_on"]
    return dict(
        divider_gain=divider_gain(RT_NOM, RB_NOM, RH_NOM),
        rt_over_rh=RT_NOM / RH_NOM,
        nominal=dict(on=nominal_on, off=nominal_off,
                     hysteresis=nominal_on - nominal_off),
        band_0v40=four,
        band_0v55=full,
        shift_0v40_to_0v55=four["on_min"] - full["on_min"],
        shift_closed_form=low_corner_shift(worst["rt"], worst["rh"],
                                           VOL_FULL_T - VOL_25C),
        corner_coupling_is_immaterial=(
            band(VOL_FULL_T, coupled=True)["on_min"] == full["on_min"]),
        margin_to_58v4=margin(full["on_min"]),
        sink_current_at_worst_voh=sink_current(
            worst["voh"], VOL_FULL_T),
        sink_limit=VOL_ISINK_MAX,
    )


def main() -> int:
    result = evaluate()
    full = result["band_0v55"]
    print("CX-01 OV trip band, LM339B, output-low limited by the full-temperature")
    print("VOL spec (550 mV over -40...85 C, ISINK <= 4 mA, VID = -1 V).")
    print()
    print(f"  divider          Rt = 225k, Rb = 10k, Rh = 330k, Vref = 2.5 V")
    print(f"  gain 1+Rt/Rb+Rt/Rh = {result['divider_gain']:.6f}")
    print(f"  Rt/Rh              = {result['rt_over_rh']:.6f}")
    print()
    print("  Vbus_trip = Vref*(1+Rt/Rb+Rt/Rh) - Vout*Rt/Rh")
    print(f"  nominal turn-on  (Vout = 0.2 V) = "
          f"{result['nominal']['on']:.5f} V")
    print(f"  nominal turn-off (Vout = VOH)   = "
          f"{result['nominal']['off']:.5f} V")
    print(f"  nominal hysteresis              = "
          f"{result['nominal']['hysteresis']:.5f} V")
    print()
    print(f"  corners swept: {full['corners']} "
          f"(6 independent binary limits x 2 output-low levels)")
    print()
    print(f"  published corner, Vout low 0...{VOL_25C:.2f} V:")
    print(f"    turn-on  {result['band_0v40']['on_min']:.5f}"
          f" ... {result['band_0v40']['on_max']:.5f} V")
    print(f"  qualified corner, Vout low 0...{VOL_FULL_T:.2f} V:")
    print(f"    turn-on  {full['on_min']:.5f} ... {full['on_max']:.5f} V")
    print(f"    turn-off {full['off_min']:.5f} ... {full['off_max']:.5f} V")
    print()
    w = full["worst_on"]
    print("  worst turn-on corner (minimum):")
    print(f"    Rt = {w['rt']:.1f} ohm  Rb = {w['rb']:.1f} ohm  "
          f"Rh = {w['rh']:.1f} ohm")
    print(f"    Vref = {w['vref']:.6f} V  Vout(low) = {w['vol']:.2f} V")
    print(f"    = {w['vref']:.6f} * {divider_gain(w['rt'], w['rb'], w['rh']):.6f}"
          f" - {w['vol']:.2f} * {w['rt'] / w['rh']:.6f}")
    print(f"    = {full['on_min']:.5f} V")
    print()
    print("  shift from the 0.40 V corner to the 0.55 V corner:")
    print(f"    swept      = {result['shift_0v40_to_0v55']:.5f} V")
    print(f"    closed form (Rt/Rh)*dVout = {w['rt'] / w['rh']:.6f}"
          f" * {VOL_FULL_T - VOL_25C:.2f} = "
          f"{result['shift_closed_form']:.5f} V")
    print(f"    coupling output-low to the VOH corner is immaterial: "
          f"{result['corner_coupling_is_immaterial']}")
    print()
    print(f"  sink current at the worst VOH with Vout = {VOL_FULL_T:.2f} V: "
          f"{result['sink_current_at_worst_voh'] * 1e3:.3f} mA "
          f"(limit {result['sink_limit'] * 1e3:.0f} mA)")
    print()
    print(f"  qualified minimum turn-on = {full['on_min']:.3f} V")
    print(f"  margin to the release-contract bus maximum "
          f"{BUS_MAX_CONTRACT:.1f} V = {result['margin_to_58v4']:.3f} V")
    print()
    print("  NOT INCLUDED, and not claimed: VOL at small input overdrive (the")
    print("  datasheet limit is at VID = -1 V; at threshold VID -> 0), resistor")
    print("  tracking, ageing, reference load regulation.")
    print()
    print(json.dumps(result, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
