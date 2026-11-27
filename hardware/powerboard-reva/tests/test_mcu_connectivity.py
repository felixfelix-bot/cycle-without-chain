"""Fixed physical-pin contracts against KiCad's actual exported netlist, not CSV."""
from pathlib import Path
import copy
import unittest
from verify_exports import parse, child, children, value

ROOT = Path(__file__).resolve().parents[1]
PWM = {39:'GEN_INLA',40:'GEN_INHA',41:'GEN_INLB',42:'GEN_INHB',43:'GEN_INLC',44:'GEN_INHC',65:'HUB_INHA',66:'HUB_INHB',67:'HUB_INHC',29:'HUB_INLA',32:'HUB_INLB',33:'HUB_INLC'}
ADC = {20:'GEN_SOA',21:'GEN_SOB',22:'GEN_SOC',15:'HUB_SOA',16:'HUB_SOB',17:'HUB_SOC'}

def exported():
    tree = parse((ROOT/'exports/powerboard-reva.net').read_text())
    parts = {value(c,'ref'):value(c,'value') for c in children(child(tree,'components'),'comp')}
    nets = {}
    for net in children(child(tree,'nets'),'net'):
        for node in children(net,'node'):
            nets[value(node,'ref'),value(node,'pin')] = value(net,'name').lstrip('/')
    return parts,nets

def validate(parts,nets):
    def pin(ref,p,n):
        if nets.get((ref,str(p))) != n:
            raise ValueError(f'{ref}.{p}: expected {n}, got {nets.get((ref,str(p)))}')
    def element(kind,a,b,prefix):
        hits = [r for r,v in parts.items() if r.startswith(kind) and v.startswith(prefix) and {nets.get((r,'1')),nets.get((r,'2'))} == {a,b}]
        if not hits: raise ValueError(f'missing {prefix} {kind}: {a} -- {b}')
    if parts.get('U17') != 'STM32G474VET6': raise ValueError('missing real STM32G474VET6')
    for p,n in PWM.items(): pin('U17',p,n)
    for p in [46,84]: pin('U17',p,'TIMER_BREAK_OK')
    pin('U16',4,'TIMER_BREAK_OK')
    for ref,pre in [('U1','GEN'),('U2','HUB')]:
        for p,n in [(32,'INHA'),(33,'INLA'),(34,'INHB'),(35,'INLB'),(36,'INHC'),(37,'INLC'),(31,'ENABLE')]:pin(ref,p,pre+'_'+n)
        for p,n in [(29,'DRV_SCK'),(28,'DRV_MOSI'),(27,'DRV_MISO')]:pin(ref,p,n)
        element('R','TIMER_BREAK_OK',pre+'_ENABLE','1k')
    for p,n in {27:'DRV_SCK',28:'DRV_MISO',92:'DRV_MOSI',62:'GEN_nSCS',45:'HUB_nSCS',1:'MCU_ARM',2:'WDI',3:'RESET_REQUEST',61:'FAULT_CHAIN_SENSE',14:'MCU_NRST',95:'MCU_BOOT0',76:'SWDIO',77:'SWCLK',93:'ENC_A',94:'ENC_B'}.items():pin('U17',p,n)
    for p in [24,49,64,75,100,6]:pin('U17',p,'LOGIC3V3_EXT')
    for p in [23,48,63,74,99,35]:pin('U17',p,'PGND')
    for p,n in [(37,'MCU_VDDA'),(36,'MCU_VREF')]:
        pin('U17',p,n);element('R','LOGIC3V3_EXT',n,'0R');element('C',n,'PGND','100n');element('C',n,'PGND','1u')
    decaps=[r for r,v in parts.items() if r.startswith('C') and v.startswith('100n') and {nets.get((r,'1')),nets.get((r,'2'))}=={'LOGIC3V3_EXT','PGND'}]
    if len(decaps)<6:raise ValueError('missing VDD/VBAT decoupling')
    for p,source in ADC.items():
        target=source+'_ADC';pin('U17',p,target);element('R',source,target,'100R');element('C',target,'PGND','1n')
    for p,pre,i in [(55,'GEN',1),(56,'GEN',2),(57,'GEN',3),(58,'HUB',1),(59,'HUB',2),(60,'HUB',3)]:
        n=f'{pre}_HALL_{i}';pin('U17',p,n);element('R',n+'_EXT',n,'1k');element('R',n+'_EXT','LOGIC3V3_EXT','10k');element('C',n,'PGND','1n')
    for n in ['ENC_A','ENC_B']:
        element('R',n+'_EXT',n,'1k');element('R',n+'_EXT','LOGIC3V3_EXT','10k');element('C',n,'PGND','1n')
    unused = {4,5,7,8,9,10,11,12,13,19,30,31,38,47,51,52,53,54,68,69,70,71,72,73,78,79,80,81,82,83,85,86,87,88,89,90,91,96,97,98}
    for p in unused:
        if not nets.get(('U17',str(p)),'').startswith('unconnected-(U17-'):
            raise ValueError(f'unused MCU pin {p} must be explicit NC')
    for n in ['MCU_ARM','RESET_REQUEST','WDI','MCU_BOOT0']:element('R',n,'PGND','1' if n=='WDI' else '10k')
    element('R','FAULT_CHAIN','FAULT_CHAIN_SENSE','10k');element('R','FAULT_CHAIN_SENSE','PGND','100k')
    element('R','MCU_NRST','LOGIC3V3_EXT','10k');element('C','MCU_NRST','PGND','100n')
    if any('_PWM_EXT' in v or '_SPI_EXT' in v or '_ADC_EXT' in v or v=='SAFETY_CONTROL' for v in parts.values()):raise ValueError('placeholder control connector remains')

class MCUConnectivity(unittest.TestCase):
    def test_exported_topology(self):validate(*exported())
    def test_mutations_rejected(self):
        parts,nets=exported()
        validate(parts,nets)
        for endpoint in [('U17','40'),('U17','46'),('U17','84'),('U17','20'),('U17','55'),('U17','24'),('U1','29')]:
            with self.subTest(endpoint=endpoint):
                broken=copy.copy(nets);broken[endpoint]='BROKEN'
                with self.assertRaises(ValueError):validate(parts,broken)
        for source in ADC.values():
            broken=copy.copy(nets)
            for r,v in parts.items():
                if r.startswith('C') and broken.get((r,'1'))==source+'_ADC':broken[r,'2']='BROKEN'
            with self.assertRaises(ValueError):validate(parts,broken)
