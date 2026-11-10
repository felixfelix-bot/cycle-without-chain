"""Tests for the LTO bus-maximum reconciliation.

Written BEFORE the model, so the first run is RED. Every expected value is
either a closed-form arithmetic result stated in the test, or a value copied
from a cited primary document, or a figure carried over from the existing
precharge/storage models so that the same quantity can be compared old-vs-new.

Run:
    python3 -m unittest discover -s analysis/storage -p 'test_lto_bus.py' -v
    python3 -O -m unittest discover -s analysis/storage -p 'test_lto_bus.py' -v
"""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f'{name}.py')
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CandidateCellsTest(unittest.TestCase):
    """Every ceiling/floor used must come from one named document."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load('lto_bus')

    def test_candidates_are_cited(self):
        for cell in self.m.CANDIDATES:
            self.assertTrue(cell.document, cell.name)
            self.assertIn('§', cell.document, f'{cell.name} citation has no section')
            self.assertTrue(cell.manufacturer, cell.name)

    def test_yinlong_40ah_values(self):
        c = self.m.cell('yinlong-66160-40ah')
        self.assertAlmostEqual(c.nominal_v, 2.3)
        self.assertAlmostEqual(c.charge_ceiling_v, 2.9)
        self.assertAlmostEqual(c.discharge_floor_v, 1.5)
        self.assertAlmostEqual(c.cont_a, 240)
        self.assertAlmostEqual(c.pulse_a, 400)
        self.assertAlmostEqual(c.temp_low_c, -40)
        self.assertAlmostEqual(c.temp_high_c, 65)
        self.assertAlmostEqual(c.cycles, 16000)

    def test_altairnano_70ah_values(self):
        c = self.m.cell('altairnano-70ah')
        self.assertAlmostEqual(c.nominal_v, 2.22)
        self.assertAlmostEqual(c.charge_ceiling_v, 2.9)
        self.assertAlmostEqual(c.discharge_floor_v, 1.5)
        self.assertAlmostEqual(c.cont_a, 500)
        self.assertAlmostEqual(c.pulse_a, 900)
        self.assertAlmostEqual(c.cycles, 25000)

    def test_toshiba_cell_level_gaps_are_declared_not_filled(self):
        # The bicycle-mass cell has no cell datasheet: those fields stay None.
        c = self.m.cell('toshiba-scib-2.9ah')
        self.assertAlmostEqual(c.nominal_v, 2.4)
        self.assertAlmostEqual(c.charge_ceiling_v, 2.7)
        self.assertIsNone(c.cont_a)
        self.assertIsNone(c.temp_low_c)
        self.assertIsNone(c.cycles)
        self.assertIn('NOT IN DOCUMENT', c.gaps)


class SeriesSelectionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _load('lto_bus')

    def test_series_is_twenty(self):
        self.assertEqual(self.m.select_series(), 20)

    def test_the_floor_binds_not_the_ceiling(self):
        # 58.4/2.7 = 21 cells; 36/1.8 = 20 cells. The floor governs.
        bounds = self.m.series_bounds()
        self.assertEqual(bounds['by_ceiling'], 21)
        self.assertEqual(bounds['by_floor'], 20)
        self.assertEqual(bounds['governs'], 'floor')

    def test_bus_minimum_is_36_volts_at_the_usable_floor(self):
        self.assertAlmostEqual(self.m.bus_minimum_v(), 36.0)

    def test_design_bus_maximum_is_54_volts(self):
        self.assertAlmostEqual(self.m.design_bus_maximum_v(), 54.0)

    def test_58_4_needs_more_than_any_verified_ceiling(self):
        # 58.4 / 20 = 2.92 V/cell, above every ceiling we could document.
        self.assertAlmostEqual(self.m.implied_cell_ceiling_for(58.4), 2.92)
        for cell in self.m.CANDIDATES:
            self.assertGreater(
                self.m.implied_cell_ceiling_for(58.4), cell.charge_ceiling_v,
                f'{cell.name} could reach 58.4 V — the conclusion would change')

    def test_58_4_is_not_an_integer_multiple(self):
        for cell in self.m.CANDIDATES:
            quotient = 58.4 / cell.charge_ceiling_v
            self.assertNotAlmostEqual(quotient, round(quotient), places=6)

    def test_58_0_at_the_most_permissive_ceiling_is_also_rejected(self):
        # 20 x 2.9 = 58.0 V: inside Yinlong's ceiling, above Altairnano's warm
        # ceiling of 2.8 V, and with zero margin at the top. Rejected.
        self.assertAlmostEqual(self.m.alternative_bus_maximum_v(2.9), 58.0)
        self.assertFalse(self.m.alternative_ceiling_has_margin(2.9))
        self.assertTrue(self.m.alternative_ceiling_has_margin(2.7))

    def test_raw_1_5_v_floor_would_need_more_cells_than_the_envelope_allows(self):
        # 36/1.5 = 24 cells, and 24 x 2.7 = 64.8 V, above the 58.4 V envelope.
        self.assertEqual(self.m.required_series_for_floor(36.0, 1.5), 24)
        self.assertGreater(
            self.m.required_series_for_floor(36.0, 1.5) * self.m.ADOPTED_CELL_CEILING_V,
            self.m.LEGACY_BUS_MAX_V)

    def test_usable_floor_is_1_8_v(self):
        self.assertAlmostEqual(self.m.USABLE_FLOOR_V, 1.8)


class NegativeControlTest(unittest.TestCase):
    """Fails if someone reinstates 58.4 V while LTO is the selected chemistry."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load('lto_bus')

    def test_guard_raises_on_58_4(self):
        with self.assertRaises(ValueError):
            self.m.assert_bus_maximum_admissible(58.4)

    def test_guard_accepts_the_design_point(self):
        self.assertAlmostEqual(self.m.assert_bus_maximum_admissible(54.0), 54.0)

    def test_guard_is_not_an_assert_statement(self):
        # -O must not be able to strip the guard out of the module.
        source = (HERE / 'lto_bus.py').read_text(encoding='utf-8')
        self.assertNotIn('\n    assert ', source)

    def test_no_model_output_equals_the_legacy_envelope(self):
        self.assertNotAlmostEqual(self.m.design_bus_maximum_v(), 58.4)
        self.assertLess(self.m.design_bus_maximum_v(), 58.4)


class DownstreamNumbersTest(unittest.TestCase):
    """Old value vs recomputed value, using the project's own constants."""

    @classmethod
    def setUpClass(cls):
        cls.m = _load('lto_bus')

    def test_precharge_fault_energy_at_58_4_matches_the_corpus(self):
        # precharge-budget-review.md §Independent checks: 156.591368 W, 54.806979 J
        self.assertAlmostEqual(self.m.precharge_fault_power(58.4), 156.591368, places=5)
        self.assertAlmostEqual(self.m.precharge_fault_energy(58.4, 0.350), 54.806979, places=5)

    def test_precharge_fault_energy_at_the_new_maximum(self):
        # 54.0^2 / 21.78 = 133.8843 W ; x 0.350 = 46.859507 J
        self.assertAlmostEqual(self.m.precharge_fault_power(54.0), 133.884297, places=5)
        self.assertAlmostEqual(self.m.precharge_fault_energy(54.0, 0.350), 46.859504, places=5)

    def test_precharge_energy_scales_with_v_squared(self):
        ratio = self.m.precharge_fault_energy(54.0) / self.m.precharge_fault_energy(58.4)
        self.assertAlmostEqual(ratio, (54.0 / 58.4) ** 2, places=9)

    def test_precharge_close_time_reproduces_the_corpus(self):
        # precharge-power-sources.md §4: 0.166955 s at 36 V, 0.162515 s at 58.4 V
        self.assertAlmostEqual(self.m.precharge_close_time(36.0), 0.166955, places=5)
        self.assertAlmostEqual(self.m.precharge_close_time(58.4), 0.162515, places=5)

    def test_precharge_close_time_at_the_new_maximum_is_shorter(self):
        t_new = self.m.precharge_close_time(54.0)
        self.assertLess(t_new, self.m.precharge_close_time(58.4))
        self.assertAlmostEqual(t_new, 0.161736, places=5)

    def test_reverse_pack_stress_and_mosfet_margin(self):
        self.assertAlmostEqual(self.m.reverse_pack_stress_v(58.4), 116.8)
        self.assertAlmostEqual(self.m.reverse_pack_stress_v(54.0), 108.0)
        self.assertAlmostEqual(self.m.mosfet_static_margin_v(58.4, 150.0), 33.2)
        self.assertAlmostEqual(self.m.mosfet_static_margin_v(54.0, 150.0), 42.0)

    def test_braking_resistor_power(self):
        self.assertAlmostEqual(self.m.braking_resistor_power(60.0, 9.4), 382.978722, places=5)
        self.assertAlmostEqual(self.m.braking_resistor_power(54.0, 9.4), 310.212766, places=5)

    def test_clamp_rise_at_the_new_maximum(self):
        # V = sqrt(V0^2 + 2Pt/C); 100 uF, 500 W
        self.assertAlmostEqual(self.m.clamp_rise_v(60.0, 500.0, 100e-6, 10e-6), 60.827626, places=5)
        self.assertAlmostEqual(self.m.clamp_rise_v(54.0, 500.0, 100e-6, 10e-6), 54.918121, places=5)

    def test_bus_input_current_does_not_move_at_the_low_corner(self):
        self.assertAlmostEqual(self.m.bus_input_current_a(1.1, 36.0), 0.0305556, places=6)
        self.assertAlmostEqual(self.m.bus_input_current_a(0.8, 36.0), 0.0222222, places=6)

    def test_bus_input_current_at_the_high_corner(self):
        self.assertAlmostEqual(self.m.bus_input_current_a(1.1, 58.4), 0.0188356, places=6)
        self.assertAlmostEqual(self.m.bus_input_current_a(1.1, 54.0), 0.0203704, places=6)

    def test_ov_band_does_not_move_and_becomes_more_admissible(self):
        # protection-milestone-report.md §OV thresholds: 59.417–61.226 V.
        self.assertAlmostEqual(self.m.OV_TRIP_MIN_V, 59.417)
        self.assertAlmostEqual(self.m.OV_TRIP_MAX_V, 61.226)
        self.assertAlmostEqual(self.m.ov_band_margin_v(54.0), 5.417, places=3)
        self.assertAlmostEqual(self.m.ov_band_margin_v(58.4), 1.017, places=3)

    def test_present_ov_band_is_admissible_at_54_v(self):
        self.assertTrue(self.m.ov_band_admissible(54.0))

    def test_present_ov_band_is_NOT_admissible_at_58_4_v(self):
        # 59.417 V leaves 1.017 V over 58.4 V, under the documented 2.114 V
        # hysteresis it must clear.
        self.assertFalse(self.m.ov_band_admissible(58.4))

    def test_supercap_surge_ceiling_forces_a_second_clamp(self):
        # 2.85 V/cell surge x 20 = 57.00 V, which is BELOW the 59.417 V OV trip.
        self.assertAlmostEqual(self.m.supercap_surge_ceiling_v(20, 2.85), 57.0)
        self.assertLess(self.m.supercap_surge_ceiling_v(20, 2.85), self.m.OV_TRIP_MIN_V)
        self.assertTrue(self.m.supercap_needs_own_clamp(20, 2.85))


class SupercapacitorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _load('lto_bus')

    def test_eaton_400f_values_are_from_the_datasheet(self):
        cell = self.m.EATON_XV3560
        self.assertAlmostEqual(cell.cell_f, 400)
        self.assertAlmostEqual(cell.cell_v, 2.7)
        self.assertAlmostEqual(cell.esr_ohm, 0.0032)
        self.assertAlmostEqual(cell.mass_g, 72)
        self.assertAlmostEqual(cell.diameter_mm, 35.0)
        self.assertAlmostEqual(cell.length_mm, 63.0)

    def test_datasheet_stored_energy_cross_check(self):
        # Eaton TD4424 prints "Stored energy 0.41 Wh" for the 400 F cell.
        self.assertAlmostEqual(self.m.single_cell_energy_wh(400, 2.7), 0.405, places=4)

    def test_string_is_voltage_driven(self):
        s = self.m.supercap_string(400, 2.7, 0.0032, 72, 35.0, 63.0, 54.0, 36.0)
        self.assertEqual(s['n'], 20)
        self.assertAlmostEqual(s['capacitance_f'], 20.0)
        self.assertAlmostEqual(s['esr_ohm'], 0.064)
        self.assertAlmostEqual(s['usable_wh'], 4.5, places=6)

    def test_more_energy_needs_no_more_cells(self):
        # The 0.7709 Wh excursion needs only 3.426 F; the 54 V string already has 20 F.
        need_f = self.m.capacitance_for_excursion(0.7709, 54.0, 36.0)
        self.assertAlmostEqual(need_f, 3.4262, places=4)
        self.assertGreater(20.0, need_f)

    def test_margin_over_the_documented_excursion(self):
        s = self.m.supercap_string(400, 2.7, 0.0032, 72, 35.0, 63.0, 54.0, 36.0)
        self.assertAlmostEqual(s['excursion_margin'], 4.5 / 0.7709, places=4)

    def test_thirty_second_case_is_smaller(self):
        # storage-review.md §Findings 3: 30 s ramp excursion is 0.5592 Wh, not 0.7709 Wh.
        self.assertLess(self.m.launch_excursion_wh(30.0), self.m.launch_excursion_wh(10.0))

    def test_mass_and_volume_at_pack_level(self):
        s = self.m.supercap_string(400, 2.7, 0.0032, 72, 35.0, 63.0, 54.0, 36.0)
        self.assertAlmostEqual(s['cell_mass_kg'], 1.44)
        self.assertAlmostEqual(s['pack_mass_kg'], 1.44 * 1.35, places=6)
        # pi/4 * 3.5^2 * 6.3 = 60.6188 cm3 per cell
        self.assertAlmostEqual(s['cell_volume_l'], 20 * 60.6188 / 1000, places=3)

    def test_pack_energy_density_corrects_the_corpus(self):
        # 0.405 Wh / 0.072 kg = 5.625 Wh/kg cell; the corpus's 6.53 used 62 g.
        s = self.m.supercap_string(400, 2.7, 0.0032, 72, 35.0, 63.0, 54.0, 36.0)
        self.assertAlmostEqual(s['cell_wh_per_kg'], 5.625, places=4)
        self.assertAlmostEqual(s['pack_wh_per_kg'], 5.625 / 1.35, places=4)

    def test_cell_count_buys_voltage_not_energy(self):
        # E_string = N * E_cell: one cell over 1.8-2.7 V stores 0.2250 Wh.
        per_cell = self.m.supercap_cell_energy_wh(400, 2.7, 1.8)
        self.assertAlmostEqual(per_cell, 0.225, places=6)
        # four cells carry 0.9 Wh, already more than the 0.7709 Wh excursion
        self.assertEqual(self.m.min_cells_for_excursion(0.7709, 400, 2.7, 1.8), 4)
        self.assertGreater(4 * per_cell, 0.7709)
        self.assertLess(3 * per_cell, 0.7709)

    def test_permanently_parallel_breaks_the_bus_capacitance_ceiling(self):
        opts = self.m.supercap_options(0.7709, 54.0, 36.0)
        direct = opts[0]
        self.assertEqual(direct['cells'], 20)
        self.assertAlmostEqual(direct['capacitance_f'], 20.0)
        self.assertFalse(direct['needs_converter'])
        self.assertGreater(direct['bus_cap_ratio'], 1000)
        self.assertAlmostEqual(direct['precharge_tau_s'], 447.4, places=1)

    def test_string_voltage_equals_the_bus_window_without_a_converter(self):
        # This is the load-bearing consequence of choosing 2.7 V / 1.8 V.
        opts = self.m.supercap_options(0.7709, 54.0, 36.0)
        switched = opts[1]
        self.assertAlmostEqual(switched['string_v_max'], 54.0)
        self.assertAlmostEqual(switched['string_v_min'], 36.0)
        self.assertFalse(switched['needs_converter'])
        self.assertTrue(switched['needs_own_switch'])
        self.assertTrue(switched['needs_own_ov_clamp'])
        self.assertAlmostEqual(switched['own_surge_ceiling_v'], 57.0)

    def test_switched_string_leaves_the_entry_circuit_alone(self):
        opts = self.m.supercap_options(0.7709, 54.0, 36.0)
        switched = opts[1]
        self.assertEqual(switched['bus_cap_ratio'], 0.0)
        self.assertIsNone(switched['precharge_tau_s'])

    def test_minimum_cell_count_option_is_the_wrong_objective(self):
        opts = self.m.supercap_options(0.7709, 54.0, 36.0)
        conv = opts[2]
        self.assertTrue(conv['needs_converter'])
        self.assertEqual(conv['cells'], 4)
        self.assertLess(conv['cells'], opts[0]['cells'])
        self.assertLess(conv['cell_mass_kg'], opts[0]['cell_mass_kg'])
        self.assertGreater(conv['usable_over_excursion'], 1.0)
        # but the string is only 7.2-10.8 V, so the current and ESR heat are large
        self.assertAlmostEqual(conv['string_v_min'], 7.2)
        self.assertGreater(conv['string_current_at_500w_low_v_a'], 60.0)
        self.assertGreater(conv['esr_loss_at_500w_low_v_w'], 50.0)
        self.assertGreater(conv['converter_ratio_at_500w'], 4.0)


class InputValidationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.m = _load('lto_bus')

    def test_negative_and_zero_inputs_rejected(self):
        with self.assertRaises(ValueError):
            self.m.precharge_fault_energy(-1.0)
        with self.assertRaises(ValueError):
            self.m.bus_input_current_a(1.1, 0.0)
        with self.assertRaises(ValueError):
            self.m.braking_resistor_power(54.0, 0.0)
        with self.assertRaises(ValueError):
            self.m.capacitance_for_excursion(0.0, 54.0, 36.0)
        with self.assertRaises(ValueError):
            self.m.capacitance_for_excursion(0.7709, 36.0, 54.0)

    def test_unknown_cell_name_raises(self):
        with self.assertRaises(KeyError):
            self.m.cell('no-such-cell')


if __name__ == '__main__':
    unittest.main()
