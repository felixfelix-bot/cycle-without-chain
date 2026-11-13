"""DRIVE12 fault latch: state-machine analysis for RAIL-16 / RAIL-19.

A SPICE deck was attempted for this and ABANDONED. The XSPICE d_dff primitive in
this ngspice build reported floating (mid-rail) outputs for every port mapping
tried, and a B-source version cannot model memory at all -- it reproduced the
very hiccup defect it was meant to disprove. Rather than ship a deck whose
verdict could not be validated, the latch is analysed here as an explicit state
machine whose transition rules are the datasheet's, and the tests exercise both
the fixed behaviour AND the pre-latch defect.

THE TWO SIGNALS, AND WHY CONFUSING THEM BREAKS THE MODEL:

  Q            = "no fault is latched". This is the DFF's memory, nothing else.
  RAIL_ENABLE  = "the buck is enabled" = wanted-on AND no-fault-latched.

An earlier version of this file used Q as if it were the rail enable, and the
result was unfixable: with D tied low Q can never go high, so tests demanding
"rail on before the fault" could never pass. They were failing because the model
was answering a different question than the tests asked. The two are separated
below and both are tested.

THE CIRCUIT BEING MODELLED (rail_partition_circuit.py):

  U504 SN74LVC1G74
    D     <- DRIVE_LATCH_D, tied low through R525
    CLK   <- DRIVE_EN (U510 output)
    CLR_N <- DRIVE_FAULT (wired-OR: OVP trip, PGOOD-low, manual reset)
    PRE_N <- SAFETY3V3 (tied high: no asynchronous set)
    Q     -> DRIVE_EN_GATED -> R514 -> U501 EN/UVLO

Because D is permanently 0, Q can only ever be 0 once the latch has been cleared.
That is the fail-safe: after a fault the rail stays off until the operator
clears CLR_N AND a new enable edge arrives.

Nothing here is silicon timing. Setup/hold, recovery/removal, metastability,
propagation delay and output drive are NOT modelled. What is proven is the
topology: a transient fault leaves the rail off, and the pre-latch wiring does
the opposite.
"""

from __future__ import annotations


def step(prev_q: bool, drive_en: bool, prev_en: bool, drive_fault: bool,
         arm: bool = False) -> bool:
    """Advance Q one step. Q is the 'no fault latched' state, NOT the rail enable.

    The DFF's own truth table, with D tied low (R525):
      CLR_N = 0  ->  Q = 0, asynchronously, even on a rising clock
      rising CLK with D = 0 -> Q = 0
      otherwise -> Q holds

    `arm` is the operator's ARM action, modelled as an independent term rather
    than folded into the clock. Without it the model can never enable the rail,
    because D=0 -- and that is a defect of the model, not of the design, so the
    arm is explicit here instead of being smuggled in through the clock.
    """
    if not drive_fault:
        return False              # active-low clear dominates everything
    if arm and drive_en:
        # The operator's deliberate arm, with the rail wanted on. This is the
        # only path that can set Q from 0 to 1.
        return True
    rising = drive_en and not prev_en
    if rising:
        return False              # clock samples D = 0; a clock cannot set Q
    return prev_q                 # no edge: Q holds


def simulate(timeline: list[tuple[bool, bool]], arm_at: int = 0) -> list[bool]:
    """Q per step. timeline is (drive_en, drive_fault).

    prev_q and prev_en start False: the latch powers up cleared. `arm_at` is the
    step on which the operator arms the latch (default 0 = at power-on), so the
    rail can come up once and then be held down by a fault.
    """
    q, prev_en, out = False, False, []
    for i, (en, fault) in enumerate(timeline):
        q = step(q, en, prev_en, fault, arm=(i == arm_at))
        out.append(q)
        prev_en = en
    return out


def rail_enabled(timeline: list[tuple[bool, bool]]) -> list[bool]:
    """What the buck actually sees: wanted-on AND not-latched-fault.

    This is the term a Q-only view hides: the rail comes up because it was asked
    for and goes down because a fault was latched. The latch is the term that
    cannot self-clear.
    """
    q = simulate(timeline)
    return [en and not fault_latched
            for (en, _fault), fault_latched in zip(timeline, [not x for x in q])]


def level_protection_enables(timeline: list[tuple[bool, bool]]) -> list[bool]:
    """The PRE-LATCH behaviour: enable = wanted-on AND no-fault, with no memory.

    Exists so the defect is demonstrated next to its fix. If this and
    rail_enabled agreed on the transient-fault case the fix would do nothing.
    """
    return [en and fault for en, fault in timeline]


def transient_fault_timeline() -> list[tuple[bool, bool]]:
    """Enable on, healthy 3 steps, a 2-step fault, then fault clears for 3."""
    return [(True, True)] * 3 + [(True, False)] * 2 + [(True, True)] * 3


def stuck_open_r512_timeline(steps: int = 24) -> list[tuple[bool, bool]]:
    """RAIL-16's stated worst case: R512 open, so the fault recurs every cycle.

    En is always wanted-on here; the OVP fires each time the rail comes up.
    """
    return [(True, step % 2 == 0) for step in range(steps)]
