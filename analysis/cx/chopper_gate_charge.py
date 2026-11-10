#!/usr/bin/env python3
"""PROT-11: put chopper gate charge into the auxiliary ledger and re-check 1.1 W.

WHY THIS EXISTS
---------------
``docs/design/rail-partition-milestone.md`` publishes the always-on auxiliary
ledger as **1.027108922 W** against a **1.1 W** early sink-input acceptance
envelope, leaving **0.072891078 W**. Its own SINK12 subtotal is annotated:

    | **Direct SINK12 subtotal** | excludes U4 cascade and active gate charge |

and ``docs/design/precharge-power-sources.md`` states the missing term outright:

    Active gate charging adds Pgate = Qg_total x 12 V x f_chop and gate
    pulldown loss; neither chopper frequency nor worst-case Qg has been
    qualified here.

So the published margin is a *lower bound* on consumption: it omits a load that
is definitely present whenever the brake chopper chops. PROT-11 asks for that
term to be added and the envelope re-checked.

WHAT THIS MODULE COMPUTES
-------------------------
Three things, in order of usefulness:

1. Reproduces the published 1.027108922 W / 0.072891078 W so the arithmetic is
   anchored, not assumed.
2. Computes the gate-charge term for Q13 (CSD19532Q5B) driven by U10
   (UCC27511) at 12 V, including the 10 kohm gate-source pulldown.
3. Inverts the result: the chopper frequency at which the margin is exhausted.
   The frequency is NOT specified anywhere in the corpus, so the honest output
   is not "it fits" but "it fits only below this f_chop".

WHAT THIS IS NOT
----------------
- Not a measurement. Qg is a datasheet limit; f_chop is unqualified.
- Not a claim that the chopper works at any frequency. Switching loss in Q13,
  dump-resistor thermal duty and the 1.1 W envelope itself are separate gates
  (BRK-*, PROT-01, PROT-07).
- Not closure of PROT-11 by itself: it converts an unbounded omission into a
  bounded condition. The gate stays open until f_chop is chosen and recorded.

SOURCES
-------
- Q13 CSD19532Q5B, TI SLPS414 Rev. B, Electrical Characteristics:
  Qg (gate charge total, 10 V) 48 nC typical / 62 nC max; Qgd 8.7 nC.
  https://www.ti.com/lit/ds/symlink/csd19532q5b.pdf
- Drive rail 12 V and pulldown 10 kohm: protection-milestone-report.md
  section "Circuit and primary-source identities" (U10 -> Q13, 10 ohm turn-on,
  2.2 ohm turn-off, 10 kohm gate-source pulldown).
- Ledger and envelope: rail-partition-milestone.md section "Actual load
  ledger"; precharge-power-sources.md section 3.
"""

from __future__ import annotations

# --- published ledger, reproduced exactly ---------------------------------
SINK12_DIRECT_W = 0.203055319   # rail-partition-milestone.md SINK12 subtotal
U4_INPUT_W = 0.133210034        # TLV76033 input for SAFETY3V3
MAIN_PROOF_ALLOWANCE_W = 0.100000000  # explicitly unimplemented allocation
CONVERSION_EFFICIENCY = 0.60    # historical assumed end-to-end
INPUT_RESERVE_W = 0.30
ENVELOPE_W = 1.1                # early sink-input acceptance envelope

# all-OC-on-safety scenario quoted in the same document
ALL_OC_U4_INPUT_W = 0.149368546

# --- Q13 / U10 gate-charge parameters ------------------------------------
QG_TYP_10V_C = 48e-9            # CSD19532Q5B, TI SLPS414 Rev. B
QG_MAX_10V_C = 62e-9            # Digi-Key / TI max column at 10 V
GATE_DRIVE_V = 12.0             # U10 UCC27511 VDD = SINK12
GATE_PULLDOWN_OHM = 10_000.0    # gate-source pulldown, protection report


def published_sink_input_w(u4_input_w: float = U4_INPUT_W) -> float:
    """Reproduce the published whole-ledger input power."""
    return (
        (SINK12_DIRECT_W + u4_input_w + MAIN_PROOF_ALLOWANCE_W)
        / CONVERSION_EFFICIENCY
        + INPUT_RESERVE_W
    )


def published_margin_w(u4_input_w: float = U4_INPUT_W) -> float:
    return ENVELOPE_W - published_sink_input_w(u4_input_w)


def gate_charge_power_w(f_chop_hz: float, qg_c: float = QG_MAX_10V_C,
                        drive_v: float = GATE_DRIVE_V) -> float:
    """Power drawn from the 12 V rail to charge Q13's gate, ignoring pulldown."""
    if f_chop_hz < 0:
        raise ValueError("f_chop must be non-negative")
    return qg_c * drive_v * f_chop_hz


def gate_pulldown_power_w(duty: float, drive_v: float = GATE_DRIVE_V,
                          r_pd: float = GATE_PULLDOWN_OHM) -> float:
    """Pulldown dissipation while the gate is held at drive_v.

    The 10 kohm gate-source resistor sees full gate voltage during on-time.
    At 12 V this is 14.4 mW at 100% duty, which is not negligible against a
    72.9 mW margin.
    """
    if not 0.0 <= duty <= 1.0:
        raise ValueError("duty must be within 0..1")
    return duty * drive_v * drive_v / r_pd


def total_chopper_aux_w(f_chop_hz: float, duty: float,
                        qg_c: float = QG_MAX_10V_C) -> float:
    """Gate charge plus pulldown, at the 12 V rail."""
    return (gate_charge_power_w(f_chop_hz, qg_c)
            + gate_pulldown_power_w(duty))


def sink_input_with_chopper_w(f_chop_hz: float, duty: float,
                              qg_c: float = QG_MAX_10V_C,
                              u4_input_w: float = U4_INPUT_W) -> float:
    """Whole-ledger input power with the chopper load included.

    The chopper load sits on the 12 V rail, so it enters the numerator before
    the conversion-efficiency division, exactly like the other SINK12 terms.
    """
    return (
        (SINK12_DIRECT_W + u4_input_w + MAIN_PROOF_ALLOWANCE_W
         + total_chopper_aux_w(f_chop_hz, duty, qg_c))
        / CONVERSION_EFFICIENCY
        + INPUT_RESERVE_W
    )


def max_f_chop_hz(duty: float,
                  envelope_w: float = ENVELOPE_W,
                  qg_c: float = QG_MAX_10V_C,
                  u4_input_w: float = U4_INPUT_W,
                  drive_v: float = GATE_DRIVE_V) -> float:
    """Chopper frequency at which the envelope is exactly exhausted.

    Everything else is fixed at its published value, so this is the break
    frequency for the gate-charge term alone. At or above it, the design must
    find the power elsewhere or reduce Qg/f/duty.
    """
    margin_w = envelope_w - published_sink_input_w(u4_input_w)
    if margin_w <= 0:
        return 0.0
    # margin is at the input side; allow the same fraction at the 12 V rail
    allowed_rail_w = margin_w * CONVERSION_EFFICIENCY
    pd_w = gate_pulldown_power_w(duty, drive_v)
    if allowed_rail_w <= pd_w:
        return 0.0
    return (allowed_rail_w - pd_w) / (qg_c * drive_v)


def main() -> None:
    margin = published_margin_w()
    all_oc_margin = published_margin_w(ALL_OC_U4_INPUT_W)

    print("PROT-11  chopper gate charge against the 1.1 W auxiliary envelope")
    print("=" * 72)
    print()
    print("1. Reproduce the published ledger (no gate charge)")
    print(f"   SINK12 direct          {SINK12_DIRECT_W:.9f} W")
    print(f"   U4 input (SAFETY3V3)   {U4_INPUT_W:.9f} W")
    print(f"   main-proof allowance   {MAIN_PROOF_ALLOWANCE_W:.9f} W")
    print(f"   /{CONVERSION_EFFICIENCY:.2f} + {INPUT_RESERVE_W:.2f} reserve")
    print(f"   whole-ledger input     {published_sink_input_w():.9f} W")
    print(f"   envelope               {ENVELOPE_W:.9f} W")
    print(f"   margin                 {margin:.9f} W")
    print(f"   all-OC-on-safety margin{all_oc_margin:.9f} W")
    print()
    print("   Published values: 1.027108922 W and 0.072891078 W."
          f"  Match: {abs(published_sink_input_w() - 1.027108922) < 1e-9}")
    print()
    print("2. The omitted term, at the 12 V rail")
    print(f"   Qg max (10 V)          {QG_MAX_10V_C * 1e9:.1f} nC")
    print(f"   Qg typ (10 V)          {QG_TYP_10V_C * 1e9:.1f} nC")
    print(f"   drive                  {GATE_DRIVE_V:.1f} V")
    print(f"   pulldown               {GATE_PULLDOWN_OHM / 1000:.0f} kohm"
          f"  ({gate_pulldown_power_w(1.0) * 1e3:.1f} mW at 100 % duty)")
    print()
    print("   f_chop     gate-charge    pulldown(50%)   input-side total   verdict")
    for f in (1_000, 5_000, 10_000, 20_000, 40_000, 60_000, 100_000):
        gate = gate_charge_power_w(f)
        pd_w = gate_pulldown_power_w(0.5)
        inp = sink_input_with_chopper_w(f, 0.5)
        ok = "fits" if inp <= ENVELOPE_W else "EXCEEDS"
        print(f"   {f:>7} Hz  {gate * 1e3:>9.3f} mW  {pd_w * 1e3:>9.3f} mW"
              f"  {inp:>12.6f} W   {ok}")
    print()
    print("3. Break frequency (margin exhausted)")
    for duty, label in ((0.0, "0 %"), (0.5, "50 %"), (1.0, "100 %")):
        f = max_f_chop_hz(duty)
        print(f"   duty {label:>4}: f_chop <= {f:,.0f} Hz at Qg max"
              f"  ({f / 1000:.2f} kHz)")
    for duty, label in ((0.0, "0 %"), (0.5, "50 %"), (1.0, "100 %")):
        f = max_f_chop_hz(duty, qg_c=QG_TYP_10V_C)
        print(f"   duty {label:>4}: f_chop <= {f:,.0f} Hz at Qg typ"
              f"  ({f / 1000:.2f} kHz)")
    print()
    print("   All-OC scenario, duty 50 %, Qg max:")
    print(f"      f_chop <= {max_f_chop_hz(0.5, u4_input_w=ALL_OC_U4_INPUT_W):,.0f} Hz")
    print()
    print("4. Sensitivity to gate drive voltage")
    print("   Qg is specified at 10 V; the driver runs at 12 V, so the real Qg")
    print("   is HIGHER than the datasheet limit used above. The break")
    print("   frequency therefore shrinks by the same factor:")
    for scale in (1.0, 1.1, 1.25, 1.5):
        f = max_f_chop_hz(0.5, qg_c=QG_MAX_10V_C * scale) / 1000
        print(f"      Qg x{scale:.2f}  ->  {f:>6.2f} kHz")
    print()
    print("VERDICT: the ledger omission is bounded, not eliminated. The design")
    print("fits the 1.1 W envelope only if f_chop stays below the figure above")
    print("at the real duty cycle. f_chop is not yet chosen anywhere in the")
    print("corpus, so PROT-11 remains OPEN with a stated condition, and the")
    print("1.027108922 W figure must not be quoted as the finished total.")


if __name__ == "__main__":
    main()
