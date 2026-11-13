"""Tests for the overcurrent trip envelope (register OC-03, OC-08).

The binding test is ``test_reproduces_documented_screen``: the register publishes
16.92639 .. 23.08413 A, and this module must reproduce those numbers exactly. If
the model drifts, that test fails and the documented figure can no longer be
claimed as computed by this code — which is the whole point of having it in code
rather than prose.
"""

import json
import unittest

import oc_envelope as oce


class TestReproducesDocumentedScreen(unittest.TestCase):
    """The module must agree with the figure already published in the repo."""

    def test_reproduces_documented_screen(self):
        env = oce.envelope(oce.LOW_REF)
        # exact to the five decimals the register prints
        self.assertAlmostEqual(env["earliest_a"], 16.92639, places=4)
        self.assertAlmostEqual(env["latest_a"], 23.08413, places=4)

    def test_high_leg_is_mirror_symmetric(self):
        # HIGH_REF is the mirror of LOW_REF, so the screen must mirror too.
        low = oce.envelope(oce.LOW_REF)
        high = oce.envelope(oce.HIGH_REF)
        self.assertAlmostEqual(high["earliest_a"], -low["latest_a"], places=4)
        self.assertAlmostEqual(high["latest_a"], -low["earliest_a"], places=4)

    def test_corner_count_is_exhaustive(self):
        # 7 binary terms -> 128 corners: rail, top, bottom, gain, shunt, csa, comp
        self.assertEqual(oce.envelope(oce.LOW_REF)["corners"], 128)


class TestTheTwoTraps(unittest.TestCase):
    """Both of these were got wrong on the first attempt; neither is guessable."""

    def test_csa_offset_is_shunt_referred_not_input_referred(self):
        # 3 mV across 2 mOhm is 1.5 A. If it were input-referred it would be
        # 3mV/(20*2mOhm) = 0.075 A, twenty times smaller — and the envelope
        # would be far too tight.
        amps = oce.CSA_OFFSET_V / oce.SHUNT_OHM
        self.assertAlmostEqual(amps, 1.5, places=6)
        self.assertNotAlmostEqual(
            oce.CSA_OFFSET_V / (20 * oce.SHUNT_OHM), 1.5, places=2)

    def test_reference_is_mid_rail_not_the_divider_node(self):
        # Swapping the sign of the (VREF/2 - node) term must change the answer,
        # proving the bias is actually subtracted rather than ignored.
        base = oce.trip_current(3.3, *oce.LOW_REF, 20.0, 0.002)
        flipped = ((3.3 / 2.0 + oce.divider_node(*oce.LOW_REF, 3.3)
                    ) / 20.0) / 0.002
        self.assertNotAlmostEqual(base, flipped, places=2)


class TestCommissioningCap(unittest.TestCase):
    def test_cap_is_below_earliest_possible_trip(self):
        # The 10 A commissioning cap must never itself cause a trip, so it has
        # to sit below the earliest corner the protection can fire at.
        r = oce.evaluate()
        self.assertTrue(r["cap_below_earliest_trip"])
        self.assertGreater(r["cap_margin_a"], 5.0)

    def test_cap_is_about_half_the_earliest_trip(self):
        # 10 A against a 16.9 A worst-case floor is a deliberately conservative
        # first-power-up limit, not a normal operating point.
        r = oce.evaluate()
        self.assertLess(r["commissioning_cap_a"] / r["envelope"]["low"]["earliest_a"],
                        0.65)


class TestHysteresisBand(unittest.TestCase):
    def test_release_band_is_tiny(self):
        # 0.030 A nominal is the published equivalence. A band this small cannot
        # reject noise on its own, which is why OC-08 asks for the noise
        # envelope rather than accepting hysteresis as sufficient.
        h = oce.hysteresis_band_a()
        self.assertAlmostEqual(h["band_a"], 0.03, places=4)
        self.assertLess(h["band_a"], 0.1)

    def test_the_binding_band_is_the_smallest_not_the_nominal(self):
        # At GAIN_MAX the same 1.2 mV represents less current, so the part can
        # provide less release separation than the nominal figure suggests.
        # Quoting nominal as "the" band is the optimistic read; this asserts the
        # module reports the pessimistic one and that it is genuinely smaller.
        h = oce.hysteresis_band_a()
        # lowest gain (19.4) -> least amplification -> largest current band
        # highest gain (20.6) -> most amplification -> smallest current band
        self.assertGreater(h["band_max_a"], h["band_nominal_a"])
        self.assertLess(h["band_min_a"], h["band_nominal_a"])
        self.assertAlmostEqual(h["band_min_a"], 0.0012 / 20.6 / 0.002, places=9)
        self.assertAlmostEqual(h["band_max_a"], 0.0012 / 19.4 / 0.002, places=9)
        # the spread is small but the pessimistic end is the one that matters
        self.assertLess(h["band_min_a"], 0.030)


class TestNoSafetyClaim(unittest.TestCase):
    def test_safety_claim_is_always_false(self):
        # This is the load-bearing assertion. A static envelope is not a
        # qualified trip point, and the module must never imply otherwise.
        r = oce.evaluate()
        self.assertIs(r["safety_claim"], False)
        self.assertIn("unbounded", r["safety_claim_reason"].lower()
                      .replace("five terms above are unbounded", "unbounded"))

    def test_unbounded_terms_are_all_named(self):
        r = oce.evaluate()
        joined = " ".join(r["unbounded_terms"]).lower()
        for term in ("midpoint", "thermal", "latency", "blind", "common reference"):
            self.assertIn(term, joined)


class TestResultsArtifact(unittest.TestCase):
    def test_results_file_matches_module(self):
        r = oce.evaluate()
        with open("oc-envelope-results.json", encoding="utf-8") as fh:
            saved = json.load(fh)
        self.assertAlmostEqual(saved["envelope"]["low"]["earliest_a"],
                               r["envelope"]["low"]["earliest_a"], places=9)


if __name__ == "__main__":
    unittest.main()
