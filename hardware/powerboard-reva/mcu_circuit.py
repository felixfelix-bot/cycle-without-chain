"""STM32G474VET6 engineering schematic; no firmware or safety qualification.
Pin provenance: docs/mcu-source-evidence.md / DS12288 Rev5 T12/T13.
Additional pins: PE2/3/4=1/2/3 (T12); PB6/7=93/94 TIM4_CH1/2 AF2
(T13 p74); PG10-NRST=14, PB8-BOOT0=95, PA13/14 SWD=76/77.
"""

def populate(g):
    Sheet, stock, passive, pins = (g[k] for k in ['Sheet','stock','passive','pins'])
    def r(s,v,x,y,a,b):return passive(s,'R',v,x,y,a,b,'Resistor_SMD:R_0603_1608Metric')
    def c(s,v,x,y,a,b):return passive(s,'C',v,x,y,a,b,'Capacitor_SMD:C_0603_1608Metric')
    def conn(s,value,nets,x,y):
        g['counters']['J']+=1
        s.part(stock('Connector_Generic','Conn_01x'+str(len(nets)).zfill(2)), 'J'+str(g['counters']['J']),value,x,y,{str(i+1):n for i,n in enumerate(nets)})
    def save(s):s.save();g['sheets'].append(s)
    s=Sheet('mcu-core','STM32G474VET6 LQFP100: power, reset, debug and control')
    s.text('HSI16 internal clock / PLL option: no HSE or LSE fitted; PF0/PF1 and PC14/15 explicit NC.',20.32,15.24)
    s.text('BOOT0 low; keep NRST function and configure boot option bytes before use. No firmware supplied.',20.32,22.86)
    a=stock('MCU_ST_STM32G4','STM32G474VETx')
    mapping: dict[str, str | None]={num:None for num,*_ in pins(a)}
    fixed={39:'GEN_INLA',40:'GEN_INHA',41:'GEN_INLB',42:'GEN_INHB',43:'GEN_INLC',44:'GEN_INHC',65:'HUB_INHA',66:'HUB_INHB',67:'HUB_INHC',29:'HUB_INLA',32:'HUB_INLB',33:'HUB_INLC',46:'TIMER_BREAK_OK',84:'TIMER_BREAK_OK',27:'DRV_SCK',28:'DRV_MISO',92:'DRV_MOSI',62:'GEN_nSCS',45:'HUB_nSCS',1:'MCU_ARM',2:'WDI',3:'RESET_REQUEST',61:'BRAKE_SENSE',14:'MCU_NRST',95:'MCU_BOOT0',76:'SWDIO',77:'SWCLK',93:'ENC_A',94:'ENC_B'}
    for p,n in fixed.items():mapping[str(p)]=n
    for p in [24,49,64,75,100,6]:mapping[str(p)]='LOGIC3V3_EXT'
    for p in [23,48,63,74,99,35]:mapping[str(p)]='PGND'
    mapping['37']='MCU_VDDA';mapping['36']='MCU_VREF'
    for p,n in {20:'GEN_SOA',21:'GEN_SOB',22:'GEN_SOC',15:'HUB_SOA',16:'HUB_SOB',17:'HUB_SOC'}.items():mapping[str(p)]=n+'_ADC'
    for i,p in enumerate(range(55,61)):mapping[str(p)]=('GEN' if i<3 else 'HUB')+'_HALL_'+str(i%3+1)
    s.part(a,'U17','STM32G474VET6',101.6,139.7,mapping,'Package_QFP:LQFP-100_14x14mm_P0.5mm')
    conn(s,'SWD_3V3_TARGET_REFERENCE',['LOGIC3V3_EXT','SWDIO','SWCLK','MCU_NRST','PGND'],266.7,53.34)
    r(s,'10k NRST',215.9,109.22,'MCU_NRST','LOGIC3V3_EXT')
    c(s,'100n NRST',292.1,109.22,'MCU_NRST','PGND')
    r(s,'10k BOOT0',215.9,152.4,'MCU_BOOT0','PGND')
    conn(s,'RESET_BUTTON_NORMALLY_OPEN',['MCU_NRST','PGND'],292.1,152.4)
    s.text('BKIN active LOW required in TIM1/TIM8. Separate hardware ENABLE path remains intact.',20.32,238.76)
    s.text('NC GPIO: leave analog mode; HSI accuracy / PLL / ADC timing require validation.',20.32,246.38)
    s.text('MCU_ARM / RESET_REQUEST 10k and WDI 1k default-low resistors are on fault-latch page.',20.32,254)
    save(s)
    s=Sheet('mcu-power','MCU 3V3 decoupling - external supervised rail')
    s.text('One 100n per VDD pin (24,49,64,75,100) plus VBAT pin6. Place each at pin / ground return.',20.32,15.24)
    for i,p in enumerate([24,49,64,75,100,6]):c(s,f'100n 10V X7R pin{p}',63.5+(i%3)*116.84,60.96+(i//3)*40.64,'LOGIC3V3_EXT','PGND')
    c(s,'4u7 10V X7R bulk',63.5,142.24,'LOGIC3V3_EXT','PGND')
    for i,n in enumerate(['MCU_VDDA','MCU_VREF']):
        y=190.5+i*45.72
        r(s,'0R analog supply link',63.5,y,'LOGIC3V3_EXT',n)
        c(s,'100n 10V X7R',177.8,y,n,'PGND')
        c(s,'1u 10V X7R',292.1,y,n,'PGND')
    s.text('VREFBUF MUST remain disabled: external 3V3 reference. VDDA/VREF tied via 0R; not precision isolated.',20.32,266.7)
    save(s)
    s=Sheet('mcu-analog','Six CSA ADC input filters and brake status sense')
    s.text('100R / 1nF candidate filters: settling / sample aperture / CSA gain remain unqualified.',20.32,15.24)
    for i,n in enumerate(['GEN_SOA','GEN_SOB','GEN_SOC','HUB_SOA','HUB_SOB','HUB_SOC']):
        x=63.5+(i%3)*116.84;y=60.96+(i//3)*76.2
        r(s,'100R 1%',x,y,n,n+'_ADC');c(s,'1n C0G',x,y+30.48,n+'_ADC','PGND')
    r(s,'10k brake sense',63.5,218.44,'BRAKE_LOOP','BRAKE_SENSE')
    r(s,'100k brake default',177.8,218.44,'BRAKE_SENSE','PGND')
    c(s,'1n brake filter',292.1,218.44,'BRAKE_SENSE','PGND')
    s.text('BRAKE_SENSE is status ONLY. Brake comparator and fault path do not depend on firmware.',20.32,261.62)
    save(s)
    s=Sheet('mcu-sensors','3V3 Hall interfaces and optional quadrature encoder')
    s.text('3V3 ONLY: open-collector Hall / encoder or compatible 3V3 outputs. NO 5V tolerance claim.',20.32,15.24)
    for j,pre in enumerate(['GEN','HUB']):
        y=50.8+j*76.2
        conn(s,pre+'_HALL_3V3_ONLY',['LOGIC3V3_EXT','PGND']+[f'{pre}_HALL_{i}_EXT' for i in range(1,4)],50.8,y)
        for i in range(1,4):
            n=f'{pre}_HALL_{i}';x=139.7+(i-1)*88.9
            r(s,'10k Hall pullup',x,y,n+'_EXT','LOGIC3V3_EXT')
            r(s,'1k Hall series',x,y+25.4,n+'_EXT',n)
            c(s,'1n Hall filter',x,y+50.8,n,'PGND')
    conn(s,'OPTIONAL_ENCODER_3V3_ONLY',['LOGIC3V3_EXT','PGND','ENC_A_EXT','ENC_B_EXT'],50.8,218.44)
    for i,n in enumerate(['ENC_A','ENC_B']):
        x=177.8+i*116.84
        r(s,'10k encoder pullup',x,203.2,n+'_EXT','LOGIC3V3_EXT')
        r(s,'1k encoder series',x,226.06,n+'_EXT',n)
        c(s,'1n encoder filter',x,248.92,n,'PGND')
    s.text('Encoder PB6/PB7: TIM4_CH1/CH2 AF2 DS12288r5 T13 p74. Cable ESD/EMC protection unresolved.',20.32,274.32)
    save(s)
