"""Six raw-CSA windows; no MCU dependency, no continuous phase-current claim."""
def populate(g):
    Sheet,stock,passive,parse,q = (g[k] for k in ['Sheet','stock','passive','parse','q'])
    text='(symbol "Powerboard:TLV3202" (pin_names (offset 1)) (in_bom yes) (on_board yes) (symbol "TLV3202_0_1" (rectangle (start -15.24 2.54) (end 15.24 -40.64) (stroke (width .254) (type default)) (fill (type background)))) (symbol "TLV3202_1_1"'
    for i,n in enumerate(['OUT1','IN1-','IN1+','GND','IN2+','IN2-','OUT2','VCC'],1):
        typ='output' if i in [1,7] else 'power_in' if i in [4,8] else 'input'
        text+=f' (pin {typ} line (at -20.32 {-5.08*(i-1)} 0) (length 5.08) (name {q(n)} (effects (font (size 1 1)))) (number "{i}" (effects (font (size 1 1)))))'
    cmp=parse(text+'))');g['custom_symbols'].append(cmp)
    def r(s,v,x,y,a,b):passive(s,'R',v,x,y,a,b,'Resistor_SMD:R_0805_2012Metric')
    for bi,bridge in enumerate(['GEN','HUB']):
        s=Sheet(bridge.lower()+'-fast-oc',bridge+' independent raw CSA window trips')
        s.text('TLV3202IDR: positive SP-SN current DECREASES SO. Lower and upper limits both latch off.',20.32,15.24)
        s.text('No PWM blanking added. Low-side blind intervals remain; DRV VDS OCP contract mandatory.',20.32,22.86)
        for j,phase in enumerate('ABC'):
            i=bi*3+j;source=f'{bridge}_SO{phase}';x=63.5+j*116.84
            nets=[source+'_LO',source,'OC_LOW_REF','PGND',source,'OC_HIGH_REF',source+'_HI','LOGIC3V3_EXT']
            s.part(cmp,f'U{18+i}','TLV3202IDR',x,48.26,{str(k+1):n for k,n in enumerate(nets)},'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm')
            passive(s,'C','100n X7R 25V',x,111.76,'LOGIC3V3_EXT','PGND','Capacitor_SMD:C_0805_2012Metric')
            r(s,'100k 1% open SO bias',x,142.24,source,'PGND')
            for k,suffix in enumerate(['LO','HI']):
                xx=x-25.4+k*50.8;out=source+'_'+suffix
                s.part(stock('Transistor_FET','2N7002'),f'Q{14+i*2+k}','2N7002',xx,185.42,{'1':out,'2':'PGND','3':'OC_OK'},'Package_TO_SOT_SMD:SOT-23')
                r(s,'100k 1% gate default',xx,226.06,out,'PGND')
        s.text('Push-pull comparators drive separate sink FETs; outputs are NOT shorted together.',20.32,254)
        s.text('Open SO pulls down; stuck midpoint / shunt open / power-loss safety NOT proven. UNSAFE DRAFT.',20.32,264.16)
        s.save();g['sheets'].append(s)
    s=Sheet('fast-oc-reference','Ratiometric OC window and wired sink fault')
    s.text('VREF tracks actual driver LOGIC3V3_EXT: 0.852713 / 2.447287 V nominal at 3.3 V.',20.32,20.32)
    for j,(v,a,b) in enumerate([('28k7 0.1%','LOGIC3V3_EXT','OC_LOW_REF'),('10k 0.1%','OC_LOW_REF','PGND'),('10k 0.1%','LOGIC3V3_EXT','OC_HIGH_REF'),('28k7 0.1%','OC_HIGH_REF','PGND'),('4k7 1%','SAFETY3V3','OC_OK')]):
        r(s,v,63.5+(j%3)*116.84,63.5+(j//3)*60.96,a,b)
    s.text('OC_OK directly enters U14.6, clears U7/U8 and U16: both ENABLE and TIM1/TIM8 break.',20.32,210.82)
    s.text('No external hysteresis or blanking: first crossing latches. Noise/settling and sink delay unqualified.',20.32,223.52)
    s.text('Nominal trip +/-19.932 A; provisional measurement +/-30 A. Commissioning cap 10 A, NOT release.',20.32,236.22)
    s.save();g['sheets'].append(s)
