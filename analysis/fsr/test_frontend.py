import math
import unittest
import frontend as f

class FrontendTests(unittest.TestCase):
    def test_divider_limits(self):
        self.assertEqual(f.divider(math.inf), 0)
        self.assertAlmostEqual(f.divider(0), 3.3*10000/12000)
    def test_divider_midpoint(self):
        self.assertAlmostEqual(f.divider(8000), 1.65)
    def test_ratio_supply(self):
        self.assertAlmostEqual(f.divider(10000, supply=3)/3, f.divider(10000)/3.3)
    def test_conductance_limits(self):
        self.assertEqual(f.conductance(math.inf), .3)
        self.assertAlmostEqual(f.conductance(10000), .6)
        self.assertGreater(f.conductance(100), 3.25)
    def test_bridge_balance_and_clip(self):
        self.assertAlmostEqual(f.bridge(10000),1.65)
        self.assertLess(f.bridge(math.inf),0)
        self.assertGreater(f.bridge(0),3.3)
    def test_codes(self):
        self.assertEqual(f.code(-1),0)
        self.assertEqual(f.code(4),4095)
        self.assertEqual(f.code(1.65),2048)
    def test_safety_independence(self):
        for analog in [None,0,1,float('nan')]:
            self.assertTrue(f.inhibit(True, analog))
    def test_noise(self):
        self.assertAlmostEqual(f.johnson(10000,50), math.sqrt(4*1.380649e-23*300*10000*50))
    def test_invalid_resistance(self):
        with self.assertRaises(ValueError): f.divider(-1)

if __name__ == '__main__': unittest.main()
