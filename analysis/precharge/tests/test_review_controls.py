"""Independent closed-form controls; no hardware/switching qualification."""
import math
import unittest
from legacy_model import Config, simulate


class AnalyticControls(unittest.TestCase):
    def test_unloaded_rc_and_energy_balance(self):
        # Stop before MAIN; effectively remove bleed and sink loads.
        c = Config(sink_w=0, bleed_ohm=1e30, duration_s=.5, dt_s=.0000125)
        r = simulate(c)
        t = c.duration_s - .02
        resistance = c.source_ohm + c.precharge_ohm
        tau = resistance * c.cap_f
        voltage = c.pack_v * (1 - math.exp(-t / tau))
        loss = .5 * c.cap_f * c.pack_v**2 * (1 - math.exp(-2*t/tau))
        self.assertIsNone(r['close_s'])
        self.assertAlmostEqual(r['final_bus_v'], voltage, delta=.001)
        self.assertAlmostEqual(r['precharge_j'], loss*c.precharge_ohm/resistance, delta=.0002)
        # Integrated source energy = Vpack * Q; compare capacitor + both resistors.
        source = c.pack_v * c.cap_f * r['final_bus_v']
        stored = .5 * c.cap_f * r['final_bus_v']**2
        dissipated = r['precharge_j'] * resistance/c.precharge_ohm
        self.assertLess(abs(source-stored-dissipated), .0003)

    def test_short_closed_form(self):
        c = Config(short_ohm=1, dt_s=.0000125)
        r = simulate(c)
        # Bus stays below 15 V: no sink standby. PRE runs .02 <= t < 1.5.
        rp = c.precharge_ohm + c.source_ohm
        rl = 1/(1/c.short_ohm + 1/c.bleed_ohm)
        tau = c.cap_f/(1/rp + 1/rl)
        steady_v = c.pack_v*rl/(rp+rl)
        a = (c.pack_v-steady_v)/rp
        b = steady_v/rp
        t = 1.5-.02
        energy = c.precharge_ohm*(a*a*t + 2*a*b*tau*(1-math.exp(-t/tau))
                                  + b*b*tau/2*(1-math.exp(-2*t/tau)))
        self.assertEqual(r['fault'], 'timeout')
        self.assertAlmostEqual(r['precharge_j'], energy, delta=.00001)

    def test_three_step_sensitivity(self):
        for args in ({}, {'short_ohm': 1}, {'pack_v': 0, 'regen_a': 1}):
            rows = [simulate(Config(dt_s=dt, **args)) for dt in (.00005, .000025, .0000125)]
            with self.subTest(args=args):
                self.assertEqual(rows[0]['state'], rows[-1]['state'])
                self.assertLess(abs(rows[0]['precharge_j']-rows[-1]['precharge_j']), .005)
                self.assertLess(abs(rows[0]['max_bus_v']-rows[-1]['max_bus_v']), .04)
                if rows[0]['close_s'] is not None:
                    self.assertLess(abs(rows[0]['close_s']-rows[-1]['close_s']), .002)


if __name__ == '__main__':
    unittest.main()
