import unittest, math
from test_mcu_connectivity import exported

class EntryCircuit(unittest.TestCase):
    def test_fused_precharge_and_measurement(self):
        parts,nets=exported()
        self.assertIn('F1',parts)
        self.assertIn('J43',parts)
        for endpoint, net in {('F1','1'):'SOURCE_POS',('F1','2'):'ENTRY_FUSED',('Q400','2'):'ENTRY_FUSED',('Q401','2'):'BUS_SHUNT_HI',('Q403','2'):'PRECHARGE_R',('D20','1'):'DC_LINK',('D20','2'):'PGND',('J43','1'):'BUS_SHUNT_HI',('J43','2'):'DC_LINK',('J43','4'):'PGND'}.items():
            self.assertEqual(nets[endpoint],net)
        for prefix,a,b in [('22R 1% RH050','PRECHARGE_R','BUS_SHUNT_HI'),('2m 1% WSLP','BUS_SHUNT_HI','DC_LINK'),('10k 1% RH025','DC_LINK','PGND')]:
            self.assertTrue(any(v.startswith(prefix) and {nets.get((r,'1')),nets.get((r,'2'))}=={a,b} for r,v in parts.items()))
    def test_energy_bounds(self):
        # Conservative explicit capacitance budget, not nominal capacitor sum.
        c=0.0015; v=58.4; r=21.78; rb=10000
        self.assertAlmostEqual(c*v*v/2,2.55792)
        self.assertLess(v/r,2.7)
        self.assertLess(v*v/r,157)
        self.assertLess(v*v/r*.350,54.807)
        self.assertLess(-r*c*math.log(1/58.4),0.62)
        self.assertLess(rb*c*math.log(v/5),37)
