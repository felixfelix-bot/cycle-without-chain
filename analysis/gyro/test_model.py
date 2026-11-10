import math
import unittest
from model import gravity_torque, omega, momentum, reserve, ideal_roll_impulse, spinup_seconds


class GyroTests(unittest.TestCase):
    def test_gravity_limits_and_sign(self):
        self.assertEqual(gravity_torque(150,1,0),0)
        self.assertAlmostEqual(gravity_torque(150,1,90),150*9.80665)
        self.assertAlmostEqual(gravity_torque(140,.8,-5),-gravity_torque(140,.8,5))

    def test_energy_momentum_independent_inertia_identity(self):
        inertia, w = .002, omega(60000)
        self.assertAlmostEqual(momentum(.5*inertia*w*w,60000),inertia*w)
        self.assertAlmostEqual(w,2000*math.pi)

    def test_previous_example(self):
        energy=.5*150*(25/3.6)**2
        self.assertAlmostEqual(energy,3616.898148148148)
        self.assertAlmostEqual(momentum(energy,60000),1.151294438454827,places=6)

    def test_reserve_conservation_and_scaling(self):
        full,stored,hmax,hmin=reserve(3600,60000,48000)
        self.assertAlmostEqual(full-stored,3600)
        self.assertAlmostEqual(full,10000)
        self.assertAlmostEqual(stored/full,.8**2)
        self.assertAlmostEqual(hmin/hmax,.8)

    def test_reserve_diverges_near_max(self):
        self.assertGreater(reserve(3600,60000,59999)[0],1e7)

    def test_travel_bound(self):
        self.assertAlmostEqual(ideal_roll_impulse(10,-90,90),20)
        self.assertLess(ideal_roll_impulse(10,-45,45),20)
        self.assertAlmostEqual(ideal_roll_impulse(10,0,90),10)

    def test_spinup(self):
        self.assertEqual(spinup_seconds(10000,100),100)
        self.assertEqual(spinup_seconds(10000,100,.5),200)

    def test_invalid_inputs(self):
        for args in ((3600,60000,60000),(3600,60000,0),(-1,60000,30000)):
            with self.assertRaises(ValueError): reserve(*args)
        with self.assertRaises(ValueError): omega(0)
        with self.assertRaises(ValueError): momentum(-1,60000)
        with self.assertRaises(ValueError): spinup_seconds(100,0)


if __name__ == '__main__': unittest.main()
