"""Placed protection circuit; called by hierarchical schematic generator."""
def populate(g):
    Sheet,parse,q,stock,passive,pins=g['Sheet'],g['parse'],g['q'],g['stock'],g['passive'],g['pins']
    def ic(name, pin_names, outputs=(), powerout=(), oc=()):
        text=f'(symbol "Powerboard:{name}" (pin_names (offset 1)) (in_bom yes) (on_board yes) (symbol "{name}_0_1" (rectangle (start -15.24 2.54) (end 15.24 {-5.08*len(pin_names)}) (stroke (width .254) (type default)) (fill (type background)))) (symbol "{name}_1_1"'
        for i,n in enumerate(pin_names,1):
            typ='open_collector' if i in oc else 'power_out' if i in powerout else 'output' if i in outputs else 'power_in' if n in ['VCC','VDD','GND','IN'] else 'input'
            text+=f' (pin {typ} line (at -20.32 {-5.08*(i-1)} 0) (length 5.08) (name {q(n)} (effects (font (size 1 1)))) (number "{i}" (effects (font (size 1 1)))))'
        a=parse(text+'))');g['custom_symbols'].append(a);return a
    def part(s,a,ref,mpn,x,y,nets,fp):s.part(a,ref,mpn,x,y,{str(i+1):n for i,n in enumerate(nets)},fp)
    def r(s,v,x,y,a,b):return passive(s,'R',v,x,y,a,b,'Resistor_SMD:R_0805_2012Metric')
    def c(s,v,x,y,a,b):return passive(s,'C',v,x,y,a,b,'Capacitor_SMD:C_0805_2012Metric')
    aux=Sheet('aux-supply','Bus-fed auxiliary and independent safety supply')
    aux.text('R-78HB12-0.5: 17-72V operating, 75V absolute. Entry transient protection still REQUIRED.',20.32,15.24)
    part(aux,ic('R78HB',['IN','GND','OUT'],powerout=(3,)),'U3','R-78HB12-0.5',63.5,50.8,['DC_LINK','PGND','AUX12V'],'')
    part(aux,ic('TLV760',['OUT','IN','GND'],powerout=(1,)),'U4','TLV76033DBZR',177.8,50.8,['SAFETY3V3','AUX12V','PGND'],'Package_TO_SOT_SMD:SOT-23')
    c(aux,'3.3u 100V GRM32ER72A335KA35L',63.5,109.22,'DC_LINK','PGND')
    c(aux,'10u 25V GRM21BR61E106KA73L',139.7,109.22,'AUX12V','PGND')
    c(aux,'1u 25V GRM21BR71E105KA99L',215.9,109.22,'SAFETY3V3','PGND')
    r(aux,'1k 1% CRCW08051K00FKEA',292.1,109.22,'AUX12V','PGND')
    part(aux,ic('LM4040',['K','A','NC']), 'U5','LM4040AIM3-2.5/NOPB',63.5,172.72,['REF2V5','PGND','PGND'],'Package_TO_SOT_SMD:SOT-23')
    r(aux,'4k7 1% CRCW08054K70FKEA',139.7,172.72,'AUX12V','REF2V5')
    c(aux,'100n 25V GRM21BR71E104KA01L',215.9,172.72,'REF2V5','PGND')
    aux.text('Safety supply is NOT the MCU supply. LOGIC3V3_EXT remains a supervised, external MCU rail.',20.32,241.3)
    aux.text('Supply total/current/thermal budget provisional; no galvanic isolation or stored-energy ride-through.',20.32,251.46)
    aux.save();g['sheets'].append(aux)
    s=Sheet('protection-comparators','Autonomous OV chopper comparator and rail / brake monitors')
    s.text('Comparator powered from AUX12V; open collectors pulled to SAFETY3V3. No MCU in OV path.',20.32,15.24)
    a=ic('LM339B',['OUT1','OUT2','VCC','IN2-','IN2+','IN1-','IN1+','IN3-','IN3+','IN4-','IN4+','GND','OUT4','OUT3'],oc=(1,2,13,14))
    part(s,a,'U6','LM339BIDR',63.5,43.18,['HEALTHY','OV_CMD','AUX12V','REF2V5','OV_SENSE','REF2V5','AUX_SENSE','REF2V5','MCU_SENSE','REF2V5','BRAKE_LOOP','PGND','HEALTHY','HEALTHY'],'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm')
    specs=[('112k 0.1% ERA-6AEB1123V','DC_LINK','OV_MID'),('113k 0.1% ERA-6AEB1133V','OV_MID','OV_SENSE'),('10k 0.1% ERA-6AEB103V','OV_SENSE','PGND'),('330k 0.1% ERA-6AEB334V','OV_CMD','OV_SENSE'),('1k 1% CRCW08051K00FKEA','SAFETY3V3','OV_CMD'),('30k 0.1% ERA-6AEB303V','AUX12V','AUX_SENSE'),('10k 0.1% ERA-6AEB103V','AUX_SENSE','PGND'),('2k 0.1% ERA-6AEB202V','LOGIC3V3_EXT','MCU_SENSE'),('10k 0.1% ERA-6AEB103V','MCU_SENSE','PGND'),('10k 1% CRCW080510K0FKEA','BRAKE_LOOP','PGND'),('4k7 1% CRCW08054K70FKEA','SAFETY3V3','HEALTHY')]
    for i,(v,a,b) in enumerate(specs):r(s,v,177.8+(i%3)*76.2,50.8+(i//3)*45.72,a,b)
    c(s,'100p C0G GRM21A5C1H101JA01D',177.8,238.76,'OV_SENSE','PGND')
    c(s,'100n 25V GRM21BR71E104KA01L',292.1,238.76,'AUX12V','PGND')
    s.text('BRAKE_LOOP must close to SAFETY3V3 through normally-closed brake + thermal switches. Open wire trips.',20.32,266.7)
    s.save();g['sheets'].append(s)
    s=Sheet('fault-latch','Set-dominant fault memory and hardware bridge enable')
    s.text('HEALTHY low SETS fault; RESET_REQUEST accepted only while HEALTHY high. ARM alone cannot reset.',20.32,15.24)
    part(s,ic('HC00',['1A','1B','1Y','2A','2B','2Y','GND','3Y','3A','3B','4Y','4A','4B','VCC'],outputs=(3,6,8,11)),'U7','SN74HC00DR',63.5,43.18,['HEALTHY','RESET_REQUEST','RESET_N','HEALTHY','PERMIT','FAULT_LATCH','PGND','PERMIT','RESET_N','FAULT_LATCH','UNUSED_NAND','PGND','PGND','SAFETY3V3'],'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm')
    part(s,ic('HC11',['1A','1B','2A','2B','2C','2Y','GND','3Y','3A','3B','3C','1Y','1C','VCC'],outputs=(6,8,12)),'U8','SN74HC11DR',177.8,43.18,['HEALTHY','PERMIT','HEALTHY','PERMIT','MCU_ARM','HUB_ENABLE_RAW','PGND','TIMER_BREAK_OK','HEALTHY','PERMIT','SAFETY3V3','GEN_ENABLE_RAW','MCU_ARM','SAFETY3V3'],'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm')
    part(s,ic('TPS3823',['RESET_N','GND','MR_N','WDI','VDD'],outputs=(1,)),'U9','TPS3823-33DBVR',292.1,43.18,['WD_RESET_N','PGND','SAFETY3V3','WDI','SAFETY3V3'],'Package_TO_SOT_SMD:SOT-23-5')
    for i,n in enumerate(['GEN_nFAULT','HUB_nFAULT','WD_RESET_N']):
        s.part(stock('Device','D'),'D'+str(i+1),'BAT54WS-7-F',292.1,96.52+i*30.48,{'1':n,'2':'HEALTHY'},'Diode_SMD:D_SOD-323')
    r(s,'100k CRCW0805100KFKEA',292.1,200.66,'UNUSED_NAND','PGND')
    for i,n in enumerate(['RESET_REQUEST','MCU_ARM','WDI']):r(s,'10k 1% CRCW080510K0FKEA',63.5+i*76.2,200.66,n,'PGND')
    r(s,'1k 1% CRCW08051K00FKEA',63.5,236.22,'GEN_ENABLE_RAW','GEN_ENABLE')
    r(s,'1k 1% CRCW08051K00FKEA',139.7,236.22,'HUB_ENABLE_RAW','HUB_ENABLE')
    for i in range(3):c(s,'100n 25V GRM21BR71E104KA01L',215.9+i*50.8,236.22,'SAFETY3V3','PGND')
    s.text('Watchdog WDI cannot float: fitted 10k pulldown. 0.9-2.5s timeout is NOT short-circuit protection.',20.32,266.7)
    s.save();g['sheets'].append(s)
    s=Sheet('brake-chopper','Independent brake chopper power stage')
    s.text('Autonomous OV path ignores bridge ENABLE. External resistor is physically required across J12 pins.',20.32,15.24)
    part(s,ic('UCC27511',['VDD','OUTH','OUTL','GND','IN-','IN+'],outputs=(2,3)),'U10','UCC27511DBVR',63.5,50.8,['AUX12V','CHOP_SOURCE','CHOP_SINK','PGND','PGND','OV_CMD'],'Package_TO_SOT_SMD:SOT-23-6')
    fet=g['FET'];s.part(fet,'Q13','CSD19532Q5B',215.9,76.2,{num:('CHOP_GATE' if name=='G' else 'DUMP_LOW' if name=='D' else 'PGND') for num,name,*_ in pins(fet)},'Package_TO_SOT_SMD:TDSON-8-1')
    r(s,'10R CRCW080510R0FKEA',139.7,132.08,'CHOP_SOURCE','CHOP_GATE')
    r(s,'2R2 CRCW08052R20FKEA',215.9,132.08,'CHOP_SINK','CHOP_GATE')
    r(s,'10k CRCW080510K0FKEA',292.1,132.08,'CHOP_GATE','PGND')
    c(s,'1u 25V GRM21BR71E105KA99L',63.5,187.96,'AUX12V','PGND')
    c(s,'100n 25V GRM21BR71E104KA01L',139.7,187.96,'AUX12V','PGND')
    g['counters']['J']+=1
    part(s,stock('Connector_Generic','Conn_01x02'),'J'+str(g['counters']['J']),'EXTERNAL_DUMP_RESISTOR',292.1,187.96,['DC_LINK','DUMP_LOW'],'')
    s.text('Candidate: 2 x TE HSC3004R7J in series (9.4 ohm). Chassis/heatsink + NC thermal cutoff required.',20.32,241.3)
    s.text('No resistor cable clamp / fuse / SOA qualification yet. Loss of AUX supply loses bus sink: NOT FAIL SAFE.',20.32,251.46)
    s.save();g['sheets'].append(s)
