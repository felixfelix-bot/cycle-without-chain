"""Single pack-side CTRL3V3 buck; source and qualification ledger in milestone.
LM5164 SNVSAU4D table 4-1, equations 13-26. No sequencer/interlock added.
"""
from fsr_circuit import symbol


def populate(g):
    stock = g['stock']
    s = g['Sheet']('ctrl-supply', 'CTRL3V3 pack-side buck - unqualified, enables inhibited')
    s.text('36-58.4V pack -> ENTRY_FUSED -> D500 -> CTRL_RAW. Upstream MAIN; no bus dependency.',20.32,15.24)
    s.text('TI LM5164 SNVSAU4D adapted Type-3 network. 0.8W PACK INPUT acceptance cap, NOT output rating.',20.32,22.86)
    s.text('NOT SAFE TO ENERGIZE. No PGOOD interlock or whole-system reverse/OV protection claimed.',20.32,30.48)
    buck = symbol(g,'LM5164DDAR',['GND','VIN','EN_UVLO','RON','FB','PGOOD','BST','SW','EP'],
                  ['power_in','power_in','input','input','input','open_collector','passive','power_out','passive'])
    s.part(buck,'U500','LM5164DDAR',76.2,101.6,
           dict(zip(map(str,range(1,10)),['PGND','CTRL_RAW','CTRL_UVLO','CTRL_RON','CTRL_FB',None,'CTRL_BST','CTRL_SW','PGND'])))
    s.part(stock('Device','D'),'D500','S1J-E3/61T 600V 1A',76.2,53.34,
           {'1':'CTRL_RAW','2':'ENTRY_FUSED'},'Diode_SMD:D_SMA')
    s.part(stock('Device','L'),'L500','68u MSS1246T-683MLC 20%',76.2,154.94,
           {'1':'CTRL_SW','2':'CTRL3V3'})
    specs = [
        ('C500','2.2u 100V CGA6N3X7R2A225K230AB','CTRL_RAW','PGND'),
        ('C501','2.2u 100V CGA6N3X7R2A225K230AB','CTRL_RAW','PGND'),
        ('C502','2.2n 50V GCM155R71H222KA37D','CTRL_BST','CTRL_SW'),
        ('C503','22u 25V TMK325B7226KMHT','CTRL3V3','PGND'),
        ('C504','22u 25V TMK325B7226KMHT','CTRL3V3','PGND'),
        ('C505','3.3n 100V CGA3E2X7R2A332K080AA','CTRL_RAMP','CTRL3V3'),
        ('C506','330p 50V C0G 5% candidate','CTRL_RAMP','CTRL_FB'),
        ('R500','27.4k 1% 0.1W candidate','CTRL_RON','PGND'),
        ('R501','87.3k 1% 0.1W candidate','CTRL3V3','CTRL_FB'),
        ('R502','49.9k 1% RG1608P-4992-B-T5','CTRL_FB','PGND'),
        ('R503','150k 1% 0.1W >=100V candidate','CTRL_SW','CTRL_RAMP'),
        ('R504','1M 1% 0.1W >=100V candidate','CTRL_RAW','CTRL_UVLO'),
        ('R505','52.3k 1% 0.1W candidate','CTRL_UVLO','PGND'),
    ]
    for i,(ref,value,a,b) in enumerate(specs):
        s.part(stock('Device',ref[0]),ref,value,157.48+(i%3)*83.82,53.34+(i//3)*40.64,{'1':a,'2':b})
    s.text('PGOOD explicitly NC: no supply-valid / gate authority claimed. U400/U401 EN 0R inhibits remain fitted.',20.32,248.92)
    s.text('100V input ceramics: bias / surge / damping OPEN; exact footprint and thermal layout not qualified.',20.32,259.08)
    s.text('D500 protects this positive supply branch only; no full-system reverse-polarity or transient proof.',20.32,269.24)
    s.save()
    g['sheets'].append(s)
