"""Independent fixed-pin OC contract against actual KiCad export."""
import copy
import unittest
from test_mcu_connectivity import exported


def validate(parts, nets):
    def pin(r,p,n):
        if nets.get((r,str(p))) != n:
            raise ValueError(f'{r}.{p}: expected {n}')
    def element(a,b,v):
        if not any(r.startswith('R') and value.startswith(v) and {nets.get((r,'1')),nets.get((r,'2'))} == {a,b} for r,value in parts.items()):
            raise ValueError(f'missing {v} resistor {a}/{b}')
    for i,source in enumerate(f'{b}_SO{p}' for b in ['GEN','HUB'] for p in 'ABC'):
        r=f'U{18+i}'
        if parts.get(r) != 'TLV3202IDR': raise ValueError(f'missing {r} TLV3202')
        for p,n in {1:source+'_LO',2:source,3:'OC_LOW_REF',4:'PGND',5:source,6:'OC_HIGH_REF',7:source+'_HI',8:'LOGIC3V3_EXT'}.items():pin(r,p,n)
        element(source,'PGND','100k')
        for k,suffix in enumerate(['LO','HI']):
            q=f'Q{14+i*2+k}'
            if parts.get(q) != '2N7002':raise ValueError(f'missing sink {q}')
            for p,n in {1:source+'_'+suffix,2:'PGND',3:'OC_OK'}.items():pin(q,p,n)
            element(source+'_'+suffix,'PGND','100k')
    for a,b,v in [('LOGIC3V3_EXT','OC_LOW_REF','28k7'),('OC_LOW_REF','PGND','10k'),('LOGIC3V3_EXT','OC_HIGH_REF','10k'),('OC_HIGH_REF','PGND','28k7'),('SAFETY3V3','OC_OK','4k7')]:element(a,b,v)
    for r,p,n in [('U14',6,'OC_OK'),('U14',4,'HEALTHY'),('U7',6,'HEALTHY'),('U8',6,'HEALTHY'),('U16',1,'HEALTHY'),('U16',3,'PERMIT'),('U16',4,'TIMER_BREAK_OK'),('U17',46,'TIMER_BREAK_OK'),('U17',84,'TIMER_BREAK_OK')]:pin(r,p,n)
    for b in ['GEN','HUB']:element('TIMER_BREAK_OK',b+'_ENABLE','1k')

class FastOC(unittest.TestCase):
    def test_actual_topology(self):validate(*exported())
    def test_corrupted_paths_rejected(self):
        parts,nets=exported();validate(parts,nets)
        for endpoint in [('U18','2'),('U23','5'),('Q14','3'),('Q25','1'),('U14','6'),('U8','6'),('U17','46'),('U17','84')]:
            broken=copy.copy(nets);broken[endpoint]='BROKEN'
            with self.assertRaises(ValueError):validate(parts,broken)
