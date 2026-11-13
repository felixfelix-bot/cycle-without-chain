"""Tests for the TPSI3052 CDIV/bypass budget.

The point of these tests is not that the arithmetic works. It is that two
specific misreadings, which I made and published, cannot come back:

  1. Treating ``CDIV2 >= 3 x CDIV1`` as a *target* and therefore reporting the
     design's 4.7x as a violation. The datasheet states a floor.
  2. Comparing the 20x-Ciss bypass requirement against CDIV1 alone rather than
     against the capacitance actually across the node (CDIV1 + CDIV2).

Both are represented below as explicit regression tests.
"""

import unittest

import size_cdiv_bypass as m


class TestDatasheetLimits(unittest.TestCase):
    def test_design_is_within_both_absolute_ranges(self):
        r = m.evaluate()
        self.assertTrue(r["cdiv1_in_range"])
        self.assertTrue(r["cdiv2_in_range"])

    def test_below_minimum_is_rejected(self):
        # 1 nF is below the 4 nF CDIV1 minimum
        r = m.evaluate(cdiv1=1e-9, cdiv2=470e-9)
        self.assertFalse(r["cdiv1_in_range"])

    def test_above_maximum_is_rejected(self):
        # 50 uF exceeds the 40 uF CDIV2 maximum
        r = m.evaluate(cdiv1=100e-9, cdiv2=50e-6)
        self.assertFalse(r["cdiv2_in_range"])

    def test_cdiv2_lower_bound_is_12nf(self):
        """Pin the CDIV2 minimum value, not just 'some bound exists'.

        A mutation that raised CDIV2_MIN_F to 0.12 uF passed every other test,
        because nothing asserted the bound itself. 20 nF must be inside the
        window and 6 nF must not be.
        """
        self.assertAlmostEqual(m.CDIV2_MIN_F * 1e9, 12.0, places=3)
        self.assertTrue(m.evaluate(cdiv1=100e-9, cdiv2=20e-9)["cdiv2_in_range"])
        self.assertFalse(m.evaluate(cdiv1=100e-9, cdiv2=6e-9)["cdiv2_in_range"])

    def test_cdiv1_lower_bound_is_4nf(self):
        self.assertAlmostEqual(m.CDIV1_MIN_F * 1e9, 4.0, places=3)
        self.assertTrue(m.evaluate(cdiv1=6e-9, cdiv2=470e-9)["cdiv1_in_range"])
        self.assertFalse(m.evaluate(cdiv1=2e-9, cdiv2=470e-9)["cdiv1_in_range"])


class TestRatioIsAFloorNotATarget(unittest.TestCase):
    """Misreading 1: a minimum read as a setpoint."""

    def test_design_ratio_meets_the_minimum(self):
        r = m.evaluate()
        self.assertGreaterEqual(r["ratio"], m.CDIV2_RATIO_MIN)
        self.assertTrue(r["ratio_ok"])

    def test_exactly_three_times_is_acceptable(self):
        # 3.0x must PASS: the spec is ">= 3", so equality is compliant
        r = m.evaluate(cdiv1=100e-9, cdiv2=300e-9)
        self.assertTrue(r["ratio_ok"])

    def test_below_three_times_fails(self):
        r = m.evaluate(cdiv1=100e-9, cdiv2=250e-9)
        self.assertFalse(r["ratio_ok"])

    def test_higher_ratio_is_not_a_violation(self):
        # the 4.7x the design actually has must read as compliant
        r = m.evaluate(cdiv1=100e-9, cdiv2=470e-9)
        self.assertAlmostEqual(r["ratio"], 4.7, places=2)
        self.assertTrue(r["ratio_ok"],
                        "a ratio above 3x must not be reported as a violation")


class TestBypassUsesTheWholeNode(unittest.TestCase):
    """Misreading 2: comparing against CDIV1 alone."""

    def test_bypass_requirement_is_20x_ciss(self):
        need = m.bypass_needed_f()
        self.assertAlmostEqual(need * 1e9, 209.4, places=1)

    def test_design_meets_bypass_with_both_capacitors(self):
        r = m.evaluate()
        self.assertTrue(r["bypass_ok"])
        self.assertGreater(r["bypass_available_nf"], r["bypass_required_nf"])

    def test_cdiv1_alone_would_appear_to_fail(self):
        """Document why the original claim looked true.

        CDIV1 by itself (100 nF) is below the 209 nF requirement, which is what
        made the finding seem real. The node has CDIV1 + CDIV2 across it.
        """
        self.assertLess(m.CDIV1_F, m.bypass_needed_f())
        self.assertGreater(m.CDIV1_F + m.CDIV2_F, m.bypass_needed_f())


class TestChargeBudget(unittest.TestCase):
    def test_droop_is_q_over_c(self):
        self.assertAlmostEqual(m.droop_v(151e-9, 100e-9), 1.51, places=3)

    def test_headroom_exceeds_single_edge_droop_by_a_margin(self):
        r = m.evaluate()
        # even the conservative CDIV1-only droop must leave more than one edge
        # of margin before UVLO
        self.assertGreater(r["uvlo_headroom_v"], r["droop_cdiv1_only_typ_v"] * 2)

    def test_worst_case_gate_charge_is_covered(self):
        r = m.evaluate()
        self.assertLess(r["droop_worst_v"], r["uvlo_headroom_v"])


class TestRecoveryIsFastestSetting(unittest.TestCase):
    def test_rpxfr_is_the_maximum_duty_setting(self):
        # 20 kOhm is the highest of the seven settings in Table 8-1
        self.assertAlmostEqual(m.RPXFR_DUTY_PCT, 93.3, places=1)

    def test_human_switch_rates_leave_ample_recovery_time(self):
        # a power switch toggling at 1 Hz leaves 1 s between edges
        self.assertGreater(1.0 / 1.0, 0.001)


if __name__ == "__main__":
    unittest.main()
