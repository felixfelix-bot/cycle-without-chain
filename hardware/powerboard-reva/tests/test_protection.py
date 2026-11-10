import unittest
from protection_calculations import thresholds, corners, latch_next, energy_rise

class Protection(unittest.TestCase):
    def test_thresholds(self):
        on, off = thresholds()
        self.assertTrue(60 < on < 61)
        self.assertTrue(57 < off < 59)
        self.assertGreater(on-off, 2)
    def test_corners(self):
        c = corners()
        self.assertGreater(c['on_min'], 58.4)
        self.assertLess(c['on_max'], 63)
        self.assertLess(c['off_max'], c['on_min'])
    def test_set_dominant(self):
        for q in [False, True]:
            self.assertTrue(latch_next(q, False, True))
            self.assertFalse(latch_next(q, True, True))
            self.assertEqual(latch_next(q, True, False), q)
    def test_energy(self):
        self.assertAlmostEqual(energy_rise(60, .0001, 500, .00001), 60.8276253)
        with self.assertRaises(ValueError): energy_rise(60, 0, 500, .01)
