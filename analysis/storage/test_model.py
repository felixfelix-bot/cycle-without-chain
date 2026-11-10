import unittest
import importlib.util
from pathlib import Path

class ModelTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name('model.py')
        self.assertTrue(path.exists(), 'storage model not implemented')
        spec = importlib.util.spec_from_file_location('model', path)
        assert spec is not None and spec.loader is not None
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)

    def test_series_energy(self):
        c, r, wh = self.m.cap_string(300, .0045, 20, 50, 25)
        self.assertEqual(c, 15)
        self.assertAlmostEqual(r, .09)
        self.assertAlmostEqual(wh, 3.90625)

    def test_current_and_heat(self):
        i, loss, terminal = self.m.discharge(50, .1, 490)
        self.assertAlmostEqual(i, 10)
        self.assertAlmostEqual(loss, 10)
        self.assertAlmostEqual(terminal, 49)

    def test_charge_separate(self):
        i, loss, terminal = self.m.charge(50, .1, 510)
        self.assertAlmostEqual(i, 10)
        self.assertAlmostEqual(loss, 10)
        self.assertAlmostEqual(terminal, 51)

    def test_impossible_power(self):
        with self.assertRaises(ValueError): self.m.discharge(10, 1, 26)

    def test_rider_offsets_not_whole_ke(self):
        a = self.m.launch(150, 25, rider=0)
        b = self.m.launch(150, 25, rider=250)
        self.assertAlmostEqual(a['buffer_wh'] - b['buffer_wh'], 250*.9*10/3600)
        self.assertAlmostEqual(a['ke_wh'], .5*150*(25/3.6)**2/3600)

    def test_regen_independent(self):
        a = self.m.launch(140,20,regen=.3)
        b = self.m.launch(140,20,regen=.6)
        self.assertAlmostEqual(b['regen_wh'], 2*a['regen_wh'])
        self.assertEqual(a['buffer_wh'], b['buffer_wh'])

    def test_surplus_is_not_negative_storage(self):
        self.assertEqual(self.m.launch(140,20,rider=2000)['buffer_wh'],0)

    def test_chronological_excursion_independent_midpoint(self):
        # Independent force/velocity quadrature, not the model's work integral.
        n, dt, cumulative, low, high = 100000, 10/100000, 0., 0., 0.
        for j in range(n):
            v = (j+.5)*dt*(25/3.6)/10
            wheel = (150*(25/3.6)/10 + 150*9.81*.006 + .5*1.225*.5*v*v)*v
            cumulative += (wheel/(8/9)+5-250*.9)*dt/3600
            low, high = min(low, cumulative), max(high, cumulative)
        result = self.m.launch(150, 25)
        self.assertAlmostEqual(result['net_bus_wh'], cumulative, places=7)
        self.assertAlmostEqual(result['excursion_wh'], high-low, places=7)
        self.assertAlmostEqual(result['charge_headroom_wh'], -low, places=7)
        self.assertGreater(result['excursion_wh'], result['buffer_wh'])
        v = 25/3.6
        force = 150*v/10 + 150*9.81*.006 + .5*1.225*.5*v*v
        self.assertAlmostEqual(result['peak_w'], force*v/(8/9)+5-225)

    def test_net_surplus_still_needs_capacity(self):
        result = self.m.launch(150, 25, seconds=30)
        self.assertEqual(result['buffer_wh'], 0)
        self.assertLess(result['net_bus_wh'], 0)
        self.assertGreater(result['excursion_wh'], .55)
        # Total traction bus demand, not just storage residual, below 500 W.
        self.assertLess(result['peak_w']+225-5, 500)

    def test_cap_voltage_corners(self):
        # 36 V terminal needs Vopen=36+R*P/36, not Vopen=36.
        _, r, _ = self.m.cap_string(300, .0045, 20, 50, 36)
        self.assertAlmostEqual(self.m.discharge(37.25, r, 500)[2], 36)
        self.assertLess(self.m.discharge(36, r, 500)[2], 36)
        self.assertGreater(self.m.charge(50, r, 475)[2], 50)
        for r in (.09, .18):
            i, heat, terminal = self.m.discharge(25, r, 500/.95)
            self.assertAlmostEqual(25*i, 500/.95 + heat)
            self.assertAlmostEqual(terminal*i, 500/.95)
            i, heat, terminal = self.m.charge(50, r, 475)
            self.assertAlmostEqual(50*i+heat, 475)
        self.assertAlmostEqual(20*2.5, 50)
        self.assertAlmostEqual(16*3.6, 57.6)
        self.assertAlmostEqual(13*4.2, 54.6)

    def test_invalid_launch(self):
        with self.assertRaises(ValueError): self.m.launch(150, 25, seconds=0)
        with self.assertRaises(ValueError): self.m.launch(150, 25, eta_drive=0)

    def test_invalid_window(self):
        with self.assertRaises(ValueError): self.m.cap_string(300,.0045,20,25,50)

if __name__ == '__main__': unittest.main()
