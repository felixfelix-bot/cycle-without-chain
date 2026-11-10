"""Tests for analysis/cx/chopper_gate_charge.py — the PROT-11 term.

The point of these tests is that the omitted gate-charge load is arithmetic:
the module reproduces the published 1.027108922 W ledger exactly, then adds the
term the ledger says it excludes, then inverts for the frequency at which the
1.1 W envelope is exhausted.

Nothing here is electrical qualification. Qg is a datasheet limit at 10 V while
the driver runs at 12 V, and no chopper frequency is specified anywhere in the
corpus, so these are screening bounds on an unbounded omission.
"""

import importlib.util
import unittest
from pathlib import Path


def _load():
    path = Path(__file__).with_name("chopper_gate_charge.py")
    if not path.is_file():
        raise AssertionError("chopper_gate_charge.py not implemented")
    spec = importlib.util.spec_from_file_location("chopper_gate_charge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChopperGateChargeTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    # --- the published ledger must reproduce before anything is added ----
    def test_published_sink_input_reproduces(self):
        self.assertAlmostEqual(self.m.published_sink_input_w(),
                               1.027108922, places=9)

    def test_published_margin_reproduces(self):
        self.assertAlmostEqual(self.m.published_margin_w(),
                               0.072891078, places=9)

    def test_all_oc_margin_reproduces(self):
        self.assertAlmostEqual(
            self.m.published_margin_w(self.m.ALL_OC_U4_INPUT_W),
            0.045960225, places=9)

    def test_envelope_is_1_1_w(self):
        self.assertEqual(self.m.ENVELOPE_W, 1.1)

    # --- the omitted term -------------------------------------------------
    def test_gate_charge_scales_with_frequency(self):
        a = self.m.gate_charge_power_w(10_000)
        b = self.m.gate_charge_power_w(20_000)
        self.assertAlmostEqual(b, 2 * a, places=12)

    def test_gate_charge_at_zero_frequency_is_zero(self):
        self.assertEqual(self.m.gate_charge_power_w(0.0), 0.0)

    def test_gate_charge_uses_max_not_typical(self):
        # Safety-relevant direction: the default must be the pessimistic Qg.
        default = self.m.gate_charge_power_w(20_000)
        typical = self.m.gate_charge_power_w(
            20_000, qg_c=self.m.QG_TYP_10V_C)
        self.assertGreater(default, typical)

    def test_pulldown_at_full_duty_is_14_4_mw(self):
        # 12^2 / 10k = 14.4 mW, the term that dominates at realistic f_chop.
        self.assertAlmostEqual(self.m.gate_pulldown_power_w(1.0),
                               0.0144, places=12)

    def test_pulldown_is_smaller_at_lower_duty(self):
        self.assertLess(self.m.gate_pulldown_power_w(0.25),
                        self.m.gate_pulldown_power_w(0.75))

    def test_pulldown_exceeds_gate_charge_below_crossover(self):
        # At low f_chop the static 10k pulldown dominates the gate current.
        self.assertGreater(self.m.gate_pulldown_power_w(0.5),
                           self.m.gate_charge_power_w(5_000))

    def test_gate_charge_exceeds_pulldown_above_crossover(self):
        # Above roughly 9.7 kHz at half duty the switching term dominates.
        self.assertGreater(self.m.gate_charge_power_w(20_000),
                           self.m.gate_pulldown_power_w(0.5))

    def test_crossover_frequency_at_half_duty_is_about_9_7_khz(self):
        # 0.5 * 12^2/10k = 7.2 mW, divided by Qg_max * 12 V.
        expected = self.m.gate_pulldown_power_w(0.5) / (
            self.m.QG_MAX_10V_C * self.m.GATE_DRIVE_V)
        self.assertAlmostEqual(expected, 9_677, delta=2)
        self.assertLess(self.m.gate_charge_power_w(expected - 100),
                        self.m.gate_pulldown_power_w(0.5))
        self.assertGreater(self.m.gate_charge_power_w(expected + 100),
                           self.m.gate_pulldown_power_w(0.5))

    # --- monotonicity and the break frequency -----------------------------
    def test_sink_input_increases_with_frequency(self):
        self.assertLess(self.m.sink_input_with_chopper_w(10_000, 0.5),
                        self.m.sink_input_with_chopper_w(50_000, 0.5))

    def test_sink_input_increases_with_duty(self):
        self.assertLess(self.m.sink_input_with_chopper_w(20_000, 0.25),
                        self.m.sink_input_with_chopper_w(20_000, 0.75))

    def test_at_break_frequency_the_envelope_is_exhausted(self):
        f = self.m.max_f_chop_hz(0.5)
        self.assertAlmostEqual(
            self.m.sink_input_with_chopper_w(f, 0.5),
            self.m.ENVELOPE_W, places=9)

    def test_above_break_frequency_the_envelope_is_exceeded(self):
        f = self.m.max_f_chop_hz(0.5)
        self.assertGreater(
            self.m.sink_input_with_chopper_w(f * 1.25, 0.5),
            self.m.ENVELOPE_W)

    def test_break_frequency_falls_as_duty_rises(self):
        self.assertGreater(self.m.max_f_chop_hz(0.0),
                           self.m.max_f_chop_hz(1.0))

    def test_break_frequency_around_49_khz_at_max_qg_half_duty(self):
        # The headline number quoted in the report.
        self.assertAlmostEqual(self.m.max_f_chop_hz(0.5), 49_106, delta=1)

    def test_all_oc_scenario_has_less_headroom(self):
        self.assertLess(
            self.m.max_f_chop_hz(0.5, u4_input_w=self.m.ALL_OC_U4_INPUT_W),
            self.m.max_f_chop_hz(0.5))

    def test_break_frequency_is_zero_when_margin_already_gone(self):
        self.assertEqual(
            self.m.max_f_chop_hz(0.5, u4_input_w=0.30), 0.0)

    def test_break_frequency_is_zero_when_pulldown_alone_exceeds(self):
        self.assertEqual(
            self.m.max_f_chop_hz(1.0, envelope_w=1.035), 0.0)

    # --- input validation -------------------------------------------------
    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            self.m.gate_charge_power_w(-1)

    def test_duty_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            self.m.gate_pulldown_power_w(1.5)
        with self.assertRaises(ValueError):
            self.m.gate_pulldown_power_w(-0.1)


if __name__ == "__main__":
    unittest.main()
