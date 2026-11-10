"""Independent native-export contract; no generator import or assert statements."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def validate(root):
    n = {(x.attrib['ref'], x.attrib['pin']): net.attrib['name']
         for net in root.findall('./nets/net') for x in net.findall('node')}
    v = {c.attrib['ref']: c.findtext('value') for c in root.findall('./components/comp')}
    expected = {
        'U500': ['PGND','CTRL_RAW','CTRL_UVLO','CTRL_RON','CTRL_FB',None,'CTRL_BST','CTRL_SW','PGND'],
        'D500': ['CTRL_RAW','ENTRY_FUSED'], 'L500': ['CTRL_SW','CTRL3V3'],
        'C500': ['CTRL_RAW','PGND'], 'C501': ['CTRL_RAW','PGND'],
        'C502': ['CTRL_BST','CTRL_SW'], 'C503': ['CTRL3V3','PGND'],
        'C504': ['CTRL3V3','PGND'], 'C505': ['CTRL_RAMP','CTRL3V3'],
        'C506': ['CTRL_RAMP','CTRL_FB'],
        'R500': ['CTRL_RON','PGND'], 'R501': ['CTRL3V3','CTRL_FB'],
        'R502': ['CTRL_FB','PGND'], 'R503': ['CTRL_SW','CTRL_RAMP'],
        'R504': ['CTRL_RAW','CTRL_UVLO'], 'R505': ['CTRL_UVLO','PGND'],
        'R402': ['MAIN_EN','PGND'], 'R412': ['PRE_EN','PGND'],
        'U400': ['MAIN_EN','MAIN_PXFR','CTRL3V3','PGND','MAIN_SOURCE','MAIN_VDDM','MAIN_VDDH','MAIN_VDRV'],
        'U401': ['PRE_EN','PRE_PXFR','CTRL3V3','PGND','PRE_SOURCE','PRE_VDDM','PRE_VDDH','PRE_VDRV'],
    }
    for ref, nets in expected.items():
        for i, net in enumerate(nets,1):
            if net is not None and n.get((ref,str(i))) != net:
                raise ValueError(f'{ref}.{i}: expected {net}, got {n.get((ref,str(i)))}')
    for ref, prefix in {'U500':'LM5164DDAR','D500':'S1J-E3/61T','L500':'68u MSS1246T-683ML',
                        'C502':'2.2n 50V','C505':'3.3n','C506':'330p','R500':'27.4k',
                        'R501':'87.3k','R502':'49.9k','R503':'150k','R504':'1M','R505':'52.3k',
                        'R402':'0R','R412':'0R'}.items():
        if not v.get(ref,'').startswith(prefix): raise ValueError(f'{ref}: wrong/missing value')
    if sum(value.startswith('LM5164') for value in v.values()) != 1:
        raise ValueError('exactly one LM5164 in this milestone')
    return n

class CtrlSupplyTests(unittest.TestCase):
    def load(self): return ET.parse(ROOT/'exports/ctrl-supply.xml').getroot()
    def test_native_endpoints_and_values(self): validate(self.load())
    def test_corrupted_pin_rejected(self):
        root=self.load()
        for node in root.findall('./nets/net/node'):
            if node.attrib['ref']=='U500' and node.attrib['pin']=='2': node.attrib['pin']='99'
        with self.assertRaises(ValueError): validate(root)
    def test_empty_export_rejected(self):
        with self.assertRaises(ValueError): validate(ET.fromstring('<export/>'))
    def test_arithmetic_not_qualification(self):
        v=1.2*(1+87.3/49.9); f=v*2500/27.4*1000
        self.assertAlmostEqual(v,3.2994,places=3)
        self.assertGreater(v/58.4/f,50e-9)
        self.assertGreater(v/f*(1-v/34.9)/(150e3*3.3e-9),.012)
        self.assertLess(1.55*(1+1e6*1.01/(52.3e3*.99)),34.9)
        self.assertLess(.362/.60+.10,.8)

if __name__=='__main__': unittest.main()
