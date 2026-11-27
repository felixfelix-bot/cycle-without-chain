"""Executable intent tests; unittest checks remain active with python -O."""
import importlib.util
import itertools
import unittest

SPEC = importlib.util.find_spec("model")
if SPEC is not None:
    from model import BrakeIntent, Inputs, Lever


class BrakeIntentTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(SPEC, "brake intent model not implemented")
        self.model = BrakeIntent()

    def inputs(self, **changes):
        values = dict(left=Lever(False, 0.0), right=Lever(False, 0.0))
        values.update(changes)
        return Inputs(**values)

    def test_no_brake_never_commands_regen_or_dump(self):
        for accepts, cool in itertools.product((False, True), repeat=2):
            out = self.model.step(self.inputs(battery_accepts=accepts, dump_available_cool=cool, throttle=0.7))
            self.assertEqual((out.regen, out.dump_command), (0.0, 0.0))
            self.assertEqual(out.torque_command, 0.7)

    def test_either_or_both_healthy_levers_request_brake(self):
        for left, right in ((0.5, 0), (0, 0.7), (0.5, 0.7)):
            out = self.model.step(self.inputs(left=Lever(bool(left), left), right=Lever(bool(right), right), throttle=1))
            self.assertFalse(out.positive_allowed)
            self.assertTrue(out.negative_allowed)
            self.assertEqual(out.regen, max(left, right))
            self.assertEqual(out.torque_command, -max(left, right))
            self.assertEqual(out.dump_command, 0)

    def test_full_pack_uses_cool_dump_not_battery(self):
        out = self.model.step(self.inputs(left=Lever(True, 0.8), battery_accepts=False))
        self.assertEqual((out.regen, out.dump_command, out.torque_command), (0, 0.8, -0.8))

    def test_hot_dump_allows_independently_accepted_battery_regen(self):
        out = self.model.step(self.inputs(left=Lever(True, 1), dump_available_cool=False))
        self.assertEqual((out.regen, out.dump_command, out.torque_command), (1, 0, -1))

    def test_full_pack_hot_dump_has_no_electrical_braking(self):
        out = self.model.step(self.inputs(left=Lever(True, 1), battery_accepts=False, dump_available_cool=False, throttle=1))
        self.assertEqual((out.regen, out.dump_command, out.torque_command), (0, 0, 0))
        self.assertFalse(out.positive_allowed)
        self.assertFalse(out.negative_allowed)

    def test_disagreement_and_open_wire_on_either_lever_latch(self):
        bad_channels = (Lever(True, 0), Lever(False, 0.4), Lever(None, 0), Lever(False, None), Lever(True, float('nan')), Lever(True, 1.1), Lever(False, -0.1))
        for side, bad in itertools.product(('left', 'right'), bad_channels):
            with self.subTest(side=side, bad=bad):
                model = BrakeIntent()
                out = model.step(self.inputs(**{side: bad}, throttle=1))
                self.assertTrue(out.fault_latched)
                self.assertEqual((out.torque_command, out.regen, out.dump_command), (0, 0, 0))
                self.assertEqual(model.step(self.inputs(throttle=1)).torque_command, 0)
                self.assertTrue(model.step(self.inputs(left=Lever(True, 1), manual_reset=True)).fault_latched)
                self.assertFalse(model.step(self.inputs(manual_reset=True)).fault_latched)
                self.assertEqual(model.step(self.inputs(throttle=0.5)).torque_command, 0.5)

    def test_each_hardware_kill_overrides_brake_and_stuck_mcu_demand(self):
        for gate, braking in itertools.product(('estop', 'hard_overcurrent', 'watchdog_expired'), (False, True)):
            with self.subTest(gate=gate, braking=braking):
                model = BrakeIntent()
                out = model.step(self.inputs(left=Lever(braking, float(braking)), throttle=1, **{gate: True}, manual_reset=True))
                self.assertFalse(out.gate_enabled)
                self.assertEqual((out.torque_command, out.regen, out.dump_command), (0, 0, 0))
                self.assertTrue(out.fault_latched)
                self.assertTrue(model.step(self.inputs()).fault_latched)
                self.assertFalse(model.step(self.inputs(manual_reset=True)).fault_latched)

    def test_emergency_ov_clamp_is_independent_and_can_drag_without_brake(self):
        for kill, accepts, cool in itertools.product((False, True), repeat=3):
            out = BrakeIntent().step(self.inputs(emergency_overvoltage=True, watchdog_expired=kill, battery_accepts=accepts, dump_available_cool=cool))
            self.assertTrue(out.emergency_clamp)
            self.assertTrue(out.uncommanded_drag_possible)
            self.assertEqual((out.regen, out.dump_command), (0, 0))
        self.assertFalse(BrakeIntent().step(self.inputs()).emergency_clamp)


if __name__ == '__main__':
    unittest.main(verbosity=2)
