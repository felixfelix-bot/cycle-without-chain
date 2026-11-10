"""Low-voltage FSR bench candidate; TI SBOS351E DBV and SCDS390B PW pins.
No battery-short protection or torque-sign hardware interlock is claimed.
"""
def symbol(g, name, names, types):
    q = g['q']
    text = f'(symbol "Powerboard:{name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes) (property "Reference" "U" (at 0 25.4 0) (effects (font (size 1.27 1.27)))) (property "Value" {q(name)} (at 0 22.86 0) (effects (font (size 1.27 1.27)))) (symbol "{name}_0_1" (rectangle (start -15.24 20.32) (end 15.24 -20.32) (stroke (width 0.254) (type default)) (fill (type background)))) (symbol "{name}_1_1"'
    for i, label in enumerate(names):
        left = i < 7
        x, y, angle = (-20.32, 15.24-i*5.08, 0) if left else (20.32, 15.24-(i-7)*5.08, 180)
        text += f' (pin {types[i]} line (at {x} {y} {angle}) (length 5.08) (name {q(label)} (effects (font (size 1.016 1.016)))) (number "{i+1}" (effects (font (size 1.016 1.016)))))'
    a = g['parse'](text+'))')
    g['custom_symbols'].append(a)
    return a


def populate(g):
    Sheet, stock, passive = (g[k] for k in ['Sheet','stock','passive'])
    opa = symbol(g,'OPA333AIDBVR',['OUT','V-','+IN','-IN','V+'],['output','power_in','input','input','power_in'])
    mux = symbol(g,'TMUX1511PWR',['SEL1','S1','D1','SEL2','S2','D2','GND','D3','S3','SEL3','D4','S4','SEL4','VDD'],['input','passive','passive','input','passive','passive','power_in','passive','passive','input','passive','passive','input','power_in'])
    for j, side in enumerate(['LEFT','RIGHT']):
        s=Sheet('fsr-'+side.lower(),side+' selected FSR low-voltage bench frontend')
        n=lambda suffix: side+'_FSR_'+suffix
        s.text('Interlink 34-00018 external 402 short-tail pad; connector mate / mechanics UNQUALIFIED.',20.32,15.24)
        s.text('LOW-VOLTAGE BENCH ONLY. TVS / clamps candidates, NOT battery-short protection. No torque-sign guard.',20.32,22.86)
        s.part(stock('Connector_Generic','Conn_01x02'),'J'+str(46+j),side+'_FSR_34-00018_EXTERNAL',50.8,53.34,{'1':n('EXC_CABLE'),'2':n('RETURN_CABLE')})
        specs=[('R','10k 1% FSR excitation','MCU_VREF',n('EXC_CABLE')),
               ('R','1k 1% FSR return',n('RETURN_CABLE'),n('SENSE')),
               ('R','10k 0.1% FSR measure',n('SENSE'),'PGND'),
               ('C','100n FSR sense',n('SENSE'),'PGND'),
               ('R','10k 1% OPA input limit',n('SENSE'),n('OP_IN')),
               ('C','100n OPA bypass','MCU_VREF','PGND')]
        for i,(k,v,a,b) in enumerate(specs):
            passive(s,k,v,139.7+(i%3)*88.9,53.34+(i//3)*50.8,a,b,'Resistor_SMD:R_0805_2012Metric' if k=='R' else 'Capacitor_SMD:C_0805_2012Metric')
        s.part(opa,'U'+str(26+2*j),'OPA333AIDBVR',63.5,172.72,{'1':n('BUF'),'2':'PGND','3':n('OP_IN'),'4':n('BUF'),'5':'MCU_VREF'},'Package_TO_SOT_SMD:SOT-23-5')
        s.part(mux,'U'+str(27+2*j),'TMUX1511PWR',165.1,172.72,{'1':'FSR_SAMPLE_ENABLE','2':n('BUF'),'3':n('ISO_OUT'),'4':'PGND','5':None,'6':None,'7':'PGND','8':None,'9':None,'10':'PGND','11':None,'12':None,'13':'PGND','14':'LOGIC3V3_EXT'},'Package_SO:TSSOP-14_4.4x5mm_P0.65mm')
        for i,(k,v,a,b) in enumerate([
            ('R','1k 1% ADC isolation',n('ISO_OUT'),n('ADC')),
            ('R','10k 1% ADC bleed',n('ADC'),'PGND'),
            ('C','100n ADC reservoir',n('ADC'),'PGND'),
            ('R','100k enable default off','FSR_SAMPLE_ENABLE','PGND'),
            ('C','100n mux bypass','LOGIC3V3_EXT','PGND')]):
            passive(s,k,v,266.7+(i%2)*76.2,144.78+(i//2)*38.1,a,b,'Resistor_SMD:R_0805_2012Metric' if k=='R' else 'Capacitor_SMD:C_0805_2012Metric')
        s.text('MCU_VREF = excitation / OPA supply; LOGIC3V3_EXT = mux supply. PGND common; no isolation of ground.',20.32,248.92)
        s.text('Enable PE5 pin4 default low; 20ms blanking + plausibility pending firmware / bench validation.',20.32,259.08)
        s.text('Binary switch authoritative by firmware CONTRACT ONLY. Invalid FSR cannot authorize positive torque.',20.32,269.24)
        s.save();g['sheets'].append(s)
        s=Sheet('fsr-protection-'+side.lower(),side+' FSR candidate ESD and secondary clamps - unqualified')
        for i,leg in enumerate(['EXC_CABLE','RETURN_CABLE']):
            s.part(stock('Device','D_TVS'),'D'+str(38+j*3+i),'PESD3V3U1UL CANDIDATE',76.2+i*152.4,76.2,{'1':n(leg),'2':'PGND'},'Diode_SMD:D_SOD-882')
        s.part(stock('Diode','BAT54S'),'D'+str(40+j*3),'BAT54S CANDIDATE',152.4,160.02,{'1':'PGND','2':'MCU_VREF','3':n('SENSE')},'Package_TO_SOT_SMD:SOT-23')
        s.text('Connector TVS: cathode1 cable, anode2 ground. BAT54S: anode1 ground, cathode2 rail, junction3 sense.',20.32,22.86)
        s.text('NOT QUALIFIED: clamp voltage, leakage, negative pulses, rail sink / powered-off backfeed, ESD energy.',20.32,228.6)
        s.text('Battery short is a RELEASE BLOCKER. No external cable driver; segregated current-limited LV bench only.',20.32,241.3)
        s.text('TVS is NOT a 3.3V limiter. Secondary clamp can backfeed MCU_VREF. No vehicle energization authorization.',20.32,254)
        s.save();g['sheets'].append(s)
