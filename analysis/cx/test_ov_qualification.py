"""Tests for analysis/cx/ov_qualification.py — the PROT-07 extension.

The critical property is that this module *starts from* CX-01's published band
and only then adds the terms CX-01 says it omits. A test pins the reproduction,
so the extension cannot silently drift away from the document it extends.
"""

import importlib.util
import unittest
from pathlib import Path


def _load():
    path = Path(__file__).with_name("ov_qualification.py")
    if not path.is_file():
        raise AssertionError("ov_qualification.py not implemented")
    spec = importlib.util.spec_from_file_location("ov_qualification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OvQualificationTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    # --- reproduction of the published CX-01 band ------------------------
    def test_reproduces_cx01_minimum_turn_on(self):
        b = self.m.band(0.55, self.m.DELTA_T_CX01, False, False, False, False)
        self.assertAlmostEqual(b["on_min"], 59.31539, places=4)

    def test_reproduces_cx01_maximum_turn_on(self):
        b = self.m.band(0.55, self.m.DELTA_T_CX01, False, False, False, False)
        self.assertAlmostEqual(b["on_max"], 61.22594, places=4)

    def test_reproduces_cx01_minimum_turn_off(self):
        b = self.m.band(0.55, self.m.DELTA_T_CX01, False, False, False, False)
        self.assertAlmostEqual(b["off_min"], 57.35629, places=3)

    # --- the understated temperature excursion ---------------------------
    def test_rated_excursion_is_65_k(self):
        self.assertAlmostEqual(self.m.DELTA_T_RATED, 65.0, places=6)

    def test_cx01_used_50_k(self):
        self.assertAlmostEqual(self.m.DELTA_T_CX01, 50.0, places=6)

    def test_understatement_factor_is_1_3(self):
        self.assertAlmostEqual(
            self.m.DELTA_T_RATED / self.m.DELTA_T_CX01, 1.3, places=6)

    def test_rated_excursion_exceeds_cx01_assumption(self):
        self.assertGreater(self.m.DELTA_T_RATED, self.m.DELTA_T_CX01)

    # --- component drift arithmetic --------------------------------------
    def test_resistor_tolerance_at_65_k(self):
        self.assertAlmostEqual(self.m.resistor_tol(65.0), 0.002625, places=9)

    def test_resistor_tolerance_at_50_k(self):
        self.assertAlmostEqual(self.m.resistor_tol(50.0), 0.00225, places=9)

    def test_resistor_tolerance_grows_with_excursion(self):
        self.assertLess(self.m.resistor_tol(20.0), self.m.resistor_tol(65.0))

    def test_reference_tolerance_exceeds_the_datasheet_grade_figure(self):
        # Derived total adds ageing and hysteresis on top of the grade figure.
        self.assertGreater(self.m.reference_tol(65.0),
                           self.m.reference_tol_datasheet_grade())

    def test_reference_tolerance_exceeds_what_cx01_budgeted(self):
        self.assertGreater(self.m.reference_tol(65.0), 0.006)

    def test_ageing_and_hysteresis_each_add_tolerance(self):
        base = self.m.reference_tol(65.0, False, False)
        aged = self.m.reference_tol(65.0, True, False)
        full = self.m.reference_tol(65.0, True, True)
        self.assertAlmostEqual(aged - base,
                               self.m.REF_LONG_TERM_PPM * 1e-6, places=12)
        self.assertAlmostEqual(full - aged, self.m.REF_HYSTERESIS, places=12)

    def test_negative_excursion_rejected(self):
        with self.assertRaises(ValueError):
            self.m.resistor_tol(-1.0)
        with self.assertRaises(ValueError):
            self.m.reference_tol(-1.0)

    # --- the band only widens, never narrows -----------------------------
    def test_each_added_term_lowers_minimum_turn_on(self):
        steps = [
            self.m.band(0.55, self.m.DELTA_T_CX01, False, False, False, False),
            self.m.band(0.55, self.m.DELTA_T_RATED, False, False, False, False),
            self.m.band(0.55, self.m.DELTA_T_RATED, True, False, False, False),
            self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, False),
            self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True),
        ]
        for tighter, wider in zip(steps, steps[1:]):
            self.assertLessEqual(wider["on_min"], tighter["on_min"])

    def test_final_band_is_wider_than_published(self):
        pub = self.m.band(0.55, self.m.DELTA_T_CX01, False, False, False, False)
        final = self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True)
        self.assertLess(final["on_min"], pub["on_min"])
        self.assertGreater(final["on_max"], pub["on_max"])

    # --- polarity, the bug this module was written around ----------------
    def test_higher_vol_lowers_the_turn_on_trip(self):
        lo = self.m.band(0.40, self.m.DELTA_T_RATED, True, True, False, True)
        hi = self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True)
        self.assertLess(hi["on_min"], lo["on_min"])

    def test_vol_assumption_costs_about_102_mv(self):
        lo = self.m.band(0.40, self.m.DELTA_T_RATED, True, True, False, True)
        hi = self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True)
        self.assertAlmostEqual(lo["on_min"] - hi["on_min"], 0.102, places=2)

    def test_turn_off_uses_voh_not_vol(self):
        # Changing VOL must not move turn-off at all.
        a = self.m.band(0.40, self.m.DELTA_T_RATED, True, True, False, True)
        b = self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True)
        self.assertAlmostEqual(a["off_min"], b["off_min"], places=9)
        self.assertAlmostEqual(a["off_max"], b["off_max"], places=9)

    def test_hysteresis_is_positive_at_every_matched_corner(self):
        # Not the same as comparing global extrema: those come from different
        # corners and can overlap while every real circuit has hysteresis.
        h = self.m.hysteresis_at_corners()
        self.assertGreater(h["min"], 0.0)

    def test_matched_corner_hysteresis_matches_the_closed_form(self):
        h = self.m.hysteresis_at_corners()
        self.assertAlmostEqual(h["min"],
                               self.m.hysteresis_closed_form(), places=2)

    def test_global_extrema_are_not_a_hysteresis_test(self):
        # Record why the naive comparison fails: off_max can exceed on_min
        # across different corners.
        b = self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True)
        self.assertGreater(b["off_max"], b["on_min"])

    # --- the actual safety question --------------------------------------
    def test_threshold_stays_above_the_selected_pack_ceiling(self):
        b = self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True)
        self.assertGreater(b["on_min"], self.m.CHARGE_CEILING_LTO_20S)

    def test_threshold_stays_above_the_old_contract_figure(self):
        b = self.m.band(0.55, self.m.DELTA_T_RATED, True, True, False, True)
        self.assertGreater(b["on_min"], self.m.CONTRACT_BUS_MAX)

    def test_charge_ceiling_is_stricter_than_the_contract_figure(self):
        # Why 56.0 V is the binding comparison after CX-02.
        self.assertLess(self.m.CHARGE_CEILING_LTO_20S, self.m.CONTRACT_BUS_MAX)

    # --- divider / trip sanity -------------------------------------------
    def test_divider_gain_matches_the_report(self):
        self.assertAlmostEqual(
            self.m.divider_gain(225_000, 10_000, 330_000), 24.18181818, places=7)

    def test_trip_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            self.m.trip(2.5, 0.0, 0, 10_000, 330_000)
        with self.assertRaises(ValueError):
            self.m.trip(2.5, -1.0, 225_000, 10_000, 330_000)


if __name__ == "__main__":
    unittest.main()
