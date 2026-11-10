"""Independent exact-package FSR contract; executable mutation controls, not qualification."""
import unittest
from test_mcu_connectivity import exported


def validate(parts,nets):
    def pin(r,p,n):
        if nets.get((r,str(p))) != n: raise ValueError(f'{r}.{p}: expected {n}')
    def element(k,a,b,v):
        if not any(r.startswith(k) and value==v and {nets.get((r,'1')),nets.get((r,'2'))}=={a,b} for r,value in parts.items()):
            raise ValueError(f'missing {v}: {a}/{b}')
    if any(n.startswith(('LEFT_HALL','RIGHT_HALL','BRAKE_LEFT_3V3','BRAKE_RIGHT_3V3')) for n in nets.values()):
        raise ValueError('obsolete rider Hall path remains')
    if sum(v=='100k enable default off' and {nets.get((r,'1')),nets.get((r,'2'))}=={'FSR_SAMPLE_ENABLE','PGND'} for r,v in parts.items()) != 2: raise ValueError('missing per-mux enable pulldown')
    pin('U17',4,'FSR_SAMPLE_ENABLE')
    for j,side in enumerate(['LEFT','RIGHT']):
        n=lambda suffix: side+'_FSR_'+suffix
        op,sw='U'+str(26+2*j),'U'+str(27+2*j)
        if parts.get(op)!='OPA333AIDBVR' or parts.get(sw)!='TMUX1511PWR': raise ValueError('wrong exact package')
        for p,net in {1:n('BUF'),2:'PGND',3:n('OP_IN'),4:n('BUF'),5:'MCU_VREF'}.items():pin(op,p,net)
        for p,net in {1:'FSR_SAMPLE_ENABLE',2:n('BUF'),3:n('ISO_OUT'),4:'PGND',7:'PGND',10:'PGND',13:'PGND',14:'LOGIC3V3_EXT'}.items():pin(sw,p,net)
        for p in [5,6,8,9,11,12]:
            if not nets.get((sw,str(p)),'').startswith('unconnected-('+sw+'-'):raise ValueError('unused mux signal must be NC')
        pin('U17',18 if j==0 else 25,n('ADC'))
        for p,net in {1:n('EXC_CABLE'),2:n('RETURN_CABLE')}.items():pin('J'+str(46+j),p,net)
        for k,a,b,v in [('R','MCU_VREF',n('EXC_CABLE'),'10k 1% FSR excitation'),('R',n('RETURN_CABLE'),n('SENSE'),'1k 1% FSR return'),('R',n('SENSE'),'PGND','10k 0.1% FSR measure'),('C',n('SENSE'),'PGND','100n FSR sense'),('R',n('SENSE'),n('OP_IN'),'10k 1% OPA input limit'),('R',n('ISO_OUT'),n('ADC'),'1k 1% ADC isolation'),('R',n('ADC'),'PGND','10k 1% ADC bleed'),('C',n('ADC'),'PGND','100n ADC reservoir'),('C','MCU_VREF','PGND','100n OPA bypass'),('C','LOGIC3V3_EXT','PGND','100n mux bypass'),('R','FSR_SAMPLE_ENABLE','PGND','100k enable default off')]:element(k,a,b,v)
        for i,leg in enumerate(['EXC_CABLE','RETURN_CABLE']):
            d='D'+str(38+j*3+i)
            if parts.get(d)!='PESD3V3U1UL CANDIDATE':raise ValueError('missing candidate TVS')
            pin(d,1,n(leg));pin(d,2,'PGND')
        for p,net in {1:'PGND',2:'MCU_VREF',3:n('SENSE')}.items():pin('D'+str(40+j*3),p,net)
        for p,net in {1:'PGND',2:side+'_SWITCH_EXT'}.items():pin('J'+str(44+j),p,net)


class FSRTopology(unittest.TestCase):
    def test_actual_export(self):validate(*exported())
    def test_every_fsr_endpoint_mutation(self):
        parts,nets=exported();validate(parts,nets)
        endpoints={e for e,n in nets.items() if '_FSR_' in n or n=='FSR_SAMPLE_ENABLE' or e[0] in ['U26','U27','U28','U29','D38','D39','D40','D41','D42','D43','J44','J45']}
        for e in endpoints:
            bad=dict(nets);bad[e]='BROKEN'
            with self.subTest(endpoint=e),self.assertRaises(ValueError):validate(parts,bad)
    def test_values_and_legacy_path(self):
        parts,nets=exported()
        for ref,v in parts.items():
            if 'FSR' in v and ref.startswith('R') or ref in ['U26','U27','U28','U29'] or 'ADC bleed' in v or 'OPA input limit' in v:
                bad=dict(parts);bad[ref]='WRONG'
                with self.subTest(part=ref),self.assertRaises(ValueError):validate(bad,nets)
        bad=dict(nets);bad['J999','1']='LEFT_HALL_ADC'
        with self.assertRaises(ValueError):validate(parts,bad)
