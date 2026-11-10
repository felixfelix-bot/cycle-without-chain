import unittest
from calculations import envelope, precharge, adc_window

class Calculations(unittest.TestCase):
    def test_envelope(self):
        x = envelope()
        self.assertAlmostEqual(x['bus_A'], 500/36)
        self.assertAlmostEqual(x['shunt_W'], 1.8)
        self.assertAlmostEqual(x['adc_low_V'], .45)
        self.assertAlmostEqual(x['dump_ohm'], 7.2)
        self.assertEqual(x['dump_J'], 5000)
        self.assertAlmostEqual(x['vm_static_margin_V'], 63)
    def test_precharge(self):
        x = precharge(58.4, .001, 100)
        self.assertAlmostEqual(x['initial_A'], .584)
        self.assertAlmostEqual(x['resistor_J'], 1.70528)
        self.assertGreater(x['time_99_s'], .46)
    def test_adc(self):
        self.assertAlmostEqual(adc_window(42.5e6, 24.5, 12.5, 3), 2.611764705882353e-6)
    def test_invalid(self):
        for args in [(58.4, 0, 100), (58.4, .001, -1)]:
            with self.assertRaises(ValueError): precharge(*args)
        with self.assertRaises(ValueError): adc_window(0, 24.5, 12.5, 3)

if __name__ == '__main__': unittest.main()
