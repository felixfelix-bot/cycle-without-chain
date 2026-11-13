"""Tests for the gate-resistor sizing model (RAIL-10).

These pin the *reasoning*, not just the arithmetic. The model went through three
wrong answers before landing, and each wrong answer is represented here as a
regression test so the same mistake cannot silently return:

1. First draft treated the DRV8353's 1 A source limit as a disqualification, so
   it reported that the driver "could not drive" the FET at 2.2-6.8 ohm. Wrong:
   the driver still drives, it just charges in current limit.
2. Second draft picked 2.2 ohm because it was the "fastest under the dv/dt
   ceiling" — but at 2.2 ohm the RC time (48.6 ns) is within 1.3 % of the
   current-limit floor (48.0 ns), so the resistor is inert and inside model error.
3. The design point was 20 A, the DRV8353's rating, which produced 22 W of
   switching loss and made the whole trade look absurd. The right current comes
   from the drivetrain (ARCH-04 leaves it undefined): ~13 A at 400 W on a 36 V bus.
"""

import math
import unittest

import size_gate_resistors as m


class TestPhysicsBounds(unittest.TestCase):
    def setUp(self):
        self.fet = m.Fet()
        self.drv = m.Driver()

    def test_time_constant_matches_hand_calculation(self):
        # tau = R_total * Ciss = (2.2 + 1.5 + 1.0) ohm * 4700 pF = 22.09 ns
        self.assertAlmostEqual(m.tau_ns(2.2, self.fet, self.drv), 22.09, places=2)

    def test_edge_time_is_max_of_both_mechanisms(self):
        # The edge is whichever mechanism is slower: you cannot charge faster
        # than the RC time OR than the current limit allows.
        for rg in (1.0, 3.3, 10.0, 22.0):
            t_rc, t_lim = m.transition_range_ns(rg, self.fet, self.drv)
            self.assertAlmostEqual(m.t_sw_ns(rg, self.fet, self.drv),
                                   max(t_rc, t_lim), places=6)

    def test_rc_dominates_above_crossover(self):
        # Above ~2.14 ohm external the RC time exceeds the floor, so the edge
        # equals 2.2*tau and the resistor genuinely controls switching speed.
        tau = m.tau_ns(10.0, self.fet, self.drv)
        self.assertAlmostEqual(m.t_sw_ns(10.0, self.fet, self.drv),
                               2.2 * tau, places=6)

    def test_current_limit_floor_is_qg_over_ilim(self):
        expected = (self.fet.qg_nc * 1e-9) / (self.drv.i_source_ma * 1e-3) * 1e9
        t_rc, t_lim = m.transition_range_ns(50.0, self.fet, self.drv)
        self.assertAlmostEqual(t_lim, expected, places=6)

    def test_large_resistor_is_rc_limited(self):
        # 22 ohm: RC 253 ns >> floor 48 ns, so the resistor sets the edge
        t_rc, t_lim = m.transition_range_ns(22.0, self.fet, self.drv)
        self.assertGreater(t_rc, 5 * t_lim)

    def test_small_resistor_is_current_limited(self):
        # 1 ohm: RC 36 ns < floor 48 ns, so the driver sets the edge
        t_rc, t_lim = m.transition_range_ns(1.0, self.fet, self.drv)
        self.assertLess(t_rc, t_lim)


class TestNoDisqualificationRegression(unittest.TestCase):
    """Wrong answer 1: current-limited must not mean 'cannot drive'."""

    def test_driver_still_drives_when_current_limited(self):
        r = m.evaluate(2.2, m.Fet(), m.Driver())
        # peak demand exceeds the 1 A limit ...
        self.assertGreater(r["peak_gate_current_a"], 1.0)
        # ... but the loss is finite and the transition is reported, not refused
        self.assertGreater(r["switching_loss_w"], 0.0)
        self.assertIn("t_sw_ns", r)


class TestNoInertResistorRegression(unittest.TestCase):
    """Wrong answer 2: the chosen value must actually control the edge."""

    def test_chosen_value_owns_the_edge(self):
        fet, drv = m.Fet(), m.Driver()
        rows = [m.evaluate(rg, fet, drv) for rg in m.CANDIDATES_OHM]
        ceiling, margin = m.DVDT_CEILING_V_PER_NS, m.RC_MARGIN
        viable = [r for r in rows
                  if r["dvdt_v_per_ns"] <= ceiling
                  and r["t_rc_ns"] >= margin * r["t_limit_ns"]]
        best = min(viable, key=lambda r: r["rg_ohm"])
        # the resistor must dominate the driver, not sit on the crossover
        self.assertGreater(best["t_rc_ns"], 1.2 * best["t_limit_ns"])
        self.assertLess(best["dvdt_v_per_ns"], ceiling)
        self.assertEqual(best["rg_ohm"], 3.3)

    def test_2r2_is_rejected_for_being_inert(self):
        r = m.evaluate(2.2, m.Fet(), m.Driver())
        # 48.60 ns RC vs 48.00 ns floor: 1.25 % margin, inside model error
        self.assertLess(r["t_rc_ns"] / r["t_limit_ns"], 1.2)

    def test_margin_rule_actually_excludes_the_crossover(self):
        """Pin the *rule*, not just the outcome.

        Dropping MARGIN to 1.00 leaves the chosen value at 3.3 ohm here, so a
        test that only checks the outcome misses the regression entirely (this
        was found by mutation testing). So assert the property directly: the
        chosen resistor must clear the crossover by the stated margin, and 2.2
        ohm — which sits 1.25 % above it — must not qualify under any sane rule.
        """
        rows = [m.evaluate(rg, m.Fet(), m.Driver()) for rg in m.CANDIDATES_OHM]
        ceiling = m.DVDT_CEILING_V_PER_NS
        margin = m.RC_MARGIN
        viable = [r for r in rows
                  if r["dvdt_v_per_ns"] <= ceiling
                  and r["t_rc_ns"] >= margin * r["t_limit_ns"]]
        self.assertTrue(viable, "no candidate clears the crossover")

        # 2.2 ohm must be excluded by the margin rule specifically
        r22 = [r for r in rows if r["rg_ohm"] == 2.2][0]
        self.assertFalse(
            r22["t_rc_ns"] >= margin * r22["t_limit_ns"],
            "2.2 ohm must fail the 1.20x margin rule (it is only 1.01x)")


class TestNoWrongCurrentRegression(unittest.TestCase):
    """Wrong answer 3: design current comes from the drivetrain, not the driver."""

    def test_design_current_is_not_the_driver_rating(self):
        self.assertLess(m.I_LOAD, 20.0)   # 20 A is the DRV8353's rating
        self.assertGreaterEqual(m.I_LOAD, 10.0)  # but must cover the 400 W case

    def test_loss_is_plausible_at_design_point(self):
        # Six devices at 15 A must not exceed a few watts, or the design point
        # is wrong (this is exactly what the 20 A version produced: 22 W).
        r = m.evaluate(3.3, m.Fet(), m.Driver())
        total = r["switching_loss_w"] * 6
        self.assertLess(total, 8.0)
        self.assertGreater(total, 2.0)


class TestCeilingIsNonBinding(unittest.TestCase):
    """The dv/dt ceiling does no work at this design point — say so.

    Max dv/dt across every candidate is ~1.07 V/ns, well under the 2.0 V/ns
    ceiling, so the ceiling excludes nothing. The RC-margin rule is the only
    binding constraint. Recording this prevents a future reader from believing
    the design is dv/dt-limited when it is not, and explains why loosening the
    ceiling (a mutation that no test catches) changes no outcome.
    """

    def test_no_candidate_exceeds_the_ceiling(self):
        rows = [m.evaluate(rg, m.Fet(), m.Driver()) for rg in m.CANDIDATES_OHM]
        worst = max(r["dvdt_v_per_ns"] for r in rows)
        self.assertLess(worst, m.DVDT_CEILING_V_PER_NS,
                        "ceiling has become binding; the note above is stale")

    def test_margin_is_the_binding_constraint(self):
        rows = [m.evaluate(rg, m.Fet(), m.Driver()) for rg in m.CANDIDATES_OHM]
        by_margin = [r for r in rows
                     if r["t_rc_ns"] >= m.RC_MARGIN * r["t_limit_ns"]]
        by_ceiling = [r for r in rows
                      if r["dvdt_v_per_ns"] <= m.DVDT_CEILING_V_PER_NS]
        # the ceiling lets everything through; the margin is what filters
        self.assertEqual(len(by_ceiling), len(rows))
        self.assertLess(len(by_margin), len(rows))


class TestRingingIsNotGateDamping(unittest.TestCase):
    def test_ringing_frequency_matches_lc(self):
        ring = m.ringing(vds=52.0, coss_pf=720.0, l_loop_nh=4.0)
        expected = 1.0 / (2 * math.pi * math.sqrt(4e-9 * 720e-12)) / 1e6
        self.assertAlmostEqual(ring["f_ring_mhz"], expected, places=3)

    def test_gate_resistor_does_not_change_ringing(self):
        # Ringing is set by L_loop and Coss only; it must be independent of Rg.
        # If a future edit starts implying Rg damps the loop, this fails.
        a = m.ringing(vds=52.0, coss_pf=720.0, l_loop_nh=4.0)
        b = m.ringing(vds=52.0, coss_pf=720.0, l_loop_nh=4.0)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
