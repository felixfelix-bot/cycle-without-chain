import unittest
from model import descent, split, resistor_bank, thermal_step

class BrakingTests(unittest.TestCase):
    def test_potential_energy_balance(self):
        x = descent(150, .10, 20, 300)
        self.assertAlmostEqual(x['gravity_w']*x['seconds'], 150*9.80665*300)
        self.assertAlmostEqual(x['brake_j']+x['road_j'], x['potential_j'])
    def test_no_drag_limit(self):
        x = descent(140, .05, 10, 600, crr=0, cda=0)
        self.assertAlmostEqual(x['brake_j'], 140*9.80665*600)
    def test_full_pack_conservation(self):
        x = split(1000, .5, .8, 0, 300)
        self.assertEqual(x, dict(generator_w=375., motor_controller_loss_w=75., dump_w=300., battery_w=0., mechanical_w=625.))
    def test_regen_unavailable(self):
        self.assertEqual(split(1000, 0, .8, 0, 300)['mechanical_w'], 1000)
    def test_battery_acceptance(self):
        x=split(1000, 1, .8, 200, 300)
        self.assertAlmostEqual(sum(x[k] for k in ('motor_controller_loss_w','dump_w','battery_w','mechanical_w')),1000)
    def test_resistors(self):
        x=resistor_bank(60)
        self.assertAlmostEqual(x['series_w'], 3600/9.4)
        self.assertAlmostEqual(x['parallel_w'],3600/2.35)
        self.assertAlmostEqual(x['series_max_w'],3600/(9.4*.95))
    def test_cooling_and_step(self):
        self.assertAlmostEqual(thermal_step(40,40,100,.3,900,1e6),70)
        self.assertLess(thermal_step(100,40,0,.3,900,60),100)
        self.assertGreater(thermal_step(40,40,100,.3,900,60),40)
    def test_invalid_inputs(self):
        for args in [(0,.1,20,100),(150,0,20,100),(150,.1,0,100)]:
            with self.assertRaises(ValueError): descent(*args)
        with self.assertRaises(ValueError): split(1000,1.1,.8,0,300)
        with self.assertRaises(ValueError): thermal_step(40,40,100,0,900,60)

if __name__=='__main__': unittest.main()
