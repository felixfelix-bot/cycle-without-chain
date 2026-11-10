"""Independent native XML rail contract; optimized Python retains checks."""
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
P=Path(__file__).resolve().parents[1]
def validate(root):
    n={(x.get('ref'),x.get('pin')):net.get('name') for net in root.findall('./nets/net') for x in net.findall('node')}
    expected={'U3':['DC_LINK','PGND','SINK12'],'U501':['PGND','DC_LINK','DRIVE_UVLO','DRIVE_RON','DRIVE_FB','ANALOG_OK','DRIVE_BST','DRIVE_SW','PGND'], 'U502':['LOGIC3V3_EXT','MCU3V3_EN','DRIVE12','PGND','MCU_SW','MCU_BST'],'L501':['DRIVE_SW','DRIVE12'],'L502':['MCU_SW','LOGIC3V3_EXT'],'R519':['MAIN_PROVEN_IN','PGND'],'R402':['MAIN_EN','PGND'],'R412':['PRE_EN','PGND']}
    for ref,nets in expected.items():
        for i,net in enumerate(nets,1):
            if n.get((ref,str(i)))!=net: raise ValueError(f'{ref}.{i} expected {net}')
    for ref,pin,net in [('U1','3','DRIVE12'),('U2','3','DRIVE12'),('U4','2','SINK12'),('U6','3','SINK12'),('U10','1','SINK12'),('U500','6','CTRL_PG'),('U510','1','CTRL_PG'),('U510','2','MAIN_PROVEN_IN')]:
        if n.get((ref,pin))!=net: raise ValueError(f'{ref}.{pin} expected {net}')
    return n
class RailTests(unittest.TestCase):
    def test_native(self): validate(ET.parse(P/'exports/ctrl-supply.xml').getroot())
    def test_empty_rejected(self):
        with self.assertRaises(ValueError): validate(ET.fromstring('<export/>'))
    def test_corrupt_rejected(self):
        root=ET.parse(P/'exports/ctrl-supply.xml').getroot()
        for node in root.findall('./nets/net/node'):
            if node.get('ref')=='U3' and node.get('pin')=='3': node.set('pin','99')
        with self.assertRaises(ValueError): validate(root)
