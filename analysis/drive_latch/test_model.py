"""Tests for the DRIVE12 latch model (RAIL-16 / RAIL-19).

Two different questions are tested, and they must not be conflated:

  Q (the DFF state)  answers "is a fault latched?" -- this is the memory.
  rail_enabled       answers "is the buck enabled?" = wanted-on AND not-latched.

An earlier version of this suite asked the second question of Q, which is why it
could not pass: with D tied low Q can never go high. Each case below names which
signal it asserts.
"""

import unittest

from model import (
    level_protection_enables,
    rail_enabled,
    simulate,
    step,
    stuck_open_r512_timeline,
    transient_fault_timeline,
)


class LatchMemory(unittest.TestCase):
    """Q: the fault memory itself."""

    def test_fault_clears_q_asynchronously(self):
        q = simulate([(True, True)] * 2 + [(True, False)])
        self.assertFalse(q[-1], "Q must clear when the fault asserts")

    def test_q_cannot_set_from_zero(self):
        """D tied low: Q can never become 1 from 0, on any clock."""
        self.assertFalse(step(prev_q=False, drive_en=True, prev_en=False, drive_fault=True))
        self.assertFalse(step(prev_q=False, drive_en=True, prev_en=True, drive_fault=True))

    def test_q_holds_without_an_edge(self):
        """This hold IS the latch. An AND gate would not have this property."""
        self.assertTrue(step(prev_q=True, drive_en=True, prev_en=True, drive_fault=True))
        self.assertFalse(step(prev_q=False, drive_en=False, prev_en=False, drive_fault=True))

    def test_clear_dominates_clock(self):
        """CLR_N low wins even on a rising clock."""
        self.assertFalse(step(prev_q=True, drive_en=True, prev_en=False, drive_fault=False))

    def test_power_on_is_cleared(self):
        """Before any arm action the latch is cleared, so the rail stays off."""
        self.assertFalse(simulate([(True, True)], arm_at=-1)[0])


class RailBehaviour(unittest.TestCase):
    """What the buck actually sees: wanted-on AND not-latched-fault."""

    def test_enabled_before_a_fault(self):
        en = rail_enabled(transient_fault_timeline())
        self.assertTrue(en[0] and en[2], "rail should be enabled while healthy")

    def test_disabled_during_a_fault(self):
        en = rail_enabled(transient_fault_timeline())
        self.assertFalse(en[3], "rail must go off when the fault asserts")
        self.assertFalse(en[4], "and stay off while the fault is held")

    def test_transient_fault_does_not_self_recover(self):
        """THE RAIL-16 CASE: a passing overvoltage must not self-recover."""
        en = rail_enabled(transient_fault_timeline())
        for i in (5, 6, 7):
            self.assertFalse(en[i], f"rail restarted at step {i} once the fault cleared")

    def test_old_level_protection_does_restart(self):
        """Negative control: the pre-latch wiring must show the defect.

        If this fails while the latch test above passes, the fix is fixing
        nothing. The comparison is the whole argument.
        """
        old = level_protection_enables(transient_fault_timeline())
        self.assertTrue(old[-1], "level protection must restart, to be a valid control")
        self.assertFalse(rail_enabled(transient_fault_timeline())[-1],
                         "latched behaviour must not restart")

    def test_permanent_fault_cannot_hiccup(self):
        """RAIL-16's stated worst case: a recurring fault must not oscillate."""
        t = stuck_open_r512_timeline()
        en = rail_enabled(t)
        # Once any fault is seen, the rail must stay off for every later step.
        first_fault = next(i for i, s in enumerate(t) if not s[1])
        for j in range(first_fault, len(en)):
            self.assertFalse(en[j], f"rail hiccupped at step {j}")

    def test_held_fault_beats_held_enable(self):
        self.assertTrue(all(not x for x in rail_enabled([(True, False)] * 5)))


if __name__ == "__main__":
    unittest.main()
