#!/usr/bin/env python3
"""Overcurrent trip threshold: worst-case corner envelope (register OC-03, OC-08).

WHY THIS EXISTS
---------------
The register records the OC trip as "±19.93 A nominal" and explicitly says the
worst-case claim is blocked because "unbounded midpoint error, thermal drift,
dynamic errors and common reference faults prevent a worst-case safety claim".
OC-03 asks for the corner budget; OC-08 asks whether noise and CSA settling
nuisance-latch given only 1.2 mV of internal hysteresis.

This module computes what *can* be computed — the static corner envelope from the
error sources that have datasheet bounds — and states plainly which terms are
still unbounded. It does not produce a safety claim; it produces the envelope
inside which a safety claim could later be made.

THE SIGNAL CHAIN (as actually built, and as documented in fast-oc-source-analysis §2)
-------------------------------------------------------------------------------------
The DRV8353 current-sense amplifier output is biased at VREF/2. Each comparator
input takes a resistor divider from the same VREF, so the comparator sees the
*difference* between the divider node and the mid-rail bias:

    Itrip = ((VREF/2 - VREF*Rb/(Rt+Rb) + Vcmp_os) / G + Vcsa_os) / Rshunt

Two details that are easy to get wrong, and that this module got wrong first time:

  1. The reference is **VREF/2**, not the divider node alone. The divider is
     compared against the bias, so the trip is set by how far the node sits from
     mid-rail.
  2. **CSA offset is referred to the shunt**, not to the amplifier input. DRV's
     +/-3 mV is already expressed at the sense resistor, so it does NOT get
     divided by G. Treating it as an input-referred term understates its
     contribution by a factor of G -- 0.075 A instead of 1.5 A.

Getting either wrong produces a plausible-looking envelope that disagree with the
documented one. The exhaustive corner sum below reproduces the register's figures
exactly (16.92639 .. 23.08413 A) to all five printed decimals, which is the only
reason to trust it.


WHAT IS MODELLED, AND WITH WHAT BOUNDS
--------------------------------------
  rail        3.3 V +/-3 %             register
  divider     +/-0.1 %                 ERA-6A 0.1 % resistors
  shunt       +/-1 %                   WSLP2512 1 %
  gain        19.4 .. 20.6             DRV8353 datasheet
  CSA offset  +/-3 mV                  DRV8353 datasheet (referred to input)
  comparator  +/-6 mV                  LM339B / TLV3202 class
  hysteresis  1.2 mV typical           DRV8353 internal

WHAT IS NOT MODELLED — and why that blocks a safety claim
---------------------------------------------------------
  * **Midpoint error is unbounded.** The register says so directly. The CSA
    output sits at a mid-rail bias that has no specified tolerance in the way the
    gain does, so it enters as an unknown, not a corner.
  * **Thermal drift** of shunt and offset is not characterised across the
    operating range.
  * **Dynamic errors.** The trip is a sampled comparison; the delay between the
    current crossing the threshold and the latch asserting is not budgeted here,
    and the register's OC-04 says the low-side shunt is blind during high-side
    conduction anyway.
  * **Common reference faults.** A fault that moves the 3.3 V reference and the
    comparator supply together is not covered by a rail-tolerance term.

So the output is an ENVELOPE, not a guarantee. The module returns a
``safety_claim`` field that is always False with a reason, so no caller can
mistake the number for a qualified trip point.
"""

from __future__ import annotations

import json

# --- datasheet / register bounds ---------------------------------------
VREF_V = 3.3
VREF_TOL = 0.03            # +/-3 % — illustrative, not a qualified supply spec

SHUNT_OHM = 0.002          # 2 mOhm
SHUNT_TOL = 0.01           # +/-1 %

GAIN_MIN, GAIN_MAX = 19.4, 20.6
DIVIDER_TOL = 0.001        # +/-0.1 % initial (ERA-6A)
CSA_OFFSET_V = 0.003       # +/-3 mV, REFERRED TO THE SHUNT (not the amp input)
COMP_OFFSET_V = 0.006      # +/-6 mV over temperature (TLV3202, not 1's 4 mV)
HYST_V = 0.0012            # 1.2 mV typical internal hysteresis, no guaranteed max

# Divider legs, from fast-oc-source-analysis §2.
#   LOW_REF : 28.7k from VREF to node, 10k node to PGND
#   HIGH_REF: 10k from VREF to node, 28.7k node to PGND
LOW_REF = (28.7e3, 10e3)
HIGH_REF = (10e3, 28.7e3)


def divider_node(rt: float, rb: float, vref: float) -> float:
    """Voltage at the divider tap."""
    return vref * rb / (rt + rb)


def trip_current(vref: float, rt: float, rb: float, gain: float,
                 shunt: float, csa_offset: float = 0.0,
                 comp_offset: float = 0.0) -> float:
    """Phase current at which the comparator input crosses mid-rail.

        ((VREF/2 - node + Vcmp_os) / G + Vcsa_os) / Rshunt
    """
    node = divider_node(rt, rb, vref)
    return ((vref / 2.0 - node + comp_offset) / gain + csa_offset) / shunt


def envelope(leg: tuple[float, float]) -> dict:
    """Exhaustive binary-corner trip interval for one divider leg."""
    trips = []
    for vref_t in (-VREF_TOL, VREF_TOL):
        for rt_t in (-DIVIDER_TOL, DIVIDER_TOL):
            for rb_t in (-DIVIDER_TOL, DIVIDER_TOL):
                for gain in (GAIN_MIN, GAIN_MAX):
                    for shunt_t in (-SHUNT_TOL, SHUNT_TOL):
                        for csa in (-CSA_OFFSET_V, CSA_OFFSET_V):
                            for comp in (-COMP_OFFSET_V, COMP_OFFSET_V):
                                trips.append(trip_current(
                                    vref=VREF_V * (1 + vref_t),
                                    rt=leg[0] * (1 + rt_t),
                                    rb=leg[1] * (1 + rb_t),
                                    gain=gain,
                                    shunt=SHUNT_OHM * (1 + shunt_t),
                                    csa_offset=csa,
                                    comp_offset=comp,
                                ))
    return {"earliest_a": min(trips), "latest_a": max(trips),
            "spread_a": max(trips) - min(trips),
            "corners": len(trips)}


def envelope_both() -> dict:
    return {"low": envelope(LOW_REF), "high": envelope(HIGH_REF)}


def hysteresis_band_a() -> dict:
    """Trip/release separation from the comparator's internal hysteresis only.

    OC-08's question: with 1.2 mV of hysteresis, how much current must the signal
    fall before the latch releases. If that band is smaller than the noise and
    the CSA settling residue, the comparator chatter nuisance-latches.

    Three gains matter and they disagree, so all three are reported:
      * nominal (gain 20) gives the documented 0.030 A;
      * GAIN_MIN (19.4) gives the LARGEST band, 0.0309 A;
      * GAIN_MAX (20.6) gives the SMALLEST band, 0.0291 A — and the smallest is
        the one that matters for chatter, because it is the least separation the
        part can provide. Quoting the nominal figure as "the" band quietly
        assumes the most favourable gain.
    """
    def band(gain: float) -> float:
        return (HYST_V / gain) / SHUNT_OHM

    nominal = band(20.0)
    smallest = band(GAIN_MAX)
    largest = band(GAIN_MIN)
    return {
        "hysteresis_v": HYST_V,
        "band_a": nominal,          # keeps the documented 0.030 A as the headline
        "band_nominal_a": nominal,
        "band_min_a": smallest,     # binding case for nuisance latching
        "band_max_a": largest,
        "note": ("This is the current separation a latched comparator needs to "
                 "release if hysteresis is the only mechanism. The binding figure "
                 "is band_min_a, not the nominal one. It must be compared against "
                 "measured noise and CSA settling residue, neither of which is "
                 "characterised here."),
    }


def evaluate() -> dict:
    env = envelope_both()
    hyst = hysteresis_band_a()
    # The commissioning cap the milestone document proposes. The question is not
    # whether the cap lands inside the trip band (that would be bad — it would
    # mean legitimate operating current trips the protection) but whether it sits
    # safely BELOW the earliest possible trip, so the cap never causes a trip and
    # the trip always occurs above the permitted operating envelope.
    cap_a = 10.0
    earliest = env["low"]["earliest_a"]
    return {
        "envelope": env,
        "hysteresis": hyst,
        "commissioning_cap_a": cap_a,
        "cap_below_earliest_trip": cap_a < earliest,
        "cap_margin_a": earliest - cap_a,
        "unbounded_terms": [
            "CSA midpoint bias has no specified tolerance",
            "shunt and offset thermal drift not characterised over range",
            "trip latency between threshold crossing and latch not budgeted",
            "low-side shunt blind during high-side conduction (register OC-04)",
            "common reference fault not covered by a rail-tolerance term",
        ],
        "safety_claim": False,
        "safety_claim_reason": (
            "The static envelope is computable but a guaranteed trip point is "
            "not: five terms above are unbounded, so no current can be claimed "
            "safe to reach without damage. Register OC-03 stays open until "
            "midpoint error is bounded and thermal drift is characterised."),
    }


def main() -> int:
    r = evaluate()
    e = r["envelope"]
    print("Overcurrent trip envelope — 2 mOhm shunt, DRV8353 gain 19.4-20.6")
    print("=" * 68)
    print("Exhaustive binary corners, 128 per leg (7 binary terms):")
    print("VREF +/-3 %, divider +/-0.1 %, shunt +/-1 %, gain 19.4-20.6,")
    print("CSA +/-3 mV (shunt-referred), comparator +/-6 mV")
    print()
    print("  window edge    earliest     latest      spread")
    print("                 (A)          (A)         (A)")
    for edge in ("low", "high"):
        v = e[edge]
        print("  %-13s %-12.5f %-11.5f %.5f"
              % (edge, v["earliest_a"], v["latest_a"], v["spread_a"]))
    print()
    h = r["hysteresis"]
    print("Release band from 1.2 mV hysteresis alone: %.2f A" % h["band_a"])
    print("  %s" % h["note"])
    print()
    print("Commissioning cap %.0f A vs earliest possible trip %.2f A: %s (margin %.2f A)"
          % (r["commissioning_cap_a"], r["envelope"]["low"]["earliest_a"],
             "below" if r["cap_below_earliest_trip"] else "NOT BELOW",
             r["cap_margin_a"]))
    print()
    print("NOT MODELLED — these block a safety claim:")
    for u in r["unbounded_terms"]:
        print("  - %s" % u)
    print()
    print("safety_claim: %s" % r["safety_claim"])
    print("  %s" % r["safety_claim_reason"])

    with open("oc-envelope-results.json", "w", encoding="utf-8") as fh:
        json.dump(r, fh, indent=1)
        fh.write("\n")
    print("\nwrote oc-envelope-results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
