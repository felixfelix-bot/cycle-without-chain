#!/usr/bin/env python3
"""CX-03: what regen figure does the committed model actually produce?

WHY THIS EXISTS
---------------
``docs/analysis/chainless-drivetrain.md`` §0 and §2 print **8.2 Wh** capturable
for 20 stop-starts at 65 % (one KE -> battery hop).  §12 recomputes the same
20 stops through a **two-hop** chain (0.791 out, 0.791 back) to **7.9 Wh** and
calls the 8.2 Wh figure superseded.  Both numbers were still on the page, so the
withdrawn one stayed quotable as the study's result.

The resolution is not a vote between them: it is to run
``docs/analysis/chainless_drivetrain_model.py`` and take the figure that the
current model prints.  This module re-derives that figure from the model's own
constants and a test asserts the two agree, so the document cannot drift away
from the script again.

THE TWO CHAINS
--------------
one hop  (withdrawn):  2267 J x 0.65                 -> 8.2 Wh   [65 % is A7]
two hops (current):    2267 J x 0.7912 x 0.7912      -> 7.9 Wh

0.7912 is the model's KE -> battery efficiency: Grin All-Axle DD hub *system*
0.86 x LFP round trip 0.92.  The round trip is the square of that, 0.6260.

WHAT THIS IS NOT
----------------
Not a measurement.  65 %, 86 % and 92 % are all ESTIMATE/CITED inputs, and
DRV-01 in the open-gates register exists because 65 % was never measured.  This
script only decides which of two printed numbers the model currently produces.

Run:  python3 analysis/cx/regen_recovery.py
"""

from __future__ import annotations

import json

# --- model constants, copied from docs/analysis/chainless_drivetrain_model.py
M_RIDER = 78.0      # kg  ASSUMPTION
M_BIKE = 16.0       # kg  ESTIMATE
CRR = 0.006         # -   ESTIMATE
RHO = 1.20          # kg/m3 CITED
CDA = 0.50          # m2  ESTIMATE
V_CRUISE_KMH = 25.0
N_STOPS = 20        # per 10 km commute
COMMUTE_KM = 10.0
ETA_GEN_PM_HUB = 0.86   # CITED, Grin DD hub system @31 km/h
ETA_BATTERY_RT = 0.92   # ESTIMATE, LFP round trip incl BMS
G = 9.81

# The withdrawn assumption, kept as a named constant so it is reproducible
# without being current.
WITHDRAWN_SINGLE_HOP = 0.65


def kinetic_energy(mass: float, kmh: float) -> float:
    """Joules of kinetic energy at speed ``kmh``."""
    if mass <= 0:
        raise ValueError("mass must be positive")
    if kmh < 0:
        raise ValueError("speed cannot be negative")
    v = kmh / 3.6
    return 0.5 * mass * v * v


def flat_power(mass: float, kmh: float, crr: float = CRR, rho: float = RHO,
               cda: float = CDA) -> float:
    """Wheel power to hold ``kmh`` on the flat, in W (model section 1)."""
    if mass <= 0 or kmh < 0:
        raise ValueError("invalid mass or speed")
    v = kmh / 3.6
    return (crr * mass * G + 0.5 * rho * cda * v * v) * v


def regen_recovery(mass: float, kmh: float, stops: int, eta_gen: float,
                   eta_battery: float) -> dict:
    """Both chains, so the difference is arithmetic and not an opinion."""
    for label, value in (("eta_gen", eta_gen), ("eta_battery", eta_battery)):
        if not 0.0 < value <= 1.0:
            raise ValueError(f"{label} must be in (0, 1]")
    if stops < 0:
        raise ValueError("stop count cannot be negative")

    ke = kinetic_energy(mass, kmh)
    one_hop = eta_gen * eta_battery
    round_trip = one_hop * one_hop

    t_commute = COMMUTE_KM * 1000.0 / (kmh / 3.6) if kmh > 0 else 0.0
    trip_wh = flat_power(mass, kmh) * t_commute / 3600.0

    total_wh = stops * ke * round_trip / 3600.0
    return dict(
        ke_j=ke,
        ke_wh=ke / 3600.0,
        one_hop=one_hop,
        round_trip=round_trip,
        stored_wh_per_stop=ke * one_hop / 3600.0,
        back_at_wheel_wh_per_stop=ke * round_trip / 3600.0,
        total_wh=total_wh,
        trip_wh=trip_wh,
        percent_of_trip=100.0 * total_wh / trip_wh if trip_wh else 0.0,
        single_hop_65_wh=stops * ke * WITHDRAWN_SINGLE_HOP / 3600.0,
    )


def main() -> int:
    r = regen_recovery(M_RIDER + M_BIKE, V_CRUISE_KMH, N_STOPS,
                       ETA_GEN_PM_HUB, ETA_BATTERY_RT)
    print("CX-03 regen recovery, the chain the committed model prints.")
    print()
    print(f"  KE({V_CRUISE_KMH:.0f} km/h) = 0.5 * {M_RIDER + M_BIKE:.0f} kg * "
          f"{(V_CRUISE_KMH / 3.6):.4f}^2 m/s = {r['ke_j']:.0f} J = "
          f"{r['ke_wh']:.4f} Wh")
    print(f"  one hop  = {ETA_GEN_PM_HUB:.2f} gen x {ETA_BATTERY_RT:.2f} batt"
          f" = {r['one_hop']:.4f}")
    print(f"  round trip = {r['one_hop']:.4f}^2 = {r['round_trip']:.4f}")
    print()
    print("  CURRENT (two hops, the chain the model prints):")
    print(f"    {r['ke_j']:.0f} J x {r['one_hop']:.4f} = "
          f"{r['ke_j'] * r['one_hop']:.0f} J = "
          f"{r['stored_wh_per_stop']:.4f} Wh stored")
    print(f"          x {r['one_hop']:.4f} = "
          f"{r['ke_j'] * r['round_trip']:.0f} J = "
          f"{r['back_at_wheel_wh_per_stop']:.4f} Wh back at the wheel")
    print(f"    {N_STOPS} stops -> {r['total_wh']:.2f} Wh usable = "
          f"{r['percent_of_trip']:.1f} % of the {r['trip_wh']:.1f} Wh trip")
    print()
    print("  WITHDRAWN (one hop at 65 %, kept only to show what it was):")
    print(f"    {N_STOPS} x {r['ke_wh']:.4f} Wh x {WITHDRAWN_SINGLE_HOP:.2f} "
          f"= {r['single_hop_65_wh']:.2f} Wh")
    print()
    print(f"  VERDICT: the current model produces {r['total_wh']:.1f} Wh, so "
          f"{r['total_wh']:.1f} Wh is current and")
    print(f"           the 8.2 Wh single-hop figure is superseded. Both round")
    print(f"           to single-digit Wh and neither changes the verdict.")
    print()
    print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
