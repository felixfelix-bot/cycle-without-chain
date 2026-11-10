#!/usr/bin/env python3
"""Deterministic KiCad 9 review schematic. No SKiDL netlist-only substitution.
Stock symbols are embedded, with inheritance resolved; DRV8353S from TI table.
"""
from pathlib import Path
import re, json, uuid, csv, hashlib
ROOT=Path(__file__).resolve().parent
LIB=Path('/usr/share/kicad/symbols')
G=1.27

def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'cycle-powerboard-reva/'+s))
def q(s): return json.dumps(str(s))
def parse(s):
    tok=re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]',s); stack=[]; out=[]
    for t in tok:
        if t=='(': stack.append([])
        elif t==')':
            x=stack.pop()
            if stack: stack[-1].append(x)
            else: out=x
        else: stack[-1].append(t)
    return out

def dump(a): return '('+' '.join(dump(x) if isinstance(x,list) else x for x in a)+')'
def val(s): return json.loads(s) if s.startswith('"') else s
def child(a,key): return next((x for x in a if isinstance(x,list) and x[0]==key),None)
cache={}
def stock(lib,name):
    if lib not in cache:
        cache[lib]={val(x[1]):x for x in parse((LIB/(lib+'.kicad_sym')).read_text()) if isinstance(x,list) and x[0]=='symbol'}
    import copy
    a=copy.deepcopy(cache[lib][name]); ext=child(a,'extends')
    if ext:
        base=stock(lib,val(ext[1]))
        a.remove(ext)
        for x in base:
            if isinstance(x,list) and x[0]=='symbol':
                x[1]=q(name+'_'+val(x[1]).rsplit('_',2)[1]+'_'+val(x[1]).rsplit('_',2)[2]); a.append(x)
            elif isinstance(x,list) and x[0] in ['pin_names','pin_numbers','in_bom','on_board','exclude_from_sim'] and child(a,x[0]) is None:
                a.append(x)
    a[1]=q(lib+':'+name)
    return a

def pins(a):
    result=[]
    for sub in a:
        if isinstance(sub,list) and sub[0]=='symbol':
            for p in sub:
                if isinstance(p,list) and p[0]=='pin':
                    at=child(p,'at'); result.append((val(child(p,'number')[1]),val(child(p,'name')[1]),float(at[1]),float(at[2]),int(at[3])))
    return result

names=['CPL','CPH','VM','VDRAIN','VCP','GHA','SHA','GLA','SPA','SNA','SNB','SPB','GLB','SHB','GHB','GHC','SHC','GLC','SPC','SNC','SOC','SOB','SOA','VREF','AGND','nFAULT','SDO','SDI','SCLK','nSCS','ENABLE','INHA','INLA','INHB','INLB','INHC','INLC','DVDD','GND','VGLS','EP']
def driver():
    s='(symbol "Powerboard:DRV8353S" (pin_names (offset 1.016)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 57.15 0) (effects (font (size 1.27 1.27)))) (property "Value" "DRV8353SRTAT" (at 0 54.61 0) (effects (font (size 1.27 1.27)))) (symbol "DRV8353S_0_1" (rectangle (start -20.32 52.07) (end 20.32 -55.88) (stroke (width 0.254) (type default)) (fill (type background)))) (symbol "DRV8353S_1_1"'
    for i,n in enumerate(names):
        left=i<21; row=i if left else i-21; x=-25.4 if left else 25.4; y=48.26-row*5.08
        typ='input'
        if n.startswith(('GH','GL','SO')): typ='output'
        if n in ['nFAULT','SDO']: typ='open_collector'
        if n in ['VM','VREF','AGND','GND','EP']:typ='power_in'
        if n in ['DVDD','VGLS','VCP']:typ='power_out'
        if n in ['CPH','CPL']:typ='passive'
        s+=f' (pin {typ} line (at {x} {y} {0 if left else 180}) (length 5.08) (name {q(n)} (effects (font (size 1.016 1.016)))) (number "{i+1}" (effects (font (size 1.016 1.016)))))'
    return parse(s+'))')

ROOTID=uid('root'); bom=[]; pinmap=[]
class Sheet:
    def __init__(self,name,title,root=False):
        self.name=name; self.id=ROOTID if root else uid(name); self.path='/'+ROOTID if root else '/'+ROOTID+'/'+uid('sheet/'+name); self.title=title;self.syms={};self.items=[]
    def text(self,text,x,y,size=1.524): self.items.append(f'(text {q(text)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid {uid(self.name+text)}))')
    def wirelabel(self,net,x,y,angle,tag):
        dx,dy={0:(-5.08,0),180:(5.08,0),90:(0,5.08),270:(0,-5.08)}[angle]
        xx,yy=round(x+dx,4),round(y+dy,4)
        self.items.append(f'(wire (pts (xy {x} {y}) (xy {xx} {yy})) (stroke (width 0) (type default)) (uuid {uid(tag+"wire")}))')
        # All labels global: explicit namespace GEN_/HUB_ prevents unintended merges.
        self.items.append(f'(global_label {q(net)} (shape bidirectional) (at {xx} {yy} {0 if dx<=0 else 180}) (effects (font (size 0.9 0.9)) (justify {"left" if dx<=0 else "right"})) (uuid {uid(tag+"label")}))')
    def part(self,a,ref,value,x,y,nets,footprint=''):
        libid=val(a[1]);self.syms[libid]=a
        props=f'(property "Reference" {q(ref)} (at {x} {y-5.08} 0) (effects (font (size 1.27 1.27)))) (property "Value" {q(value)} (at {x} {y-2.54} 0) (effects (font (size 1.016 1.016)))) (property "Footprint" {q(footprint)} (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))'
        self.items.append(f'(symbol (lib_id {q(libid)}) (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {uid(ref)}) {props} (instances (project "powerboard-reva" (path {q(self.path)} (reference {q(ref)}) (unit 1)))))')
        done={}
        for num,name,px,py,angle in pins(a):
            net=nets[num]; X=round(x+px,4);Y=round(y-py,4)
            if net is None:
                self.items.append(f'(no_connect (at {X} {Y}) (uuid {uid(ref+"/"+num+"/nc")}))')
                continue
            if (X,Y) in done: assert done[X,Y]==net
            else: self.wirelabel(net,X,Y,angle,ref+'/'+num);done[X,Y]=net
            pinmap.append(dict(ref=ref,pin=num,pin_name=name,net=net,sheet=self.name))
        bom.append(dict(reference=ref,value=value,footprint=footprint,sheet=self.name))
    def save(self):
        s=f'(kicad_sch (version 20250114) (generator "powerboard_generator") (uuid {self.id}) (paper {q("A1" if self.id==ROOTID else "A3")}) (title_block (title {q(self.title)}) (rev "A-PARTIAL") (comment 1 "NOT SAFE TO ENERGIZE - SAFETY CIRCUITS UNFINISHED")) (lib_symbols '+ ' '.join(dump(a) for a in self.syms.values())+') '+' '.join(self.items)
        if self.id==ROOTID:s+=' (sheet_instances (path "/" (page "1")))'
        (ROOT/(self.name+'.kicad_sch')).write_text(s+')\n')

R=stock('Device','R');C=stock('Device','C');FET=stock('Transistor_FET','CSD19532Q5B');DRV=driver()
local_drv=parse(dump(DRV)); local_drv[1]=q('DRV8353S')
(ROOT/'Powerboard.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "powerboard_generator") '+dump(local_drv)+')\n')
(ROOT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Powerboard") (type "KiCad") (uri "${KIPRJMOD}/Powerboard.kicad_sym") (options "") (descr "TI DRV8353S SPI driver; pin table SLVSDY6A pp6-7")))\n')
counters={'R':0,'C':0,'Q':0,'J':0}
def passive(s,kind,value,x,y,a,b,fp=''):
    counters[kind]+=1;ref=kind+str(counters[kind]);s.part(R if kind=='R' else C,ref,value,x,y,{'1':a,'2':b},fp);return ref

root=Sheet('powerboard-reva','Pedal-by-wire: hierarchical engineering review',True)
root.text('PARTIAL CIRCUIT MILESTONE - NOT A RELEASE DESIGN',25.4,25.4,2.54)
root.text('Global nets join sheets. GEN_ and HUB_ segregate control and phase nets. DC_LINK / PGND shared.',25.4,35.56)
root.text('36-58.4 V screening range only. No validated current rating. No PCB or routing.',25.4,43.18)
root.text('Protected entry still missing; OV chopper and fault memory populated on dedicated pages.',25.4,50.8)
sheets=[]
for idx,prefix in enumerate(['GEN','HUB']):
    n=lambda x:prefix+'_'+x
    s=Sheet(prefix.lower()+'-driver',prefix+' DRV8353S driver and three low-side current channels')
    s.text('TI SLVSDY6A pp6-7 pin table. 40-pin RTA + exposed pad. SPI variant, NOT hardware variant.',20.32,15.24)
    s.text('VM supplied by bus-fed auxiliary 12 V. VREF=3V3 (CSA midpoint internally VREF/2).',20.32,22.86)
    s.text('RELEASE BLOCKERS: firmware, OC timing/coverage and transient/thermal qualification unfinished.',20.32,30.48)
    mapping={str(i+1):n(name) for i,name in enumerate(names)}
    for name in ['AGND','GND','EP','SNA','SNB','SNC']:mapping[str(names.index(name)+1)]='PGND'
    for name,net in [('VM','AUX12V'),('VDRAIN','DC_LINK'),('VREF','LOGIC3V3_EXT')]:mapping[str(names.index(name)+1)]=net
    for p in 'ABC': mapping[str(names.index('SH'+p)+1)]=n('PHASE_'+p); mapping[str(names.index('SP'+p)+1)]=n('SHUNT_'+p)
    for name,net in [('SCLK','DRV_SCK'),('SDI','DRV_MOSI'),('SDO','DRV_MISO')]:mapping[str(names.index(name)+1)]=net
    s.part(DRV,'U'+str(idx+1),'DRV8353SRTAT',76.2,114.3,mapping,'')
    specs=[('47n 100V X7R',n('CPH'),n('CPL')),('1u 16V X7R',n('VCP'),'DC_LINK'),('1u 16V X7R',n('VGLS'),'PGND'),('1u 10V X7R',n('DVDD'),'PGND'),('100n 25V X7R','AUX12V','PGND'),('10u 25V X7R','AUX12V','PGND'),('100n 10V X7R','LOGIC3V3_EXT','PGND')]
    for j,(v,a,b) in enumerate(specs):passive(s,'C',v,177.8+(j%3)*71.12,63.5+(j//3)*40.64,a,b)
    for j,(v,a,b) in enumerate([('100k',n('ENABLE'),'PGND'),('10k',n('nFAULT'),'LOGIC3V3_EXT'),('10k','DRV_MISO','LOGIC3V3_EXT'),('10k',n('nSCS'),'LOGIC3V3_EXT')]):passive(s,'R',v,177.8+(j%3)*71.12,190.5+(j//3)*35.56,a,b)
    s.text('ENABLE pull-down defaults off; not a safety-rated inhibit. SPI configuration and CSA gain20 not yet validated.',20.32,259.08)
    s.save();sheets.append(s)
    b=Sheet(prefix.lower()+'-bridge',prefix+' 100 V MOSFET bridge - schematic only')
    b.text('CSD19532Q5B stock KiCad symbol / pad map. Gates: 4; drains: 5; sources: 1,2,3.',20.32,15.24)
    b.text('Labels are electrical connections. Rgate=4R7 provisional. Kelvin shunts: no routing qualified.',20.32,22.86)
    for j,p in enumerate('ABC'):
        x=63.5+j*116.84
        for high,y in [(True,63.5),(False,134.62)]:
            gate=n(('GH' if high else 'GL')+p);gnet=gate+'_FET';src=n('PHASE_'+p) if high else n('SHUNT_'+p);drain='DC_LINK' if high else n('PHASE_'+p)
            counters['Q']+=1;ref='Q'+str(counters['Q']); nets={num: (gnet if name=='G' else drain if name=='D' else src) for num,name,*_ in pins(FET)}
            b.part(FET,ref,'CSD19532Q5B',x,y,nets,'Package_TO_SOT_SMD:TDSON-8-1')
            passive(b,'R','4R7 provisional',x-27.94,y+10.16,gate,gnet)
            passive(b,'R','100k G-S',x+35.56,y+10.16,gnet,src)
        passive(b,'R','2m 1% 3W WSLP2512',x,193.04,n('SHUNT_'+p),'PGND','Resistor_SMD:R_2512_6332Metric')
        passive(b,'C','1u 100V X7R provisional',x,233.68,'DC_LINK','PGND')
    b.text('Shunt amplifier SPx taps SHUNT_x; SNx taps PGND: Kelvin layout mandatory. 15A RMS => 0.45W per shunt.',20.32,259.08)
    b.save();sheets.append(b)

s=Sheet('external-boundaries','Unfinished safety / control / supply boundaries')
s.text('OFFBOARD interfaces: 3V3 supply, brake loop and protected bus entry.',20.32,15.24)
s.text('DO NOT ENERGIZE. Protected entry unfinished; MCU and protection remain unqualified.',20.32,22.86)
def connector(value,nets,x,y):
    counters['J']+=1;s.part(stock('Connector_Generic','Conn_01x'+str(len(nets)).zfill(2)),'J'+str(counters['J']),value,x,y,{str(i+1):net for i,net in enumerate(nets)})
connector('PROTECTED_DC_INPUT_EXT',['DC_LINK','PGND'],63.5,48.26)
connector('MCU_SUPPLY_EXT',['LOGIC3V3_EXT','PGND'],63.5,83.82)
for j,prefix in enumerate(['GEN','HUB']):
    x=177.8+j*116.84
    connector(prefix+'_MACHINE_PHASES',[prefix+'_PHASE_'+p for p in 'ABC'],x,48.26)
connector('SAFETY_BRAKE_LOOP_NC',['SAFETY3V3','BRAKE_LOOP'],63.5,137.16)
passive(s,'C','100u 100V provisional',63.5,190.5,'DC_LINK','PGND')
s.text('Missing: source fuse, reverse blocking, precharge, DC contactor, bus current sensor and discharge.',20.32,228.6)
s.text('Populated: OV chopper, fault latch, brake loop, watchdog, aux supply. Added: raw CSA window trip; timing/coverage unqualified.',20.32,236.22)
s.text('MCU and sensor interfaces populated; firmware, thermal sensors, storage/BMS acceptance missing.',20.32,243.84)
s.text('PGND is common, not galvanically isolated. Supply sequencing and back-power paths unqualified.',20.32,251.46)
s.save();sheets.append(s)
custom_symbols=[]
from protection_circuit import populate
populate(globals())
from mcu_circuit import populate as populate_mcu
populate_mcu(globals())
from fast_oc_circuit import populate as populate_oc
populate_oc(globals())
local_symbols=[local_drv]
for a in custom_symbols:
    b=parse(dump(a));b[1]=q(val(b[1]).split(':')[1]);local_symbols.append(b)
(ROOT/'Powerboard.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "powerboard_generator") '+' '.join(dump(a) for a in local_symbols)+')\n')
for i,s in enumerate(sheets):
    x=25.4+(i%2)*177.8;y=71.12+(i//2)*58.42
    root.items.append(f'(sheet (at {x} {y}) (size 152.4 40.64) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {uid("sheet/"+s.name)}) (property "Sheetname" {q(s.title)} (at {x} {y-2.54} 0) (effects (font (size 1.27 1.27)) (justify left))) (property "Sheetfile" {q(s.name+".kicad_sch")} (at {x} {y+43.18} 0) (effects (font (size 1.27 1.27)) (justify left))) (instances (project "powerboard-reva" (path "/{ROOTID}" (page "{i+2}")))))')
root.save()
for fn,rows in [('review-bom.csv',bom),('pin-net-map.csv',pinmap)]:
    with (ROOT/fn).open('w') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator="\n");w.writeheader();w.writerows(rows)
(ROOT/'pinout-evidence.md').write_text('''# Pin provenance\n\n- DRV8353S: TI SLVSDY6A (June 2019), pp6–7, 40-pin RTA SPI pin table; https://www.ti.com/lit/gpn/DRV8353 . Exposed pad represented as pad41 to PGND; footprint/package thermal-pad verification remains a release gate.\n- CSD19532Q5B: installed KiCad 9 stock Transistor_FET symbol inherits Q_NMOS_SSSGD_AvalancheRated. Source1/2/3, gate4, drain5 (PowerPAD footprint convention). https://www.ti.com/lit/gpn/CSD19532Q5B . Stock footprint is candidate, not manufacturing qualification.\n- DRV recommended capacitors follow pin table: CPL–CPH 47nF VDRAIN-rated; VCP–VDRAIN 1uF16V; VGLS–GND 1uF16V; DVDD–GND 1uF; VM–GND 100nF +10uF; VREF–AGND100nF.\n- VM deliberately uses bus-fed auxiliary12V rather than unrestricted DC link; VDRAIN uses DC_LINK. VREF uses3V3, not1V65; CSA midpoint is internal VREF/2.\n- Resistor values, DC-link capacitance, connectors and passive footprints are provisional or unselected. No validated thermal, ripple, transient, clearance or interrupt ratings.\n''')
print(f'Generated {len(sheets)+1} hierarchical pages, {len(bom)} components, {len(pinmap)} pin assignments')
