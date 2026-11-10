import unittest
from legacy_model import Config, simulate

class SequenceTests(unittest.TestCase):
    def test_passive_loaded_fails(self):
        r = simulate(Config(delayed_aux=False))
        self.assertFalse(r['run'])
        self.assertEqual(r['fault'], 'timeout')
    def test_delayed_aux_starts(self):
        r = simulate(Config())
        self.assertTrue(r['run'])
        self.assertLess(r['precharge_j'], 3)
        self.assertLess(r['close_mismatch_v'], 1)
    def test_voltage_capacitance_surge_sweep(self):
        for v in (36, 48, 58.4):
            for c in (.00094, .0015):
                for surge in (.1, .3, .5):
                    with self.subTest(v=v,c=c,surge=surge):
                        self.assertTrue(simulate(Config(pack_v=v, cap_f=c, surge_a=surge))['run'])
    def test_sink_budget_violation(self):
        self.assertFalse(simulate(Config(sink_w=.4))['run'])
    def test_source_limit(self):
        self.assertEqual(simulate(Config(source_limit_a=.03))['fault'], 'timeout')
    def test_short_times_out(self):
        r=simulate(Config(short_ohm=1))
        self.assertEqual(r['fault'], 'timeout')
        self.assertLess(r['precharge_j'], 55)
    def test_reverse_battery(self):
        r=simulate(Config(pack_v=-58.4))
        self.assertFalse(r['run'])
        self.assertEqual(r['peak_pack_a'],0)
    def test_hot_bus_no_connect(self):
        r=simulate(Config(initial_bus_v=65))
        self.assertEqual(r['fault'],'hot_bus')
        self.assertFalse(r['run'])
    def test_pack_absent_pm_powers_sink(self):
        r=simulate(Config(pack_v=0, regen_a=1))
        self.assertFalse(r['run'])
        self.assertGreater(r['dump_j'], 0)
        self.assertLess(r['max_bus_v'], 61)
    def test_charge_refusal_opens(self):
        r=simulate(Config(regen_a=1,regen_start_s=1.2,charge_allowed=False))
        self.assertEqual(r['fault'],'charge_refused')
        self.assertGreater(r['dump_j'],0)
    def test_accepted_regen(self):
        r=simulate(Config(regen_a=1,regen_start_s=1.2))
        self.assertGreater(r['charge_j'],0)
    def test_weld_detect_not_isolation(self):
        r=simulate(Config(welded=True))
        self.assertEqual(r['fault'],'unexpected_connection')
        self.assertGreater(r['max_bus_v'],50)
    def test_timestep_convergence(self):
        a,b=simulate(Config()),simulate(Config(dt_s=.000025))
        self.assertAlmostEqual(a['close_s'], b['close_s'],delta=.002)
        self.assertAlmostEqual(a['precharge_j'], b['precharge_j'],delta=.005)

if __name__ == '__main__': unittest.main()
