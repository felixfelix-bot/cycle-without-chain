import unittest
import model

class BudgetTests(unittest.TestCase):
    def test_component_budget_replaces_impossible_allocations(self):
        c=model.Config()
        self.assertGreaterEqual(c.sink_w, .825)
        self.assertGreaterEqual(c.controller_w, .70)
        self.assertEqual(c.precharge_ohm,22)
    def test_corners_and_startup(self):
        for v in (36,58.4):
            for r in (21.78,22.22):
                c=model.Config(pack_v=v,precharge_ohm=r, source_limit_a=3)
                a=model.simulate(c)
                self.assertTrue(a['run'],a)
                self.assertLess(a['close_s'],.30)
    def test_failed_open_never_enables_drive(self):
        self.assertFalse(model.simulate(model.Config(main_path_available=False))['run'])
    def test_energy_and_convergence(self):
        for v in (36,58.4):
            results=[]
            for dt in (50e-6,25e-6,12.5e-6):
                a=model.simulate(model.Config(pack_v=v,dt_s=dt,source_limit_a=3))
                residual=a['source_j']-sum(a[k] for k in ('series_j','bleed_j','load_j','capacitor_j'))
                self.assertLess(abs(residual),.004)
                self.assertEqual(a['sink_starts'],1)
                results.append(a)
            self.assertLess(abs(results[0]['close_s']-results[-1]['close_s']),.001)
            self.assertLess(abs(results[0]['precharge_j']-results[-1]['precharge_j']),.005)
    def test_short_and_load_violation(self):
        a=model.simulate(model.Config(short_ohm=.1,precharge_ohm=21.78,timeout_s=.350,dt_s=5e-6,duration_s=.36))
        self.assertEqual(a['fault'],'timeout')
        self.assertLess(a['precharge_j'],54.807)
        self.assertFalse(model.simulate(model.Config(pack_v=36,sink_w=2))['run'])
        self.assertFalse(model.simulate(model.Config(source_limit_a=.03))['run'])
    def test_stuck_pre_diagnostic_bound(self):
        import math
        g=1/334.5+1/21.78
        eq=(.010+36/21.78)/g
        mismatch=36-(eq+(37-eq)*math.exp(-.038*g/.0015))
        self.assertGreater(mismatch-.10,.70)
    def test_no_silent_weld_oracle(self):
        self.assertNotEqual(model.simulate(model.Config(welded=True))['fault'],'unexpected_connection')
        self.assertEqual(model.simulate(model.Config(off_path_alarm=True))['fault'],'unexpected_connection')
        for kwargs in ({'gate_valid':False},{'diagnostic_load_valid':False}):
            self.assertFalse(model.simulate(model.Config(**kwargs))['run'])
    def test_unknown_external_source_never_proves(self):
        self.assertFalse(model.simulate(model.Config(pm_quiet_valid=False))['run'])
