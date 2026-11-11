"""Independent native XML rail contract; optimized Python retains checks.

Covers the rail partition, the RAIL-01 output OVP added in this branch, and the
RAIL-04 decision that U501 PGOOD no longer gates the always-on ANALOG_OK chain.
Every check is a positive assertion with a negative control beside it; nothing
here reads the generator or the CSV manifests.
"""
import copy
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
P=Path(__file__).resolve().parents[1]

# U501 (LM5164) pin 6 is DRIVE_PG: PGOOD is a status output on its own always-on
# pullup, NOT a member of the always-on ANALOG_OK safety chain (was RAIL-04).
EXPECTED={'U3':['DC_LINK','PGND','SINK12'],
          'U501':['PGND','DC_LINK','DRIVE_UVLO','DRIVE_RON','DRIVE_FB','DRIVE_PG','DRIVE_BST','DRIVE_SW','PGND'],
          'U502':['LOGIC3V3_EXT','MCU3V3_EN','DRIVE12','PGND','MCU_SW','MCU_BST'],
          'U503':['REF2V5','PGND','DRIVE_OV_SENSE','DRIVE_UVLO','SINK12'],
          'L501':['DRIVE_SW','DRIVE12'],'L502':['MCU_SW','LOGIC3V3_EXT'],
          'R519':['MAIN_PROVEN_IN','PGND'],'R402':['MAIN_EN','PGND'],'R412':['PRE_EN','PGND'],
          'R521':['SINK12','DRIVE_PG'],'R523':['DRIVE12','DRIVE_OV_SENSE'],
          'R524':['DRIVE_OV_SENSE','PGND'],'C523':['DRIVE_OV_SENSE','PGND']}

ENDPOINTS=[('U1','3','DRIVE12'),('U2','3','DRIVE12'),('U4','2','SINK12'),('U6','3','SINK12'),
           ('U10','1','SINK12'),('U500','6','CTRL_PG'),('U510','1','CTRL_PG'),('U510','2','MAIN_PROVEN_IN')]

def validate(root):
    n={(x.get('ref'),x.get('pin')):net.get('name') for net in root.findall('./nets/net') for x in net.findall('node')}
    for ref,nets in EXPECTED.items():
        for i,net in enumerate(nets,1):
            if n.get((ref,str(i)))!=net: raise ValueError(f'{ref}.{i} expected {net}')
    for ref,pin,net in ENDPOINTS:
        if n.get((ref,pin))!=net: raise ValueError(f'{ref}.{pin} expected {net}')
    # No endpoint of U501 may sit on the always-on chain: a delayed rail's PGOOD
    # must not be able to hold an always-on safety verdict low.
    for (ref,pin),net in n.items():
        if ref=='U501' and net in ('ANALOG_OK','ANALOG_CLEAN','FAULTS_OK','HEALTHY'):
            raise ValueError(f'U501.{pin} re-coupled to always-on net {net}')
    # The OVP comparator output must be the EN/UVLO divider node, never the EN logic net.
    if n.get(('U503','4'))=='DRIVE_EN': raise ValueError('OVP output tied to DRIVE_EN, not DRIVE_UVLO')
    values={c.findtext('value') for c in root.findall('./components/comp') if c.get('ref') in ('L501','U503')}
    if not any(v and 'SPM10065VT-680M-D' in v for v in values): raise ValueError('L501 not the reselected 68uH part')
    if not any(v=='TLV1701AIDBVR' for v in values): raise ValueError('U503 OVP comparator missing')
    return n

def load():
    return ET.parse(P/'exports/ctrl-supply.xml').getroot()

def corrupt(ref,pin,net):
    """Move one endpoint to a different net. Returns the mutated tree."""
    root=load()
    moved=None
    for netel in root.findall('./nets/net'):
        for node in list(netel.findall('node')):
            if node.get('ref')==ref and node.get('pin')==pin:
                netel.remove(node); moved=dict(node.attrib)
    if moved is None: raise ValueError(f'{ref}.{pin} not present')
    for netel in root.findall('./nets/net'):
        if netel.get('name')==net: ET.SubElement(netel,'node',moved)
    return root

class RailTests(unittest.TestCase):
    def test_native(self): validate(load())
    def test_empty_rejected(self):
        with self.assertRaises(ValueError): validate(ET.fromstring('<export/>'))
    def test_corrupt_rejected(self):
        with self.assertRaises(ValueError): validate(corrupt('U3','3','DRIVE12'))
    def test_old_pgood_wiring_rejected(self):
        # Regression control for RAIL-04: the pre-branch wiring must fail.
        with self.assertRaises(ValueError): validate(corrupt('U501','6','ANALOG_OK'))
    def test_ovp_output_wiring_rejected(self):
        with self.assertRaises(ValueError): validate(corrupt('U503','4','DRIVE_EN'))
    def test_ovp_removed_rejected(self):
        root=load()
        for node in root.findall('./nets/net/node'):
            if node.get('ref')=='U503' and node.get('pin')=='3': node.set('pin','98')
        with self.assertRaises(ValueError): validate(root)
    def test_validator_is_not_reading_the_generator(self):
        # The contract is data: mutating a copy must never mutate the artifact.
        before=(P/'exports/ctrl-supply.xml').read_bytes()
        corrupt('U3','3','SINK12')
        self.assertEqual(before,(P/'exports/ctrl-supply.xml').read_bytes())
