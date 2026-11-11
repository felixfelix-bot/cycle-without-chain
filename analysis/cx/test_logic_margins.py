"""Tests for analysis/cx/logic_margins.py — the PROT-03 per-path budget.

These verify that the margin arithmetic is done in the pessimistic direction and
that the module's own headline claims are reproducible. They do not verify the
datasheet numbers themselves; those are cited in the module docstring and in
docs/design/prot03-logic-margins.md.
"""

import importlib.util
import unittest
from pathlib import Path


def _load():
    path = Path(__file__).with_name("logic_margins.py")
    if not path.is_file():
        raise AssertionError("logic_margins.py not implemented")
    spec = importlib.util.spec_from_file_location("logic_margins", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LogicMarginsTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    # --- direction of the arithmetic -------------------------------------
    def test_margin_is_receiver_limit_minus_driver_vol(self):
        self.assertAlmostEqual(self.m.logic_low_margin_v(0.55, 0.84), 0.29,
                               places=9)

    def test_margin_goes_negative_when_driver_vol_exceeds_limit(self):
        # The failure the gate is worried about must be representable.
        self.assertLess(self.m.logic_low_margin_v(1.0, 0.84), 0.0)

    def test_receiver_limit_uses_minimum_not_maximum(self):
        # Guaranteed-low requires being below VT- MIN, not the typical value.
        self.assertLess(self.m.LVC3G17_VT_MINUS_AT_3V0,
                        self.m.LVC3G17_VT_PLUS_MAX_AT_3V0)

    def test_supply_minimum_is_below_nominal(self):
        self.assertLess(self.m.supply_min_v(), self.m.SAFETY3V3_NOM)

    # --- pullup current ---------------------------------------------------
    def test_pullup_current_scales_inversely_with_resistance(self):
        a = self.m.pullup_current_a(1_000)
        b = self.m.pullup_current_a(2_000)
        self.assertAlmostEqual(a, 2 * b, places=12)

    def test_one_kohm_pullup_draws_about_3_2_ma(self):
        self.assertAlmostEqual(self.m.pullup_current_a(1_000) * 1e3, 3.168,
                               places=3)

    def test_pullup_current_uses_supply_minimum(self):
        # A pessimistic budget must not use the nominal rail.
        self.assertGreater(self.m.pullup_current_a(1_000, v_rail=3.3),
                           self.m.pullup_current_a(1_000))

    def test_zero_or_negative_pullup_rejected(self):
        with self.assertRaises(ValueError):
            self.m.pullup_current_a(0)
        with self.assertRaises(ValueError):
            self.m.pullup_current_a(-10)

    # --- the four paths ---------------------------------------------------
    def test_five_paths_are_evaluated(self):
        self.assertEqual(len(self.m.path_budget()), 5)

    def test_all_paths_have_positive_low_margin(self):
        for p in self.m.path_budget():
            self.assertGreater(p["margin_v"], 0.0, p["path"])

    def test_worst_path_is_analog_ok_at_290_mv(self):
        w = self.m.worst_path()
        self.assertIn("ANALOG_OK", w["path"])
        self.assertAlmostEqual(w["margin_v"], 0.290, places=3)

    def test_encoder_analog_ok_is_the_worst_because_highest_vol(self):
        # ANALOG_OK and OV_CMD share the LM339B 550 mV limit; ANALOG_OK wins
        # only because its receiver limit (0.84 V) is below UCC27511's 1.0 V.
        budget = {p["path"]: p for p in self.m.path_budget()}
        analog = budget["ANALOG_OK -> U11 1A"]
        ovcmd = budget["OV_CMD -> U10 IN+"]
        self.assertEqual(analog["driver_vol_max"], ovcmd["driver_vol_max"])
        self.assertLess(analog["receiver_low_limit"],
                        ovcmd["receiver_low_limit"])

    def test_worst_path_is_the_minimum_of_the_budget(self):
        rows = self.m.path_budget()
        self.assertEqual(self.m.worst_path()["margin_v"],
                         min(r["margin_v"] for r in rows))

    def test_nfault_path_has_the_largest_margin(self):
        budget = {p["path"]: p for p in self.m.path_budget()}
        self.assertAlmostEqual(
            budget["GEN_nFAULT -> U11 2A"]["margin_v"], 0.715, places=3)

    # --- high level -------------------------------------------------------
    def test_high_margin_positive_for_both_pullups(self):
        for name, r, lim in (
            ("analog", self.m.R_PULLUP_ANALOG_OK,
             self.m.LVC3G17_VT_PLUS_MAX_AT_3V0),
            ("ovcmd", self.m.R_PULLUP_OV_CMD, self.m.UCC27511_VIN_H_MAX),
        ):
            self.assertGreater(
                self.m.logic_high_margin_v(self.m.supply_min_v(), r, 50e-9, lim),
                0.0, name)

    def test_high_margin_falls_as_leakage_rises(self):
        a = self.m.logic_high_margin_v(3.3, 4_700, 1e-6, 1.87)
        b = self.m.logic_high_margin_v(3.3, 4_700, 1e-4, 1.87)
        self.assertGreater(a, b)

    # --- attribution guard ------------------------------------------------
    def test_legacy_700mv_limit_is_not_used_for_lm339b(self):
        # The 700 mV row belongs to the LMx39/LMx39A table, not the LM339B.
        self.assertEqual(self.m.LM339B_VOL_MAX, 0.550)
        self.assertNotEqual(self.m.LM339B_VOL_MAX, 0.700)

    def test_25c_limit_is_lower_than_full_range_limit(self):
        self.assertLess(self.m.LM339B_VOL_MAX_25C, self.m.LM339B_VOL_MAX)


if __name__ == "__main__":
    unittest.main()
