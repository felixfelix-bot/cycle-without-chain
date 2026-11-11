"""Tests for analysis/cx/bus_maximum.py — the CX-02 charge/stress split.

The load-bearing claim is that 58.4 V was doing two different jobs and is wrong
for both: too high as a charge ceiling for a 56.0 V LTO pack, and too low as a
stress ceiling because the chopper's own trip band sits above it.

These tests pin the arithmetic and, importantly, the one distinction that is
easy to get wrong: bus headroom is not the same as the pack accepting charge.
"""

import importlib.util
import unittest
from pathlib import Path


def _load():
    path = Path(__file__).with_name("bus_maximum.py")
    if not path.is_file():
        raise AssertionError("bus_maximum.py not implemented")
    spec = importlib.util.spec_from_file_location("bus_maximum", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BusMaximumTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    # --- where 58.4 came from --------------------------------------------
    def test_58_4_is_a_16s_lfp_string(self):
        self.assertAlmostEqual(self.m.LFP_16S_MAX, 58.4, places=6)

    def test_13s_li_ion_is_lower(self):
        self.assertAlmostEqual(self.m.LI_ION_13S_MAX, 54.6, places=6)

    def test_neither_string_is_the_selected_storage(self):
        self.assertNotAlmostEqual(self.m.pack_ceiling_v(), 58.4, places=3)
        self.assertNotAlmostEqual(self.m.pack_ceiling_v(), 54.6, places=3)

    # --- the selected pack -------------------------------------------------
    def test_20s_lto_ceiling_is_56_v(self):
        self.assertAlmostEqual(self.m.pack_ceiling_v(), 56.0, places=9)

    def test_20s_lto_nominal_is_48_v(self):
        self.assertAlmostEqual(self.m.pack_nominal_v(), 48.0, places=9)

    def test_20s_lto_floor_is_36_v(self):
        self.assertAlmostEqual(self.m.pack_floor_v(), 36.0, places=9)

    def test_ceiling_above_nominal_above_floor(self):
        self.assertGreater(self.m.pack_ceiling_v(), self.m.pack_nominal_v())
        self.assertGreater(self.m.pack_nominal_v(), self.m.pack_floor_v())

    def test_contract_figure_would_be_an_overcharge_command(self):
        self.assertGreater(self.m.CONTRACT_BUS_MAX, self.m.pack_ceiling_v())
        over = self.m.CONTRACT_BUS_MAX / self.m.pack_ceiling_v() - 1
        self.assertAlmostEqual(over, 0.042857, places=5)

    def test_bad_cell_inputs_rejected(self):
        with self.assertRaises(ValueError):
            self.m.pack_ceiling_v(cells=0)
        with self.assertRaises(ValueError):
            self.m.pack_ceiling_v(v_max=0)

    # --- the chopper cannot be below the pack ------------------------------
    def test_stress_ceiling_is_above_the_contract_figure(self):
        # 58.4 V cannot be the stress ceiling: the bus regulates above it.
        self.assertGreater(self.m.stress_ceiling_v(), self.m.CONTRACT_BUS_MAX)

    def test_stress_ceiling_is_the_top_of_the_on_band(self):
        self.assertAlmostEqual(self.m.stress_ceiling_v(), 61.226, places=9)

    def test_chopper_on_band_lies_above_the_pack_ceiling(self):
        self.assertGreater(self.m.CHOPPER_ON_MIN, self.m.pack_ceiling_v())

    def test_chopper_off_band_lies_above_the_pack_ceiling(self):
        self.assertGreater(self.m.CHOPPER_OFF_MIN, self.m.pack_ceiling_v())

    def test_chopper_holds_bus_above_pack_at_full_charge(self):
        hold = self.m.chopper_holds_above_pack_v(self.m.pack_ceiling_v())
        self.assertAlmostEqual(hold, 1.356, places=3)

    def test_hold_margin_shrinks_as_pack_rises(self):
        a = self.m.chopper_holds_above_pack_v(40.0)
        b = self.m.chopper_holds_above_pack_v(56.0)
        self.assertGreater(a, b)

    # --- the distinction that is easy to get wrong ------------------------
    def test_headroom_is_positive_even_at_full_charge(self):
        # The bus still has somewhere to rise...
        self.assertGreater(
            self.m.charge_headroom_v(self.m.pack_ceiling_v()), 0.0)

    def test_but_a_full_pack_absorbs_no_regen(self):
        # ...yet the pack at its ceiling accepts nothing. Both are true, and
        # conflating them is the error this pair of functions exists to stop.
        self.assertFalse(self.m.pack_absorbs_regen(self.m.pack_ceiling_v()))

    def test_pack_absorbs_regen_when_below_ceiling(self):
        for v in (36.0, 44.0, 48.0, 52.0, 55.9):
            self.assertTrue(self.m.pack_absorbs_regen(v), v)

    def test_absorption_boundary_is_the_ceiling(self):
        self.assertTrue(self.m.pack_absorbs_regen(55.999))
        self.assertFalse(self.m.pack_absorbs_regen(56.0))

    # --- divider arithmetic ------------------------------------------------
    def test_ratio_for_56_v_at_2v5(self):
        self.assertAlmostEqual(self.m.ratio_bound(2500, 56.0), 22.4, places=6)

    def test_ratio_grows_with_trip_voltage(self):
        self.assertGreater(self.m.ratio_bound(2500, 61.226),
                           self.m.ratio_bound(2500, 56.0))

    def test_ratio_rejects_zero_trip(self):
        with self.assertRaises(ValueError):
            self.m.ratio_bound(2500, 0)

    # --- guard against re-collapsing the two roles ------------------------
    def test_charge_and_stress_ceilings_differ(self):
        # If these ever become the same number, the CX-02 distinction has been
        # silently undone and this document's premise no longer holds.
        self.assertNotAlmostEqual(self.m.pack_ceiling_v(),
                                  self.m.stress_ceiling_v(), places=2)


if __name__ == "__main__":
    unittest.main()
