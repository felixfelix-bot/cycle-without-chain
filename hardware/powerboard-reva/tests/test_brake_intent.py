"""Independent brake interface endpoint contract; not safety qualification."""
import unittest
from test_mcu_connectivity import exported

def validate(parts,nets):
    def pin(r,p,n):
        if nets.get((r,str(p))) != n: raise ValueError(f'{r}.{p} expected {n}')
    def element(kind,a,b,prefix):
        if not any(r.startswith(kind) and v.startswith(prefix) and {nets.get((r,'1')),nets.get((r,'2'))}=={a,b} for r,v in parts.items()):
            raise ValueError(f'missing {prefix} {a}/{b}')
    pin('U6',11,'FAULT_CHAIN'); pin('J5',2,'FAULT_CHAIN')
    pin('U14',3,'WD_OK'); pin('U14',6,'OC_OK'); pin('U16',1,'HEALTHY')
    for p,n in {18:'LEFT_HALL_ADC',25:'RIGHT_HALL_ADC',26:'LEFT_SWITCH_ADC',34:'RIGHT_SWITCH_ADC'}.items(): pin('U17',p,n)
    for i,n in enumerate(['LEFT_HALL','RIGHT_HALL','LEFT_SWITCH','RIGHT_SWITCH']):
        element('R',n+'_EXT',n+'_ADC','10k')
        element('C',n+'_ADC','PGND','10n')
        pin('D'+str(30+i),1,n+'_EXT');pin('D'+str(30+i),2,'PGND')
        for p,net in [(1,'PGND'),(2,'LOGIC3V3_EXT'),(3,n+'_ADC')]:pin('D'+str(34+i),p,net)
        element('R',n+'_EXT','LOGIC3V3_EXT' if 'SWITCH' in n else 'PGND','10k' if 'SWITCH' in n else '100k')
    pin('U24',1,'OV_CMD');pin('U24',2,'BRAKE_DUMP_PERMITTED');pin('U25',1,'BRAKE_DUMP_PWM');pin('U25',2,'TIMER_BREAK_OK');pin('U25',4,'BRAKE_DUMP_PERMITTED');pin('U24',4,'CHOP_CMD');pin('U10',6,'CHOP_CMD')
    pin('U17',50,'BRAKE_DUMP_PWM')
    if 'BRAKE_LOOP' in nets.values():raise ValueError('legacy normal-brake gate kill remains')

class BrakeTopology(unittest.TestCase):
    def test_export(self):validate(*exported())
    def test_mutations(self):
        parts,nets=exported();validate(parts,nets)
        for e in [('U6','11'),('U14','3'),('U14','6'),('U17','18'),('D34','1'),('D34','2'),('D30','2'),('U10','6')]:
            bad=dict(nets);bad[e]='BROKEN'
            with self.subTest(endpoint=e),self.assertRaises(ValueError):validate(parts,bad)
