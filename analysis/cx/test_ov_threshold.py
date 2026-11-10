"""Tests for analysis/cx/ov_threshold.py — the CX-01 OV trip band.

The point of these tests is that the *recomputed* band is arithmetic, not prose:
the same code that reproduces the published 59.417 V corner (output-low 0.4 V)
also produces the 0.55 V-corner figure, and the difference between them is the
1 V-to-0.55 V output-low shift the integration review estimated as ~0.102 V.

Nothing here is electrical qualification. Every number is a screening bound on
the comparator network in hardware/powerboard-reva/protection_circuit.py, using
LM339B datasheet limits only.
"""

import importlib.util
import unittest
from pathlib import Path


def _load():
    path = Path(__file__).with_name("ov_threshold.py")
    if not path.is_file():
        raise AssertionError("ov_threshold.py not implemented")
    spec = importlib.util.spec_from_file_location("ov_threshold", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OvThresholdTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_divider_gain_matches_the_report(self):
        # 1 + 225k/10k + 225k/330k, the expression in the milestone report.
        self.assertAlmostEqual(self.m.divider_gain(225_000, 10_000, 330_000),
                               24.18181818, places=8)

    def test_nominal_trip_reproduces_the_published_extremes(self):
        # Report §OV thresholds and timing: turn-on 60.318 V, turn-off 58.205 V,
        # hysteresis 2.114 V.  The turn-on nominal is quoted at Vout = 0.2 V.
        on = self.m.trip(self.m.VREF_NOM, 0.2, self.m.RT_NOM, self.m.RB_NOM,
                         self.m.RH_NOM)
        off = self.m.trip(self.m.VREF_NOM, self.m.VOH_NOM, self.m.RT_NOM,
                          self.m.RB_NOM, self.m.RH_NOM)
        self.assertAlmostEqual(on, 60.31818, places=5)
        self.assertAlmostEqual(off, 58.20455, places=5)
        self.assertAlmostEqual(on - off, 2.11364, places=5)

    def test_band_with_0v4_output_low_reproduces_59_417(self):
        # This is the *published* screening figure.  The script must reproduce
        # it, otherwise it is not the same model the report used.
        band = self.m.band(vol_max=self.m.VOL_25C)
        self.assertAlmostEqual(band["on_min"], 59.41720, places=5)
        self.assertAlmostEqual(band["on_max"], 61.22594, places=5)
        self.assertAlmostEqual(band["off_min"], 57.35629, places=5)
        self.assertAlmostEqual(band["off_max"], 59.05819, places=5)

    def test_band_with_0v55_output_low_is_the_qualified_minimum(self):
        band = self.m.band(vol_max=self.m.VOL_FULL_T)
        self.assertAlmostEqual(band["on_min"], 59.31539, places=5)
        self.assertAlmostEqual(band["on_max"], 61.22594, places=5)
        # The qualification removes margin from the bottom only: the maximum
        # turn-on corner is unaffected because VOH does not enter turn-on.
        self.assertAlmostEqual(band["off_min"], 57.35629, places=5)

    def test_the_0v55_corner_moves_down_by_the_reviewed_0_102_v(self):
        four = self.m.band(vol_max=self.m.VOL_25C)
        full = self.m.band(vol_max=self.m.VOL_FULL_T)
        delta = four["on_min"] - full["on_min"]
        self.assertAlmostEqual(delta, 0.10181, places=5)
        # The review's closed form: (Rt/Rh) x (0.55 - 0.40), evaluated at the
        # corner that sets the minimum (Rt low, Rh high => Rt/Rh = 0.6788).
        corner = full["worst_on"]
        analytic = self.m.low_corner_shift(corner["rt"], corner["rh"], 0.15)
        self.assertAlmostEqual(delta, analytic, places=9)
        self.assertAlmostEqual(analytic, 0.10181, places=5)

    def test_minimum_turn_on_is_monotone_in_the_output_low_limit(self):
        a = self.m.band(vol_max=0.0)["on_min"]
        b = self.m.band(vol_max=self.m.VOL_25C)["on_min"]
        c = self.m.band(vol_max=self.m.VOL_FULL_T)["on_min"]
        self.assertLess(c, b)
        self.assertLess(b, a)

    def test_hysteresis_survives_every_corner(self):
        # min turn-on must stay above max turn-off or the latch chatters.
        for vol in (self.m.VOL_25C, self.m.VOL_FULL_T):
            band = self.m.band(vol_max=vol)
            self.assertGreater(band["on_min"] - band["off_max"], 0.0)

    def test_margin_to_the_chosen_bus_maximum(self):
        band = self.m.band(vol_max=self.m.VOL_FULL_T)
        self.assertAlmostEqual(self.m.margin(band["on_min"], 58.4), 0.91539,
                               places=5)

    def test_the_band_covers_128_uncoupled_corners(self):
        # six independent binary limits (Rt, Rb, Rh, Vref, Vos, VOH) x two
        # output-low limits.  The published code coupled the output-low limit
        # to the VOH sign; that coupling is not a physical relation.
        band = self.m.band(vol_max=self.m.VOL_FULL_T)
        self.assertEqual(band["corners"], 128)

    def test_sink_current_stays_inside_the_datasheet_test_condition(self):
        # VOL max 550 mV is specified at ISINK <= 4 mA.  The 1k pullup to
        # SAFETY3V3 draws (VOH - VOL)/1k.
        for voh in (3.3 * 0.96, 3.3, 3.3 * 1.04):
            self.assertLess(self.m.sink_current(voh, self.m.VOL_FULL_T), 4e-3)

    def test_rejects_impossible_hardware(self):
        with self.assertRaises(ValueError):
            self.m.divider_gain(0, 10_000, 330_000)
        with self.assertRaises(ValueError):
            self.m.band(vol_max=-0.1)


if __name__ == "__main__":
    unittest.main()
