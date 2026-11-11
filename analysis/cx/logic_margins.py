#!/usr/bin/env python3
"""PROT-03: per-path logic-level budget for the safety chain.

WHY THIS EXISTS
---------------
``docs/design/open-gates-register.md`` PROT-03 says the logic margins are not
closed, on the evidence that:

    LM339B VOL 400 mV at 25 C and 550 mV over -40...85 C at 4 mA, BAT54WS
    0.32 V at 1 mA, DRV nFAULT 0.125 V, TPS382x 0.4 V, HC thresholds
    specified only at 2/4.5/6 V
    "VOL-plus-diode sums above the logic low threshold at a cold or
    low-supply corner"

Two parts of that premise are now stale against the schematic in
``hardware/powerboard-reva/``:

1. **The series diodes are gone from the fault bus.** ``protection_circuit.py``
   names the sheet ``fault-interfaces`` with the on-sheet text "LVC Schmitt fault
   inputs without series diode offsets". The BAT54WS parts still in the tree are
   in ``brake_intent_circuit.py`` and ``fsr_circuit.py`` as analog clamps, not in
   the fault path. So the 0.445 V (nFAULT + diode) and 0.72 V (supervisor +
   diode) screening sums do not describe this design.

2. **The logic is LVC, not HC.** ``U7``/``U8`` SN74LVC1G74, ``U11``/``U12``
   SN74LVC3G17 (Schmitt buffer), ``U13``/``U14``/``U16`` SN74LVC1G11,
   ``U15`` SN74LVC1G04. "HC thresholds specified only at 2/4.5/6 V" no longer
   applies.

The gate offers a choice: *"per-path budget with temperature, sink current and
leakage, else a Schmitt or interface stage."* The design has already taken the
second option for the fault bus. What has never been done is the arithmetic that
shows the chosen interface actually works at the corner. That is what this
module does, and it is the reason the gate can move from "no budget exists" to a
stated per-path result.

WHAT THIS IS NOT
----------------
- Not a measurement, and not proof of correct behaviour with a rail absent or
  ramping. Supply-permutation and backfeed behaviour is PROT-04 and stays open.
- Not an edge-rate or metastability qualification. An LVC Schmitt has hysteresis
  but no guaranteed behaviour for arbitrarily slow edges near the threshold;
  that is a timing question, not a DC one.
- Not a claim that 290 mV of DC margin is comfortable. It is a number, and the
  smallest one in the chain is reported as such rather than averaged away.

THE PATHS
---------
Four paths carry a low from an open-drain driver into a CMOS input:

  A  ANALOG_OK   : U6 LM339B OUT -> U11 LVC3G17 1A   (4k7 pullup to SAFETY3V3)
  B  GEN_nFAULT : U1 DRV8353 nFAULT -> U11 LVC3G17 2A (10k pullup)
  C  WD_RESET_N : U9 TPS3823 RESET_N -> U11 LVC3G17 3A (10k pullup)
  D  OV_CMD     : U6 LM339B OUT -> U10 UCC27511 IN+ (1k pullup)

Pin assignment verified against protection_circuit.py: U11's net list is
1A=ANALOG_OK, 3Y=WD_OK, 2A=GEN_nFAULT, 2Y=GEN_OK, 3A=WD_RESET_N,
1Y=ANALOG_CLEAN. The same DRV8353 nFAULT reasoning applies to HUB_nFAULT on
U12 pin 1A.

Path D is the one that matters most: it drives the brake chopper. It is the only
path whose receiver is not a Schmitt input, so it uses the UCC27511 VIN_L limit
rather than the LVC VT- limit.

DRIVEN LIMITS, ALL FROM PRIMARY DATASHEETS FETCHED FOR THIS AUDIT
-----------------------------------------------------------------
- LM339B VOL max **550 mV**, ISINK <= 4 mA, VID = -1 V, TA = -40...+85 C
  (TI SLCS006 / lm339b, section 6.7 "Electrical Characteristics for LM339B").
  NOTE: the 700 mV row in the same datasheet belongs to the legacy LMx39/LMx39A
  table (section 6.10), not to the LM339B. Using 700 mV here would be wrong in
  the pessimistic direction but would misattribute the part.
- DRV8353 nFAULT VOL max **125 mV** at IO = 5 mA (SLVSDY6A, open-drain outputs).
- TPS3823-33 RESET VOL max **0.4 V** at IOL = 1.2 mA, VDD = VIT- - 0.2 V.
- SN74LVC3G17 at VCC = 3 V: VT- MIN **0.84 V**, MAX 1.14 V; VT+ MIN 1.5 V
  (SCES470F). At VCC = 2.3 V: VT- 0.58-0.87 V. Guaranteed-to-be-read-as-low
  means below VT- *minimum*, which is the pessimistic column.
- UCC27511: VIN_L MIN **1.0 V**, MAX 1.2 V; VIN_H MIN 2.2 V, MAX 2.4 V.
- SN74LVC1G11 at VCC = 3-3.6 V: VIH min 2 V, VIL max 0.8 V (SCES487I).
"""

from __future__ import annotations

# --- receiver limits -------------------------------------------------------
# LVC Schmitt: an input is guaranteed LOW only below VT- MIN.
LVC3G17_VT_MINUS_AT_3V0 = 0.84     # V, SCES470F, -40..85 C
LVC3G17_VT_MINUS_AT_2V3 = 0.58
LVC3G17_VT_PLUS_MIN_AT_3V0 = 1.50  # guaranteed HIGH above VT+ MAX is wrong:
LVC3G17_VT_PLUS_MAX_AT_3V0 = 1.87  # HIGH needs above VT+ MAX
# UCC27511 non-Schmitt input
UCC27511_VIN_L_MIN = 1.00
UCC27511_VIN_H_MAX = 2.40
# LVC gate (non-Schmitt) worst-case DC levels
LVC1G11_VIL_MAX_AT_3V0 = 0.80
LVC1G11_VIH_MIN_AT_3V0 = 2.00

# --- driver low-level limits ----------------------------------------------
LM339B_VOL_MAX = 0.550        # at ISINK <= 4 mA, full -40..85 C
LM339B_VOL_MAX_25C = 0.400    # 25 C column
DRV8353_NFAULT_VOL_MAX = 0.125  # at 5 mA
TPS3823_VOL_MAX = 0.400        # at 1.2 mA

# --- pullups as fitted -----------------------------------------------------
R_PULLUP_ANALOG_OK = 4_700.0
R_PULLUP_NFAULT = 10_000.0
R_PULLUP_RESET = 10_000.0
R_PULLUP_OV_CMD = 1_000.0

# --- rail ---------------------------------------------------------------
SAFETY3V3_NOM = 3.30
SAFETY3V3_TOL = 0.04      # assumed regulator tolerance; not a datasheet limit
SAFETY3V3_MIN = SAFETY3V3_NOM * (1 - SAFETY3V3_TOL)


def supply_min_v(tol: float = SAFETY3V3_TOL,
                 nom: float = SAFETY3V3_NOM) -> float:
    """Lowest assumed SAFETY3V3. A tolerance, not a guaranteed regulator spec."""
    return nom * (1 - tol)


def pullup_current_a(r_pullup_ohm: float, v_low: float = 0.0,
                     v_rail: float | None = None) -> float:
    """Worst-case sink current through the pullup when the driver pulls low."""
    rail = supply_min_v() if v_rail is None else v_rail
    if r_pullup_ohm <= 0:
        raise ValueError("pullup must be positive")
    return max(0.0, (rail - v_low) / r_pullup_ohm)


def logic_low_margin_v(driver_vol_max: float, receiver_low_limit: float) -> float:
    """Positive margin means the driver's worst-case low is still read as low."""
    return receiver_low_limit - driver_vol_max


def logic_high_margin_v(v_rail: float, r_pullup_ohm: float,
                        leakage_a: float, receiver_high_min: float) -> float:
    """Open-drain high: rail minus the drop across the pullup from leakage."""
    v_high = v_rail - leakage_a * r_pullup_ohm
    return v_high - receiver_high_min


PATHS = (
    # name, driver VOL max, receiver low limit, pullup, receiver name
    ("ANALOG_OK -> U11 1A", LM339B_VOL_MAX, LVC3G17_VT_MINUS_AT_3V0,
     R_PULLUP_ANALOG_OK, "LVC3G17 VT-(min) @3.0V"),
    ("GEN_nFAULT -> U11 2A", DRV8353_NFAULT_VOL_MAX, LVC3G17_VT_MINUS_AT_3V0,
     R_PULLUP_NFAULT, "LVC3G17 VT-(min) @3.0V"),
    ("HUB_nFAULT -> U12 1A", DRV8353_NFAULT_VOL_MAX, LVC3G17_VT_MINUS_AT_3V0,
     R_PULLUP_NFAULT, "LVC3G17 VT-(min) @3.0V"),
    ("WD_RESET_N -> U11 3A", TPS3823_VOL_MAX, LVC3G17_VT_MINUS_AT_3V0,
     R_PULLUP_RESET, "LVC3G17 VT-(min) @3.0V"),
    ("OV_CMD -> U10 IN+", LM339B_VOL_MAX, UCC27511_VIN_L_MIN,
     R_PULLUP_OV_CMD, "UCC27511 VIN_L(min)"),
)


def path_budget() -> list[dict]:
    """Per-path DC low-level budget at the cold corner."""
    out = []
    for name, vol, limit, r_pu, recv in PATHS:
        out.append({
            "path": name,
            "driver_vol_max": vol,
            "receiver_low_limit": limit,
            "pullup_ohm": r_pu,
            "sink_ma": pullup_current_a(r_pu) * 1e3,
            "margin_v": logic_low_margin_v(vol, limit),
            "receiver": recv,
        })
    return out


def worst_path() -> dict:
    """The path with the least low-level margin."""
    return min(path_budget(), key=lambda p: p["margin_v"])


def main() -> None:
    print("PROT-03  per-path logic-level budget, cold corner")
    print("=" * 78)
    print()
    print("SAFETY3V3 assumed minimum:", f"{supply_min_v():.3f} V",
          f"({SAFETY3V3_TOL * 100:.0f}% tolerance assumed, not a datasheet limit)")
    print()
    print("LOW LEVEL  (driver pulls down; receiver must read it as low)")
    hdr = ("path", "VOL max", "receiver limit", "sink", "margin")
    print(f"  {hdr[0]:<26} {hdr[1]:>8} {hdr[2]:>15} {hdr[3]:>8} {hdr[4]:>9}")
    for p in path_budget():
        print(f"  {p['path']:<26} {p['driver_vol_max']:>6.3f} V"
              f" {p['receiver_low_limit']:>13.2f} V"
              f" {p['sink_ma']:>6.2f} mA"
              f" {p['margin_v'] * 1e3:>6.0f} mV")
    w = worst_path()
    print()
    print(f"  Tightest path: {w['path']} at {w['margin_v'] * 1e3:.0f} mV margin.")
    print()
    print("HIGH LEVEL  (open drain released; leakage drop across the pullup)")
    print("  LM339B IOH leakage max 50 nA, DRV8353 IOZ, TPS3823 output leakage:")
    for name, r_pu, recv, lim in (
        ("ANALOG_OK -> LVC3G17", R_PULLUP_ANALOG_OK, "LVC3G17 VT+(max) @3.0V",
         LVC3G17_VT_PLUS_MAX_AT_3V0),
        ("OV_CMD -> UCC27511 IN+", R_PULLUP_OV_CMD, "UCC27511 VIN_H(max)",
         UCC27511_VIN_H_MAX),
    ):
        m = logic_high_margin_v(supply_min_v(), r_pu, 50e-9, lim)
        print(f"  {name:<26} limit {lim:>5.2f} V   margin {m * 1e3:>6.0f} mV")
    print()
    print("WHAT CHANGED FROM THE REGISTER'S PREMISE")
    print("  - The fault bus has no series diode: the sheet is 'LVC Schmitt fault")
    print("    inputs without series diode offsets'. The 0.445 V / 0.72 V sums do")
    print("    not apply to this topology.")
    print("  - Logic is LVC, not HC, so the 2/4.5/6 V threshold complaint is moot.")
    print("  - All four paths pass on DC low level at the cold corner, the")
    print("    tightest by 290 mV.")
    print()
    print("WHAT THIS DOES NOT CLOSE")
    print("  - Rail-absent and ramping behaviour (PROT-04), edge rates and")
    print("    metastability, and any measured confirmation.")
    print("  - The 4% SAFETY3V3 tolerance is an assumption, not a regulator spec.")
    print("  - A 290 mV DC margin at 25 C is not the same as 290 mV over life;")
    print("    aging, contamination and injected noise all erode it and none is")
    print("    quantified here.")


if __name__ == "__main__":
    main()
