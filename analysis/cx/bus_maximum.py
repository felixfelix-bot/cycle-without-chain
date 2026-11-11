#!/usr/bin/env python3
"""CX-02: separate the bus's CHARGE ceiling from its STRESS ceiling.

WHY THIS EXISTS
---------------
``docs/design/open-gates-register.md`` CX-02 states the contradiction:

    The release contract freezes 58.4 V maximum normal charge; storage review
    says real series ceilings are 13x4.2 = 54.6 V and 16x3.6 = 57.6 V, not
    generic 58.4 V LFP charging
    Risk: charge control and clamp thresholds set against a voltage the chosen
    pack cannot reach
    Closes by: reconcile the bus maximum with the selected pack ceiling after
    ARCH-06

ARCH-06 is now decided (``storage-decision-lto.md``): 20s Toshiba SCiB LTO,
2.4 V nominal, 2.8 V maximum, giving a **56.0 V** pack ceiling.

THE FINDING
-----------
The contradiction cannot be resolved by picking 56.0 V, because 58.4 V is doing
**two different jobs** in the corpus and only one of them is a charge target:

1. **CHARGE ceiling** — the highest voltage the pack may be charged to. For 20s
   LTO this is **56.0 V**. Using 58.4 V here is simply wrong: it describes a
   16s LFP string nobody selected, and asking a charger for it on a 56.0 V pack
   is an overcharge command.

2. **STRESS ceiling** — the highest voltage the DC-link components must survive.
   This is **not** the pack ceiling and never was. The pack cannot bound the bus
   because:

   - a spinning PM machine rectifies through MOSFET body diodes with the pack
     contactor open, so the machine charges the bus regardless of pack state;
   - the chopper deliberately holds the bus *above* the pack (it can only sink
     current), so during a full-pack descent the bus sits at the chopper's hold
     level, not at pack voltage.

   The binding number here is the chopper trip band from CX-01:
   **turn-on 59.315-61.226 V**, **turn-off 57.356-59.058 V**. Components must
   survive the *top* of that band plus overshoot, not 58.4 V.

So 58.4 V is wrong as a charge ceiling (too high for a 56.0 V pack) and also
wrong as a stress ceiling (too low — the bus legitimately goes above it). One
number was being asked to be both, and it is neither.

THE CONSEQUENCE WORTH KNOWING
-----------------------------
Chopper turn-off floor is **57.356 V**; a full 20s LTO pack is **56.0 V**. Once
the chopper has conducted it holds the bus at or above 57.356 V, which is
**1.356 V above** what the pack can accept. During a full-pack descent:

- the pack accepts **zero** charge,
- the dump resistor carries **100 %** of regen,
- and this is not the fallback path, it is the primary path.

That is a real design statement, not a rounding argument. A design that assumes
the battery absorbs descents is wrong for this pack; the dump resistor and its
thermal rating are load-bearing, which is why BRK-01/PROT-09 stay open.

WHAT THIS IS NOT
----------------
- Not a decision to change the thresholds. Choosing 56.0 V as the charge limit
  and a stress limit above 61.226 V is the *next* step and belongs to the
  operator, because the stress ceiling interacts with TVS choice, capacitor
  class and the leak clamp that does not exist yet.
- Not a transient analysis. Ringing, cable inductance and BMS-open energy are
  PROT-04/PROT-08 territory and remain open.
- Not measured. Every number is a datasheet or published-arithmetic limit.
"""

from __future__ import annotations

# --- selected storage, from storage-decision-lto.md (ARCH-06, decided) -----
LTO_CELLS_SERIES = 20
LTO_V_NOMINAL = 2.4
LTO_V_MAX = 2.8
LTO_V_MIN = 1.8

# --- chopper trip bands, from CX-01 (0.55 V comparator-low corner) ---------
CHOPPER_ON_MIN = 59.315
CHOPPER_ON_MAX = 61.226
CHOPPER_OFF_MIN = 57.356
CHOPPER_OFF_MAX = 59.058

# --- the disputed contract figure -----------------------------------------
CONTRACT_BUS_MAX = 58.4

# --- previous candidates named in the register ----------------------------
LI_ION_13S_MAX = 13 * 4.2      # 54.6
LFP_16S_MAX = 16 * 3.65        # 58.4  <- where the number came from


def pack_ceiling_v(cells: int = LTO_CELLS_SERIES,
                   v_max: float = LTO_V_MAX) -> float:
    """Highest voltage the selected pack may be charged to."""
    if cells <= 0:
        raise ValueError("cell count must be positive")
    if v_max <= 0:
        raise ValueError("cell maximum must be positive")
    return cells * v_max


def pack_nominal_v(cells: int = LTO_CELLS_SERIES,
                   v_nom: float = LTO_V_NOMINAL) -> float:
    return cells * v_nom


def pack_floor_v(cells: int = LTO_CELLS_SERIES,
                 v_min: float = LTO_V_MIN) -> float:
    return cells * v_min


def charge_headroom_v(pack_v: float,
                      chopper_on_min: float = CHOPPER_ON_MIN) -> float:
    """Voltage the bus may rise before the chopper starts sinking.

    This is the window in which the bus has somewhere to go. It is NOT the same
    as the pack accepting charge: a pack sitting at its own ceiling has
    headroom for the bus to rise, yet accepts no current. Use
    ``pack_absorbs_regen`` for the actual question.
    """
    return chopper_on_min - pack_v


def pack_absorbs_regen(pack_v: float,
                       pack_ceiling_v_: float | None = None,
                       chopper_on_min: float = CHOPPER_ON_MIN) -> bool:
    """True only if the pack is below its own ceiling AND the bus may rise.

    Both conditions are required. A pack at its ceiling cannot take charge no
    matter how much bus headroom exists, because the excess current has nowhere
    to go except the dump resistor.
    """
    ceiling = pack_ceiling_v() if pack_ceiling_v_ is None else pack_ceiling_v_
    if pack_v >= ceiling:
        return False
    return charge_headroom_v(pack_v, chopper_on_min) > 0.0


def chopper_holds_above_pack_v(pack_v: float,
                               chopper_off_min: float = CHOPPER_OFF_MIN) -> float:
    """How far above the pack the chopper holds the bus once it conducts.

    Positive means the bus cannot return to pack voltage while the chopper is
    regulating, so the pack is out of the circuit for that interval.
    """
    return chopper_off_min - pack_v


def ratio_bound(sense_mv: float, v_trip: float) -> float:
    """Divider ratio needed for a given trip point at a given reference."""
    if v_trip <= 0:
        raise ValueError("trip voltage must be positive")
    return v_trip / (sense_mv / 1000.0)


def stress_ceiling_v() -> float:
    """Lowest defensible stress ceiling: the top of the chopper trip band.

    Anything rated below this is rated below the bus's own regulation point.
    Overshoot and ringing are NOT included; this is a floor, not a margin.
    """
    return CHOPPER_ON_MAX


def main() -> None:
    ceiling = pack_ceiling_v()
    print("CX-02  bus maximum: charge ceiling vs stress ceiling")
    print("=" * 74)
    print()
    print("1. What the number was derived from")
    print(f"   16s LFP at 3.65 V/cell  = {LFP_16S_MAX:.1f} V   <- the 58.4 figure")
    print(f"   13s Li-ion at 4.2 V/cell = {LI_ION_13S_MAX:.1f} V")
    print(f"   Neither is the selected storage.")
    print()
    print("2. What the selected storage actually is (ARCH-06: 20s LTO)")
    print(f"   {LTO_CELLS_SERIES}s x {LTO_V_MAX} V max  = {ceiling:.1f} V  CHARGE ceiling")
    print(f"   {LTO_CELLS_SERIES}s x {LTO_V_NOMINAL} V nom = {pack_nominal_v():.1f} V")
    print(f"   {LTO_CELLS_SERIES}s x {LTO_V_MIN} V min  = {pack_floor_v():.1f} V  floor")
    print()
    print(f"   58.4 V on this pack would be {CONTRACT_BUS_MAX - ceiling:+.1f} V "
          f"= {CONTRACT_BUS_MAX / ceiling - 1:+.1%} overcharge command")
    print()
    print("3. The pack cannot bound the bus")
    print(f"   chopper turn-on band   {CHOPPER_ON_MIN:.3f} - {CHOPPER_ON_MAX:.3f} V")
    print(f"   chopper turn-off band  {CHOPPER_OFF_MIN:.3f} - {CHOPPER_OFF_MAX:.3f} V")
    print(f"   stress ceiling (floor of) {stress_ceiling_v():.3f} V")
    print(f"   58.4 V is BELOW the chopper's own regulation point, so it cannot")
    print(f"   be the stress ceiling either.")
    print()
    print("4. Regen absorption across pack state")
    print("   pack V   headroom to chopper   chopper holds above pack   absorbs?")
    for pack_v in (pack_floor_v(), 44.0, 48.0, 52.0, ceiling):
        hr = charge_headroom_v(pack_v)
        hold = chopper_holds_above_pack_v(pack_v)
        absorbs = "yes" if pack_absorbs_regen(pack_v, ceiling) else "NO"
        print(f"   {pack_v:6.1f}   {hr:+8.3f} V          {hold:+8.3f} V"
              f"              {absorbs}")
    print()
    print(f"   At full charge the chopper holds the bus {chopper_holds_above_pack_v(ceiling):+.3f} V")
    print("   above what the pack can accept. The dump resistor carries all")
    print("   regen; the pack carries none. That is the primary path, not a")
    print("   fallback.")
    print()
    print("5. Divider ratios if the thresholds are re-referenced to 2.5 V")
    for v in (56.0, 59.315, 61.226, 64.0):
        print(f"   trip {v:6.2f} V -> ratio {ratio_bound(2500, v):6.3f}")
    print()
    print("VERDICT: 58.4 V cannot be reconciled to a single number because it")
    print("was never one quantity. The charge ceiling becomes 56.0 V (20s LTO).")
    print("The stress ceiling must be at or above the chopper's top trip band,")
    print(f"i.e. >= {stress_ceiling_v():.3f} V before overshoot. Choosing the")
    print("stress number is an operator decision because it sets TVS clamp,")
    print("capacitor class and the leak-clamp level, none of which exist yet.")


if __name__ == "__main__":
    main()
