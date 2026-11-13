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
          'U503':['REF2V5','PGND','DRIVE_OV_SENSE','DRIVE_OV_TRIP','SINK12'],
          # RAIL-16 latch: CLK=DRIVE_EN, D tied low, Q_N loaded, Q gates the buck,
          # CLR_N is the wired-OR fault node, PRE_N tied high, VCC from SAFETY3V3.
          'U504':['DRIVE_EN','DRIVE_LATCH_D','DRIVE_NQ','PGND','DRIVE_EN_GATED',
                  'DRIVE_FAULT','SAFETY3V3','SAFETY3V3'],
          # RAIL-19: DRIVE_PG finally has a consumer.
          'U505':['DRIVE_EN_GATED','DRIVE_PG','PGND','DRIVE_FAULT','SAFETY3V3'],
          'L501':['DRIVE_SW','DRIVE12'],'L502':['MCU_SW','LOGIC3V3_EXT'],
          'R519':['MAIN_PROVEN_IN','PGND'],'R402':['MAIN_EN','PGND'],'R412':['PRE_EN','PGND'],
          'R521':['SINK12','DRIVE_PG'],'R523':['DRIVE12','DRIVE_OV_SENSE'],
          'R524':['DRIVE_OV_SENSE','PGND'],'C523':['DRIVE_OV_SENSE','PGND'],
          'R514':['DRIVE_EN_GATED','DRIVE_UVLO'],
          'R525':['DRIVE_LATCH_D','PGND'],'R526':['SAFETY3V3','DRIVE_FAULT'],
          'D520':['DRIVE_OV_TRIP','DRIVE_FAULT'],'D521':['DRIVE_PG','DRIVE_FAULT'],
          'D522':['DRIVE_RESET_SW','DRIVE_FAULT'],'J48':['DRIVE_RESET_SW','PGND']}

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
    # L501 must be a part TDK still sells: the VT variant is NRND with
    # SPM10065VC-680M-D named as the replacement, and a new design must not
    # name a not-recommended part. Both share the same 2.95/6.10/4.50 land.
    if not any(v and 'SPM10065VC-680M-D' in v for v in values): raise ValueError('L501 not the production 68uH part')
    if any(v and 'VT-680M-D' in v for v in values): raise ValueError('L501 names the NRND VT variant')
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

    # --- RAIL-16 / RAIL-19: the DRIVE12 fault latch ------------------------
    # The OVP comparator used to pull DRIVE_UVLO directly. That is level
    # protection, not a latch: with a permanently open R512 the rail hiccups
    # between ~0 and 18 V forever instead of staying off. A D-flip-flop whose
    # clear input is held by the fault makes the trip persistent, and gives
    # DRIVE_PG (previously a pull-up with no consumer) a real function.

    def test_latch_exists_and_is_powered_from_the_always_on_rail(self):
        n = validate(load())
        # U504 is the fault latch. It must run from SAFETY3V3, never from
        # DRIVE12: a latch powered by the rail it is protecting loses state at
        # exactly the moment it is needed.
        vcc = [net for (ref, pin), net in n.items() if ref == 'U504' and pin == '8']
        if vcc != ['SAFETY3V3']:
            raise ValueError(f'latch VCC is {vcc}, not SAFETY3V3')
        gnd = [net for (ref, pin), net in n.items() if ref == 'U504' and pin == '4']
        if gnd != ['PGND']:
            raise ValueError(f'latch GND is {gnd}, not PGND')

    def test_latch_clear_is_driven_by_the_fault_not_by_the_rail(self):
        n = validate(load())
        clr = [net for (ref, pin), net in n.items() if ref == 'U504' and pin == '6']
        if clr != ['DRIVE_FAULT']:
            raise ValueError(f'latch CLR_N is {clr}, not the DRIVE_FAULT node')

    def test_ovp_no_longer_drives_drive_uvlo_directly(self):
        # The whole point: U503's output must reach the latch, not the buck.
        n = validate(load())
        out = [net for (ref, pin), net in n.items() if ref == 'U503' and pin == '4']
        if out != ['DRIVE_OV_TRIP']:
            raise ValueError(f'U503 output is {out}; it must be DRIVE_OV_TRIP, not DRIVE_UVLO')

    def test_latch_output_reaches_the_buck_enable(self):
        n = validate(load())
        q = [net for (ref, pin), net in n.items() if ref == 'U504' and pin == '5']
        if q != ['DRIVE_EN_GATED']:
            raise ValueError(f'latch Q is {q}, not DRIVE_EN_GATED')
        uvlo = [net for (ref, pin), net in n.items() if ref == 'U501' and pin == '3']
        if uvlo != ['DRIVE_UVLO']:
            raise ValueError(f'U501 EN/UVLO is {uvlo}')

    def test_drive_pg_has_a_consumer(self):
        # RAIL-19: a status net nothing reads is dead weight. PGOOD must gate
        # the AND that produces DRIVE_EN_GATED.
        n = validate(load())
        consumers = {ref for (ref, pin), net in n.items() if net == 'DRIVE_PG' and ref != 'R521'}
        if not consumers:
            raise ValueError('DRIVE_PG still has no consumer besides its own pull-up')

    def test_every_rail_part_has_a_footprint(self):
        """A part with no footprint cannot be ordered or placed.

        The latch added U504, U505, R525-R528, D520-D522 and J48. Four of the
        resistors were committed with an empty footprint field, and nothing
        failed: check_bom.py grades approved-mpns.json rather than the generated
        CSV, so a blank land pattern is invisible to it. This asserts on the BOM
        that actually gets ordered.
        """
        board = Path(__file__).resolve().parents[1]
        rows = [r for r in (board / "review-bom.csv").read_text(encoding="utf-8").splitlines() if r.strip()]
        rail = [r for r in rows if r.split(",")[-1].strip() in ("rail-partition", "rail-passives")]
        self.assertTrue(rail, "no rail-partition/rail-passives rows found in the BOM")
        blank = [r.split(",")[0] for r in rail if not r.split(",")[2].strip()]
        self.assertEqual(blank, [], f"rail parts with no footprint: {blank}")
