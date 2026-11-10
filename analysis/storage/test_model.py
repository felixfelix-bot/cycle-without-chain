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

    def test_invalid_window(self):
        with self.assertRaises(ValueError): self.m.cap_string(300,.0045,20,25,50)

if __name__ == '__main__': unittest.main()
