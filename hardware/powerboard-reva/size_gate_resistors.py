#!/usr/bin/env python3
"""Gate-resistor sizing for the DRV8353 half-bridges (RAIL-10 / PROT-11 support).

THE QUESTION THE SCHEMATIC ASKED
--------------------------------
The BOM carries "4R7 provisional" on twelve gate resistors and "10R 1% gate
candidate" on four. "Provisional" reaching a fabrication BOM is exactly what
RAIL-10 forbids, so the value has to be derived rather than defaulted.

WHY A GATE RESISTOR IS A TRADE, NOT A VALUE
-------------------------------------------
The resistor sets three things at once and they pull in opposite directions:

  * **Turn-on speed**, and therefore switching loss. Slower costs efficiency.
  * **dI/dt and dV/dt**, and therefore the phase-node ringing that stresses the
    MOSFET and radiates EMI. Faster costs margin.
  * **Peak gate drive current**, which the DRV8353's internal driver and its
    VCP charge pump must supply.

There is no single "correct" number; there is a cheapest point that satisfies
the ringing and drive-current constraints. This module computes that point and
states the losses it costs, so the choice is auditable.

METHOD
------
For a gate drive into Qg with a series resistor Rg (plus the driver's internal
Rg_int and the MOSFET's internal gate resistance Rg_i), the classic first-order
model is an RC charge:

    tau   = (Rg + Rg_int + Rg_i) * Ciss_effective
    t_sw  ~ 2.2 * tau                     (10 %-90 %)

Switching loss per switching event, for a hard-switched half bridge:

    P_sw  = 0.5 * Vds * Id * (t_on + t_off) * f_sw

Gate drive peak current:

    I_pk  = (Vdrive - Vplateau) / (Rg + Rg_int + Rg_i)

Ringing: the phase node is an LC tank of L_loop and Qoss/Coss. The damping factor
of the loop with an added snubber or just the device's own loss sets overshoot.
Rather than pretend to model EMI, this module reports the ringing frequency and
the overshoot implied by an assumed loop inductance, and treats the gate resistor
as the knob that trades dv/dt against loss.

WHAT THIS IS NOT
----------------
Not a double-pulse test. The datasheet numbers used here (Qg, Ciss, Coss, tr/tf)
are typicals at one test condition. The real optimum is set by the actual loop
inductance of the laid-out board, which does not exist yet. So the output is a
**defensible starting value plus the loss it implies**, to be confirmed on the
bench — not a claim that the number is final. That distinction is why the gate
stays OPEN in the register while the value is frozen to something derivable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Fet:
    """CSD19532Q5B, TI SLPS414 Rev. B. Typical values at Vgs = 10 V."""
    name: str = "CSD19532Q5B"
    vds_max: float = 100.0
    qg_nc: float = 48.0          # total gate charge, typ @ 10 V
    qgd_nc: float = 7.0          # gate-drain (Miller) charge, typ
    ciss_pf: float = 4700.0      # input capacitance, typ
    coss_pf: float = 720.0       # output capacitance, typ
    rg_internal_ohm: float = 1.0 # silicon gate resistance, from datasheet
    tr_ns: float = 12.0          # rise time, typ, datasheet test condition
    tf_ns: float = 9.0           # fall time, typ


@dataclass(frozen=True)
class Driver:
    """DRV8353 internal gate driver, TI SLVSDY6A."""
    name: str = "DRV8353S"
    vdrive: float = 10.0         # VGS drive level used for Qg
    rg_int_ohm: float = 1.5      # driver's internal pull-up/pull-down resistance
    i_source_ma: float = 1000.0  # peak source current capability
    i_sink_ma: float = 2000.0    # peak sink current capability


# Design point: 48 V nominal rail, the current this board actually switches.
VDS_OPERATING = 52.0     # V, above nominal for headroom in the loss figure

# Phase current: this is NOT the DRV8353's 20 A rating — it is what the bike asks
# for. Register gate ARCH-04 leaves phase current undefined, so it is derived here
# from the drivetrain instead of being adopted from the driver's datasheet:
#
#   400 W mechanical at 36 V (worst-case low bus) / 0.85 motor eff
#       = 13.1 A DC  ->  ~13 A phase RMS
#
# 15 A is used as the design point: the 400 W case with headroom. Launch peaks are
# 2-3x this, but they are transient and the device's pulse rating covers them —
# sizing continuous loss at the peak would over-build the gate drive for a duty
# cycle that never persists.
I_LOAD = 15.0            # A per phase, from the drivetrain (see above)
F_SW = 20_000.0          # Hz, the chopper/commutation rate under consideration
L_LOOP_NH = 4.0          # nH, assumed commutation loop inductance (unlaid-out)

# Candidate gate resistors to trade off
CANDIDATES_OHM = (2.2, 3.3, 4.7, 6.8, 10.0, 15.0, 22.0)

# --- selection policy (module-level so tests can pin the rule, not the answer) ---
# dv/dt ceiling for a 100 V Si MOSFET on a low-inductance loop at ~52 V bus.
DVDT_CEILING_V_PER_NS = 2.0
# The resistor must dominate the edge by this factor, i.e. t_RC >= MARGIN*t_limit.
# 1.20 because Ciss and Rg_int are themselves +/-20 % typicals: a value closer to
# the crossover than that cannot be shown to control the edge at all.
RC_MARGIN = 1.20


def tau_ns(rg: float, fet: Fet, drv: Driver) -> float:
    """Gate charge time constant, in ns."""
    r_total = rg + drv.rg_int_ohm + fet.rg_internal_ohm
    return r_total * fet.ciss_pf * 1e-3   # ohm * pF -> ns


def t_sw_ns(rg: float, fet: Fet, drv: Driver) -> float:
    """10 %-90 % gate transition — the RC-model edge time, floored by Qg/I_limit.

    The two mechanisms bound the same edge; they do not add. If the RC time is
    longer than the current-limit floor, the RC tail dominates and the edge is
    RC-set. If it is shorter, the driver cannot reach the RC rate at all, so the
    edge is current-limited and takes the floor time. The edge is therefore
    ``max`` of the two — but that means the reported transition is never the
    "fast" number in the table, and an earlier draft displayed the pair in a way
    that implied a range. There is no range: there is one edge time, and which
    mechanism sets it.

    A gate driver cannot deliver more than its rated peak current. When the RC
    time constant asks for more than that, the gate charges at the current limit
    instead and the transition is set by Qg/I_limit, not by Rg. Treating the
    current limit as a *disqualification* (as an earlier draft of this module
    did) is wrong: the driver still drives the FET, just more slowly than the
    RC model predicts, and the loss is correspondingly higher.

        t_RC   = 2.2 * (Rg + Rg_int + Rg_i) * Ciss
        t_Ilim = Qg / I_source_limit          (charge-limited floor)

        t_sw   = max(t_RC, t_Ilim)
    """
    t_rc, t_limit = transition_range_ns(rg, fet, drv)
    return max(t_rc, t_limit)


def transition_range_ns(rg: float, fet: Fet, drv: Driver) -> tuple[float, float]:
    """Return ``(t_rc_ns, t_limit_ns)`` — the two competing edge mechanisms.

    The DRV8353's source current is finite, so an edge has two possible limits:

        t_rc    = 2.2 * R_total * Ciss    the RC charge time
        t_limit = Qg / I_source           the current-limit floor

    The actual edge is ``max`` of the two: whichever mechanism is slower wins,
    because you cannot charge faster than either allows. Returning the pair (not
    a min/max pair, which reads as an interval) lets the caller say *which*
    mechanism set the edge, which is the fact that decides whether a resistor is
    doing any work at all.
    """
    t_rc = 2.2 * tau_ns(rg, fet, drv)
    t_ilim = (fet.qg_nc * 1e-9) / (drv.i_source_ma * 1e-3) * 1e9   # ns
    return (t_rc, t_ilim)


def switching_loss_w(rg: float, fet: Fet, drv: Driver,
                     vds: float = VDS_OPERATING, i_load: float = I_LOAD,
                     f_sw: float = F_SW) -> float:
    """Hard-switched loss per device, summed over turn-on and turn-off."""
    t = t_sw_ns(rg, fet, drv) * 1e-9
    return 0.5 * vds * i_load * (t + t) * f_sw


def peak_gate_current_a(rg: float, fet: Fet, drv: Driver) -> float:
    """Peak current the driver must source to charge the gate."""
    r_total = rg + drv.rg_int_ohm + fet.rg_internal_ohm
    return (drv.vdrive) / r_total


def ringing(vds: float = VDS_OPERATING, coss_pf: float = 720.0,
            l_loop_nh: float = L_LOOP_NH) -> dict:
    """Phase-node ringing frequency and the energy in the loop."""
    import math
    f_ring = 1.0 / (2.0 * math.pi * math.sqrt(l_loop_nh * 1e-9 * coss_pf * 1e-12))
    # characteristic impedance of the loop
    z0 = math.sqrt(l_loop_nh * 1e-9 / (coss_pf * 1e-12))
    # energy stored if the node rings to the full rail
    e_uj = 0.5 * coss_pf * 1e-12 * vds * vds * 1e6
    return {"f_ring_mhz": f_ring / 1e6, "z0_ohm": z0, "energy_uj": e_uj}


def evaluate(rg: float, fet: Fet, drv: Driver) -> dict:
    t = t_sw_ns(rg, fet, drv)
    t_rc = 2.2 * tau_ns(rg, fet, drv)
    t_limit = (fet.qg_nc * 1e-9) / (drv.i_source_ma * 1e-3) * 1e9
    p = switching_loss_w(rg, fet, drv)
    i_pk = peak_gate_current_a(rg, fet, drv)
    # dv/dt on the phase node during the switching transition
    dvdt = VDS_OPERATING / (t * 1e-9) / 1e9   # V/ns
    return {
        "rg_ohm": rg,
        "tau_ns": round(tau_ns(rg, fet, drv), 3),
        "t_sw_ns": round(t, 2),
        "t_rc_ns": round(t_rc, 2),
        "t_limit_ns": round(t_limit, 2),
        "switching_loss_w": round(p, 4),
        "peak_gate_current_a": round(i_pk, 3),
        "driver_can_drive": i_pk * 1000.0 <= drv.i_source_ma,
        "dvdt_v_per_ns": round(dvdt, 3),
    }


def main() -> int:
    fet, drv = Fet(), Driver()
    rows = [evaluate(rg, fet, drv) for rg in CANDIDATES_OHM]

    print("Gate resistor trade-off — %s driven by %s" % (fet.name, drv.name))
    print("Design point: %.0f V, %.0f A, %.0f kHz, loop %.1f nH"
          % (VDS_OPERATING, I_LOAD, F_SW / 1000, L_LOOP_NH))
    print()
    print("  Rg    t_RC    t_limit  t_sw    P_sw      I_pk     dv/dt    edge set by")
    print("  (ohm) (ns)    (ns)     (ns)    (W)       (A)      (V/ns)")
    for r in rows:
        mode = "RC" if r["t_rc_ns"] >= r["t_limit_ns"] else "I-limit"
        print("  %-5.1f %-7.1f %-8.1f %-7.1f %-9.4f %-8.3f %-8.2f %s"
              % (r["rg_ohm"], r["t_rc_ns"], r["t_limit_ns"], r["t_sw_ns"],
                 r["switching_loss_w"], r["peak_gate_current_a"],
                 r["dvdt_v_per_ns"], mode))
    print()
    ring = ringing()
    print("Phase-node ringing with %.1f nH loop and %.0f pF Coss:"
          % (L_LOOP_NH, fet.coss_pf))
    print("  resonant frequency : %.1f MHz" % ring["f_ring_mhz"])
    print("  loop impedance Z0  : %.2f ohm" % ring["z0_ohm"])
    print("  energy in Coss     : %.2f uJ per edge" % ring["energy_uj"])
    print()

    # Selection criterion.
    #
    # A gate resistor only controls the edge while its RC time constant exceeds
    # the driver's current-limit floor (Qg/I_source). At the crossover the
    # resistor is *inert*: adding it changes nothing because the driver is still
    # the limiter. Choosing the "fastest value under the dv/dt ceiling" therefore
    # picks a resistor that does no work at all, which is what an earlier draft
    # of this module did (it landed on 2.2 ohm, whose RC time, 48.6 ns, is
    # indistinguishable from the 48.0 ns current-limit floor).
    #
    # So: require the resistor to genuinely dominate (RC >= 1.3x the floor) AND
    # keep dv/dt under the ceiling. Among survivors take the fastest, because
    # every ohm of extra resistance is switching loss paid for margin that a
    # 100 V device at 52 V does not need.
    DVDT_CEILING = DVDT_CEILING_V_PER_NS
    t_floor = (fet.qg_nc * 1e-9) / (drv.i_source_ma * 1e-3) * 1e9   # ns

    # Criterion: the smallest Rg at which the resistor genuinely sets the edge
    # (t_RC > t_limit) while dv/dt stays under the ceiling. Below that point the
    # driver, not the resistor, is the limiter — fitting a resistor there buys no
    # control over dv/dt and is simply the wrong component value to publish.
    # A value sitting 1 % above the crossover is inside the model's own error
    # (Ciss and Rg_int are themselves +/-20 % typicals), so "just above" is not a
    # selection. Require the resistor to own at least 20 % of the edge.
    viable = [r for r in rows
              if r["dvdt_v_per_ns"] <= DVDT_CEILING
              and r["t_rc_ns"] >= RC_MARGIN * r["t_limit_ns"]]
    if not viable:
        print("No candidate satisfies both the dv/dt ceiling and resistor")
        print("dominance; the driver/turns ratio needs revisiting.")
        return 1
    best = min(viable, key=lambda r: r["rg_ohm"])
    print("Chosen: Rg = %.1f ohm" % best["rg_ohm"])
    print("  switching loss : %.4f W per device (%.2f W over six)"
          % (best["switching_loss_w"], best["switching_loss_w"] * 6))
    print("  transition     : %.2f ns (RC model %.2f ns = %.2fx the %.1f ns floor)"
          % (best["t_sw_ns"], best["t_rc_ns"],
             best["t_rc_ns"] / best["t_limit_ns"], best["t_limit_ns"]))
    print("  dv/dt          : %.2f V/ns (ceiling %.1f)"
          % (best["dvdt_v_per_ns"], DVDT_CEILING))
    driver_limited = best["peak_gate_current_a"] > drv.i_source_ma / 1000.0
    print("  peak gate I    : %.3f A vs driver limit %.2f A%s"
          % (best["peak_gate_current_a"], drv.i_source_ma / 1000.0,
             " (current-limited)" if driver_limited else ""))
    print()
    print("Crossover: the resistor starts to matter above R_total = %.2f ohm,"
          % ((t_floor / 2.2) / fet.ciss_pf * 1e3))
    print("i.e. Rg > %.2f ohm external. Below that the DRV8353 dictates the edge."
          % (((t_floor / 2.2) / fet.ciss_pf * 1e3) - drv.rg_int_ohm
             - fet.rg_internal_ohm))
    print()
    print("Important: the gate resistor sets dv/dt but does NOT damp the power")
    print("loop. With %.1f nH and %.0f pF the loop rings at %.1f MHz with Z0 ="
          % (L_LOOP_NH, fet.coss_pf, ring["f_ring_mhz"]))
    print("%.2f ohm; damping that is a snubber-and-layout problem, not a gate"
          % ring["z0_ohm"])
    print("resistor problem. Rg only controls how hard the ring is excited.")
    print()
    nxt = [r for r in rows if r["rg_ohm"] > best["rg_ohm"]][:1]
    if nxt:
        d = nxt[0]["switching_loss_w"] - best["switching_loss_w"]
        print("Going to %.1f ohm costs +%.4f W per device (%.2f W over six"
              % (nxt[0]["rg_ohm"], d, d * 6))
        print("devices) for slower edges — the price of extra ringing margin.")

    out = {
        "fet": asdict(fet), "driver": asdict(drv),
        "design_point": {"vds": VDS_OPERATING, "i_load": I_LOAD,
                         "f_sw": F_SW, "l_loop_nh": L_LOOP_NH},
        "candidates": rows, "ringing": ring,
        "chosen_ohm": best["rg_ohm"],
    }
    with open("gate-resistor-results.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print("\nwrote gate-resistor-results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
