"""Independent native XML endpoints, not generator manifest agreement.
Does not establish SOA, supply startup, sequencing or protection qualification.
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ActiveEntryTests(unittest.TestCase):
    def setUp(self):
        p=ROOT/'exports/active-entry.xml'
        self.assertTrue(p.exists(), 'native active-entry export required')
        root=ET.parse(p).getroot()
        self.n={(x.attrib['ref'],x.attrib['pin']):n.attrib['name'] for n in root.findall('./nets/net') for x in n.findall('node')}
        self.v={c.attrib['ref']:c.findtext('value') for c in root.findall('./components/comp')}
    def test_no_passive_bypass(self):
        self.assertNotIn('J41',self.v)
        self.assertNotIn('J42',self.v)
        self.assertIn('22R',self.v['R116'])
    def test_common_source_pairs_and_driver_pins(self):
        for branch,a,b,u,drain in [('MAIN','Q400','Q401','U400','BUS_SHUNT_HI'),('PRE','Q402','Q403','U401','PRECHARGE_R')]:
            expected={(a,'2'):'ENTRY_FUSED',(b,'2'):drain,(a,'3'):branch+'_SOURCE',(b,'3'):branch+'_SOURCE',
                      (u,'1'):branch+'_EN',(u,'2'):branch+'_PXFR',(u,'3'):'CTRL3V3',(u,'4'):'PGND',
                      (u,'5'):branch+'_SOURCE',(u,'6'):branch+'_VDDM',(u,'7'):branch+'_VDDH',(u,'8'):branch+'_VDRV'}
            for key,net in expected.items(): self.assertEqual(self.n[key],net,key)
            for q in (a,b): self.assertEqual(self.n[q,'1'],q+'_GATE')
    def test_fixed_hardware_inhibit_and_split_caps(self):
        for k,branch in enumerate(('MAIN','PRE')):
            for ref,a,b in [(f'R{402+k*10}',branch+'_EN','PGND'),(f'C{401+k*10}',branch+'_VDDH',branch+'_VDDM'),(f'C{402+k*10}',branch+'_VDDM',branch+'_SOURCE')]:
                self.assertEqual(self.n[ref,'1'],a);self.assertEqual(self.n[ref,'2'],b)
            self.assertTrue(self.v[f'R{402+k*10}'].startswith('0R'))
