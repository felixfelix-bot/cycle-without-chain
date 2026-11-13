"""Bounded passive bench entry. Not a battery/vehicle released protection system."""
def populate(g):
    Sheet,stock,passive=(g[k] for k in ['Sheet','stock','passive'])
    s=Sheet('dc-entry','Bounded bench DC entry - active pairs inhibited')
    s.text('NOT SAFE TO ENERGIZE integrated drive. No automatic sequencing or reverse-blocking guarantee.',20.32,15.24)
    s.text('36-58.4V bench interface, 15A TARGET ONLY. Disconnect PM machines before source removal.',20.32,22.86)
    def part(lib,name,ref,value,x,y,nets,footprint=''):s.part(stock(lib,name),ref,value,x,y,nets,footprint=footprint)
    # J40 carries the full DC_LINK current (~13 A at 150-250 W crank, 145 kg) at
    # up to 56 V. It previously landed on a 1x01 2.54 mm pin header: one ~1 mm
    # pin rated near 3 A, and no pad at all for pin 2 (PGND), so PGND was a live
    # net with nowhere to terminate. XT60 is 2-pole, keyed, and both pads are
    # 4.5 mm drills for real cable. The SB50 housing stays the harness end.
    part('Connector_Generic','Conn_01x02','J40','Anderson 992G1 SB50 keyed SOURCE',50.8,53.34,{'1':'SOURCE_POS','2':'PGND'},
         footprint='Connector_AMASS:AMASS_XT60-F_1x02_P7.20mm_Vertical')
    part('Device','Fuse','F1','KLKD020CN 20A 600VDC',114.3,53.34,{'1':'SOURCE_POS','2':'ENTRY_FUSED'})
    # J41/J42 removed, not left as a parallel bypass of the active pairs.
    passive(s,'R','22R 1% RH05022R00FE02 pulse UNQUALIFIED',139.7,114.3,'PRECHARGE_R','BUS_SHUNT_HI')
    passive(s,'R','2m 1% WSLP2512R0020FEA Kelvin',241.3,114.3,'BUS_SHUNT_HI','DC_LINK')
    part('Device','D','D20','STPS30100ST reverse clamp ONLY not reverse blocker',330.2,53.34,{'1':'DC_LINK','2':'PGND'})
    passive(s,'C','470u 100V UHE2A471MHD +/-20%',50.8,180.34,'DC_LINK','PGND')
    passive(s,'C','470u 100V UHE2A471MHD +/-20%',139.7,180.34,'DC_LINK','PGND')
    passive(s,'R','10k 1% RH02510K00FE02 always-on bleed',241.3,180.34,'DC_LINK','PGND')
    # J43 pin map per dc-entry-milestone.md: pins 1/2 are the two Kelvin taps
    # across the 2 mOhm bus shunt, pin 3 DC_LINK, pin 4 PGND. Pin 2 lands on
    # DC_LINK because that IS the shunt's low side (R117 joins BUS_SHUNT_HI to
    # DC_LINK) -- the duplication of names is correct, not a defect. Checked
    # before "fixing" it: inventing a BUS_SHUNT_LO net would have created a
    # net that exists nowhere else on the board.
    part('Connector_Generic','Conn_01x04','J43','Kelvin BUS measurement isolated instrument ONLY',330.2,180.34,{'1':'BUS_SHUNT_HI','2':'DC_LINK','3':'DC_LINK','4':'PGND'},
         footprint='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical')
    s.text('J41/J42 removed. MAIN/PRE physical pairs are inhibited on separate sheets. NO ENERGIZE.',20.32,238.76)
    s.text('J43 raw high common mode: NOT MCU ADC. D20/fuse reverse-fault coordination UNQUALIFIED.',20.32,248.92)
    s.text('Sink/chopper stays DC_LINK side. MAIN open does NOT make bus safe: PM backfeeds via diodes.',20.32,259.08)
    s.save();g['sheets'].append(s)
