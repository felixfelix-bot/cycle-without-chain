"""Inhibited physical MAIN/PRE slice; no operational sequencer or CTRL supply.
TPSI3052 SLVSGS3B Table 5-1; IRFP4568PbF PD-96175 TO-247 G,D,S.
Dedicated 400-series refs avoid disturbing legacy generated passive numbering.
"""
from fsr_circuit import symbol

def populate(g):
    Sheet, stock = g['Sheet'],g['stock']
    driver=symbol(g,'TPSI3052DWZR',['EN','PXFR','VDDP','VSSP','VSSS','VDDM','VDDH','VDRV'],
                  ['input','input','power_in','power_in','power_in','power_out','power_out','output'])
    fet=stock('Transistor_FET','Q_NMOS_GDS')
    for k,branch in enumerate(('MAIN','PRE')):
        s=Sheet('entry-'+branch.lower(),branch+' back-to-back candidate - hardware inhibited')
        s.text('NO ENERGIZE: 0R EN inhibit fitted; sequencer and CTRL3V3 buck NOT IMPLEMENTED.',20.32,15.24)
        s.text('150V IRFP4568PbF G=1 D=2 S=3; SOA, clamp and thermal qualification remain OPEN.',20.32,22.86)
        def part(lib,ref,value,x,y,nets,fp=''):s.part(lib,ref,value,x,y,nets,fp)
        def rc(kind,num,value,x,y,a,b):part(stock('Device',kind),kind+str(num),value,x,y,{'1':a,'2':b})
        src=branch+'_SOURCE'; hi=branch+'_VDDH';mid=branch+'_VDDM';out=branch+'_VDRV'
        part(driver,'U'+str(400+k),'TPSI3052DWZR',63.5,76.2,
             dict(zip(map(str,range(1,9)),[branch+'_EN',branch+'_PXFR','CTRL3V3','PGND',src,mid,hi,out])))
        base=400+k*10
        rc('R',base,'20k 1% PXFR',165.1,55.88,branch+'_PXFR','PGND')
        rc('R',base+1,'10k EN default OFF',241.3,55.88,branch+'_EN','PGND')
        rc('R',base+2,'0R FIXED INHIBIT - no operational command source',330.2,55.88,branch+'_EN','PGND')
        rc('C',base,'1u 10V X7R effective >=0.22u',165.1,96.52,'CTRL3V3','PGND')
        rc('C',base+1,'100n 25V C0G 5% CDIV1',241.3,96.52,hi,mid)
        rc('C',base+2,'470n 25V C0G 5% CDIV2',330.2,96.52,mid,src)
        for j,drain in enumerate(('ENTRY_FUSED','BUS_SHUNT_HI' if branch=='MAIN' else 'PRECHARGE_R')):
            ref='Q'+str(400+k*2+j); gate=ref+'_GATE';x=88.9+j*177.8
            part(fet,ref,'IRFP4568PbF 150V candidate',x,167.64,{'1':gate,'2':drain,'3':src},'Package_TO_SOT_THT:TO-247-3_Vertical')
            rc('R',base+3+j*2,'10R 1% gate candidate',x-35.56,218.44,out,gate)
            rc('R',base+4+j*2,'100k 1% G-S default OFF',x+40.64,218.44,gate,src)
        s.text('Common-source node floats: NEVER PGND. CDIV2/CDIV1 worst 470*.95/(100*1.05)=4.25 > 3.',20.32,248.92)
        s.text('EN not gate feedback. No MAIN_PROVEN, timeout, PM-quiet or current detector claimed.',20.32,259.08)
        s.save();g['sheets'].append(s)
