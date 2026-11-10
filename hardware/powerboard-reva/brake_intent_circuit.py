"""Candidate rider interface, not a qualified positive-torque safety interlock."""
def populate(g):
    Sheet,stock,passive=g['Sheet'],g['stock'],g['passive']
    def r(s,v,x,y,a,b): return passive(s,'R',v,x,y,a,b,'Resistor_SMD:R_0805_2012Metric')
    def c(s,v,x,y,a,b): return passive(s,'C',v,x,y,a,b,'Capacitor_SMD:C_0805_2012Metric')
    def conn(s,ref,v,nets,x,y):
        s.part(stock('Connector_Generic','Conn_01x'+str(len(nets)).zfill(2)),ref,v,x,y,{str(i+1):n for i,n in enumerate(nets)})
    for j,side in enumerate(['LEFT','RIGHT']):
        s=Sheet('brake-intent-'+side.lower(),side+' supervised binary brake interface')
        s.text('Candidate only: reversible non-load-bearing lever sensors. NO mechanical brake cable alteration.',20.32,15.24)
        conn(s,'J'+str(44+j),side+'_BINARY_SWITCH_ONLY',['PGND',side+'_SWITCH_EXT'],50.8,55.88)
        for k,kind in enumerate(['SWITCH']):
            n=side+'_'+kind;i=j+2;y=111.76+k*76.2
            r(s,'10k 1% signal current limit',63.5,y,n+'_EXT',n+'_ADC')
            r(s,'10k 1% switch bias',139.7,y,n+'_EXT','LOGIC3V3_EXT')
            c(s,'10n ADC filter',215.9,y,n+'_ADC','PGND')
            s.part(stock('Device','D_TVS'),'D'+str(30+i),'PESD3V3U1UL',292.1,y,{'1':n+'_EXT','2':'PGND'},'Diode_SMD:D_SOD-882')
            s.part(stock('Diode','BAT54S'),'D'+str(34+i),'BAT54S',292.1,y+35.56,{'1':'PGND','2':'LOGIC3V3_EXT','3':n+'_ADC'},'Package_TO_SOT_SMD:SOT-23')
        s.text('External switch harness: 4k7 series + (10k parallel NC switch). Release=1.055V; press=1.964V.',20.32,259.08)
        s.text('Open=3V3 / short=0V faults via ADC; firmware NOT implemented. Clamp injection/power-off NOT qualified.',20.32,269.24)
        s.save();g['sheets'].append(s)
    s=Sheet('brake-dump-command','Rider dump PWM OR independent emergency overvoltage')
    s.part(stock('74xGxx','74LVC1G32'),'U24','SN74LVC1G32DBVR',76.2,60.96,{'1':'OV_CMD','2':'BRAKE_DUMP_PERMITTED','3':'PGND','4':'CHOP_CMD','5':'SAFETY3V3'},'Package_TO_SOT_SMD:SOT-23-5')
    s.part(stock('74xGxx','74LVC1G08'),'U25','SN74LVC1G08DBVR',76.2,203.2,{'1':'BRAKE_DUMP_PWM','2':'TIMER_BREAK_OK','3':'PGND','4':'BRAKE_DUMP_PERMITTED','5':'SAFETY3V3'},'Package_TO_SOT_SMD:SOT-23-5')
    c(s,'100n AND decoupling',177.8,203.2,'SAFETY3V3','PGND')
    r(s,'10k dump PWM default off',177.8,60.96,'BRAKE_DUMP_PWM','PGND')
    c(s,'100n OR decoupling',292.1,60.96,'SAFETY3V3','PGND')
    s.text('OV always overrides MCU PWM. Normal PWM must require valid rider request AND cool dump permission.',20.32,109.22)
    s.text('PWM AND TIMER_BREAK_OK: watchdog / E-stop / thermal fault kill normal dump. OV bypass retained.',20.32,121.92)
    s.text('No torque-sign hardware guard. Firmware must disarm on sensor fault; watchdog / OC / E-stop remain hardware kills.',20.32,134.62)
    s.text('Firmware entirely unimplemented. Do not energize; brake command control only a design contract.',20.32,147.32)
    s.save();g['sheets'].append(s)
    s=Sheet('brake-switch-harness','OFFBOARD supervised switch end-of-line network - candidate')
    s.text('OFFBOARD parts must live at lever, not board. NC contact opens on rider braking. No brake cable modification.',20.32,15.24)
    for j,side in enumerate(['LEFT','RIGHT']):
        n=side+'_SWITCH';x=76.2+j*177.8
        r(s,'4k7 1% EOL OFFBOARD',x,76.2,n+'_EXT',n+'_EOL')
        r(s,'10k 1% EOL OFFBOARD',x,134.62,n+'_EOL','PGND')
        s.part(stock('Switch','SW_SPST'),'SW'+str(j+1),'NC_RELEASE_OPEN_ON_BRAKE_UNSELECTED',x,190.5,{'1':n+'_EOL','2':'PGND'})
    s.text('Switch symbol drawn open (braking). Model cables unplugged by removing BOTH EOL resistors and switch.',20.32,248.92)
    s.text('Welded contact or resistor short can imitate release; FSR plausibility is firmware only, not independent safety.',20.32,261.62)
    s.save();g['sheets'].append(s)
