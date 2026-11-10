import unittest
import math
import implemented as f
class ImplementedTests(unittest.TestCase):
    def test_endpoints(self):
        self.assertEqual(f.adc(math.inf),0)
        self.assertAlmostEqual(f.adc(0),3.3*(10/21)*(10000/11004.5))
        self.assertGreater(f.adc(1000),f.adc(10000))
    def test_negative(self):
        with self.assertRaises(ValueError): f.adc(-1)
    def test_rc_and_leakage(self):
        r=f.results()
        self.assertLess(r['sense_half_lsb_settle_s'],.010)
        self.assertLess(r['adc_tau_s'],.0001)
        self.assertAlmostEqual(r['off_leakage_V'],.0202)
        self.assertAlmostEqual(r['return_ground_fault_current_A'],.00035)
