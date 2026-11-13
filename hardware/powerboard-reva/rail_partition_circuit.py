"""Three-rail partition: always-on SINK12, delayed DRIVE12, delayed MCU3V3.

Sources actually read for this page (values are the manufacturers' own reference
designs, not invented numbers):
- TI LM5164 SNVSAU4D table 7-1 / figure 7-1 (VIN 15-100 V, VOUT 12 V, 1 A, 300 kHz):
  CIN 2x2.2u, COUT 2x22u, LO 68u, RRON 100k, RFB1 453k, RFB2 49.9k, RA 453k,
  CA 3300p, CB 56p, CBST 2.2n. EN/UVLO rising 1.45/1.50/1.55 V, falling
  1.35/1.40/1.44 V; shutdown current 3/15 uA; no-load IQ 10.5 uA.
- Diodes AP63200/AP63201/AP63203/AP63205 (DS-...): VIN 3.8-32 V, 2 A, fixed
  3.3 V (AP63203), 1.1 MHz, 4 ms soft start, EN rising 1.18 V typ / falling
  1.10 V typ, 1 uA shutdown, 22 uA no-load IQ, TSOT26 pin map
  1 FB, 2 EN, 3 VIN, 4 GND, 5 SW, 6 BST; table 2 recommends L 3.9u, C1 10u,
  C2 2x22u, C3 100n for the 3.3 V fixed output.
- TI SN74LVC1G08 pin map already used by U25 in this project
  (1 A, 2 B, 3 GND, 4 Y, 5 VCC).
- RECOM R-78HBxx-0.5 rev 2/2014: 500 mA output, 17-72 V input for the 12 V
  variant. This is the only source of SINK12; nothing here re-rates it.

PGOOD interlocks are populated; no supply-valid sequencer or MAIN conduction detector is
invented. MAIN_PROVEN_IN is an explicit, unimplemented external input held low by
a fitted 0-ohm tie, exactly like the inherited R402/R412 EN inhibits.
"""
from fsr_circuit import symbol


def populate(g):
    stock, q = g['stock'], g['q']
    s = g['Sheet']('rail-partition', 'Rail partition: SINK12 always-on, DRIVE12/MCU3V3 delayed and inhibited')
    s.text('NOT SAFE TO ENERGIZE. Partition of the former single AUX12V; no release or energization claim.', 20.32, 15.24)
    s.text('SINK12 = U3 R-78HB12-0.5 output: always bus-fed sink/safety cluster. 1.1 W input envelope, pre-proof only.', 20.32, 22.86)
    s.text('DRIVE12 = bus LM5164 (TI 12V reference values). LOGIC3V3_EXT = AP63203 from DRIVE12. Both EN held low by 100k.', 20.32, 30.48)
    s.text('DRIVE_EN = CTRL_PG AND MAIN_PROVEN_IN. MAIN_PROVEN_IN has a FITTED 0R inhibit to PGND.', 20.32, 38.1)

    # --- Delayed enable chain -------------------------------------------------
    andg = stock('74xGxx', '74LVC1G08')
    s.part(andg, 'U510', 'SN74LVC1G08DBVR', 76.2, 76.2,
           {'1': 'CTRL_PG', '2': 'MAIN_PROVEN_IN', '3': 'PGND', '4': 'DRIVE_EN', '5': 'SAFETY3V3'},
           'Package_TO_SOT_SMD:SOT-23-5')
    s.text('U510 is powered from SAFETY3V3, the always-on safety rail. Losing it floats Y: 100k pulldowns keep both EN low.',
           20.32, 116.84)

    # --- DRIVE12: second LM5164 straight from the bus, TI 12 V reference design
    buck = symbol(g, 'LM5164DDAR', ['GND', 'VIN', 'EN_UVLO', 'RON', 'FB', 'PGOOD', 'BST', 'SW', 'EP'],
                  ['power_in', 'power_in', 'input', 'input', 'input', 'open_collector', 'passive', 'power_out', 'passive'])
    s.part(buck, 'U501', 'LM5164DDAR', 76.2, 165.1,
           dict(zip(map(str, range(1, 10)),
                     ['PGND', 'DC_LINK', 'DRIVE_UVLO', 'DRIVE_RON', 'DRIVE_FB', 'DRIVE_PG',
                      'DRIVE_BST', 'DRIVE_SW', 'PGND'])))
    s.text('U501 is TI figure 7-1 (12 V/1 A/300 kHz) with RRON=100k and RFB1/RFB2=453k/49.9k. PGOOD drives DRIVE_PG only.', 20.32, 223.52)

    # --- Independent output OVP on DRIVE12 (was RAIL-01: LM5164 has no OVP) ---
    # TLV1701 (TI SBOS589D): 2.2-36 V open-drain comparator, 560 ns typ propagation,
    # 300 uV typ offset, output may be pulled to any rail <=42 V above V-.
    # Polarity matters: SBOS589D Table 8-1 gives output LOW when IN- > IN+. The sense
    # divider is therefore on IN- (pin 3) and the 2.5 V reference on IN+ (pin 1), so a
    # rising DRIVE12 pulls the open drain LOW. Reversed, the comparator would go high
    # exactly when the rail is over voltage and never protect anything.
    # The output sinks DRIVE_UVLO - the LM5164 EN/UVLO divider node - so a trip drives
    # EN toward 0 V (below the 1.1 V shutdown threshold) without contending with the
    # U510 gate output on DRIVE_EN.
    ovp = symbol(g, 'TLV1701DBVR', ['IN+', 'V-', 'IN-', 'OUT', 'V+'],
                 ['input', 'power_in', 'input', 'open_collector', 'power_in'])
    s.part(ovp, 'U503', 'TLV1701AIDBVR', 407.67, 165.1,
           {'1': 'REF2V5', '2': 'PGND', '3': 'DRIVE_OV_SENSE', '4': 'DRIVE_UVLO', '5': 'SINK12'},
           'Package_TO_SOT_SMD:SOT-23-5')
    s.text('U503 output pulls DRIVE_UVLO low when DRIVE12 exceeds 2.5V*(R523+R524)/R524 = 16.25 V nominal. '
           'Independent of the LM5164 FB node, so an open FB divider cannot hide the fault.', 20.32, 238.76)

    # --- MCU3V3: AP63203 fixed 3.3 V buck from DRIVE12 -------------------------
    ap = symbol(g, 'AP63203WU', ['FB', 'EN', 'VIN', 'GND', 'SW', 'BST'],
                ['input', 'input', 'power_in', 'power_in', 'power_out', 'passive'])
    s.part(ap, 'U502', 'AP63203WU', 254.0, 165.1,
           {'1': 'LOGIC3V3_EXT', '2': 'MCU3V3_EN', '3': 'DRIVE12', '4': 'PGND', '5': 'MCU_SW', '6': 'MCU_BST'},
           'Package_TO_SOT_SMD:TSOT-23-6')
    s.text('U502 pin map per Diodes TSOT26 table; FB tied to VOUT for the fixed 3.3 V variant.', 20.32, 231.14)

    parts = [
        # ref, value, net A, net B, footprint
        # L501 reselected for the converter's own 1.75 A top peak limit (was MSS1246T-683MLC,
        # Isat 2.26 A / Irms 1.30 A). TDK SPM10065VC-D (production; the VT variant is NRND
        # with this part named as its replacement) 68 uH row: Isat 7.3 A at dL=-30%,
        # Itemp 3.4 A at dT=40 C, Rdc 114 mOhm typ / 131.1 mOhm max, 80 V rated.
        # Footprint: hand-authored from TDK catalogue
        # inductor_automotive_power_spm10065vc-d_en (20250303) p3 RECOMMENDED LAND
        # PATTERN - 12.0 span / 6.1 gap / 4.5 height, pad width 2.95 derived.
        # NO stock KiCad land matches (nearest L_Coilcraft_XAL1010-XXX is 2.38 wide
        # on a 6.65 pitch), hence Powerboard.pretty. RAIL-18.
        ('L501', '68u SPM10065VC-680M-D 20% AEC-Q200', 'DRIVE_SW', 'DRIVE12',
         'Powerboard:L_TDK_SPM10065VC-D'),
        ('L502', '3.9u 2A', 'MCU_SW', 'LOGIC3V3_EXT', 'Inductor_SMD:L_Bourns_SRN6045TA'),
        ('C510', '2.2u 200V X7R 22252C225KAT2A', 'DC_LINK', 'PGND', 'Capacitor_SMD:C_2225_5664Metric'),
        ('C511', '2.2u 200V X7R 22252C225KAT2A', 'DC_LINK', 'PGND', 'Capacitor_SMD:C_2225_5664Metric'),
        ('C512', '2.2n 50V GCM155R71H222KA37D', 'DRIVE_BST', 'DRIVE_SW', ''),
        ('C513', '22u 25V TMK325B7226KMHT', 'DRIVE12', 'PGND', ''),
        ('C514', '22u 25V TMK325B7226KMHT', 'DRIVE12', 'PGND', ''),
        ('C515', '3.3n 100V CGA3E2X7R2A332K080AA', 'DRIVE_RAMP', 'DRIVE12', ''),
        ('C516', '56p 50V C0G', 'DRIVE_RAMP', 'DRIVE_FB', ''),
        ('C517', '10u 25V X7R', 'DRIVE12', 'PGND', ''),
        ('C518', '22u 16V X7R', 'LOGIC3V3_EXT', 'PGND', ''),
        ('C519', '22u 16V X7R', 'LOGIC3V3_EXT', 'PGND', ''),
        ('C520', '100n 25V X7R', 'MCU_BST', 'MCU_SW', ''),
        ('C521', '100n 25V X7R', 'SAFETY3V3', 'PGND', ''),
        ('R510', '100k 1% 0.1W TI reference', 'DRIVE_RON', 'PGND', ''),
        ('R511', '453k 1% 0.1W TI reference', 'DRIVE12', 'DRIVE_FB', ''),
        ('R512', '49.9k 1% RG1608P-4992-B-T5', 'DRIVE_FB', 'PGND', ''),
        ('R513', '453k 1% 0.1W TI reference', 'DRIVE_SW', 'DRIVE_RAMP', ''),
        ('R514', '82k 1% 0.1W >=100V', 'DRIVE_EN', 'DRIVE_UVLO', ''),
        ('R515', '100k 1% DELAY EN pulldown', 'DRIVE_UVLO', 'PGND', ''),
        ('R516', '47k 1% EN series', 'DRIVE_EN', 'MCU3V3_EN', ''),
        ('R517', '100k 1% DELAY EN pulldown', 'MCU3V3_EN', 'PGND', ''),
        ('R518', '100k 1% MAIN_PROVEN default low', 'MAIN_PROVEN_IN', 'PGND', ''),
        ('R519', '0R FIXED INHIBIT - no MAIN_PROVEN detector fitted', 'MAIN_PROVEN_IN', 'PGND', ''),
        ('R520', '10k CTRL PGOOD pullup', 'CTRL3V3', 'CTRL_PG', ''),
        # RAIL-04 decision: U501 PGOOD no longer joins the always-on ANALOG_OK chain.
        # It gets its own status net on an always-on pullup (PGOOD abs max 14 V, SINK12 max 12.36 V).
        ('R521', '47k 1% DRIVE_PG pullup (PGOOD abs max 14V)', 'SINK12', 'DRIVE_PG', ''),
        # RAIL-01 output OVP divider; trip 2.5V*(649k+118k)/118k = 16.25 V nominal.
        ('R523', '649k 0.1% DRIVE12 OVP upper leg', 'DRIVE12', 'DRIVE_OV_SENSE', ''),
        ('R524', '118k 0.1% DRIVE12 OVP lower leg', 'DRIVE_OV_SENSE', 'PGND', ''),
        # 100pF, not 1nF or 100nF. With Rth = 649k||118k = 99.85k, 100nF would add a
        # 9.98ms lag (324 V of overshoot at 32.4 mV/us) and defeat the OVP; 1nF gives
        # 100us => 3.24 V. 100pF gives tau = 9.98us => 0.32 V of lag, so the peak stays
        # far below the 25 V C513/C514/C517 rating. C0G for stable tau.
        ('C523', '100p 50V C0G OVP sense filter', 'DRIVE_OV_SENSE', 'PGND', ''),
    ]
    s.save(); g['sheets'].append(s)
    s = g['Sheet']('rail-passives', 'Rail partition passive networks - unqualified')
    for i, (ref, value, a, b, fp) in enumerate(parts):
        s.part(stock('Device', ref[0]), ref, value, 38.1 + (i % 5) * 76.2, 45.72 + (i // 5) * 33.02,
               {'1': a, '2': b}, fp)

    s.text('R519 0R keeps MAIN_PROVEN_IN low, so DRIVE_EN stays low: both delayed rails are OFF by construction.', 20.32, 271.78)
    s.text('U501 PGOOD drives DRIVE_PG only: the always-on ANALOG_OK chain is no longer gated by a delayed rail.', 20.32, 279.4)
    s.save()
    g['sheets'].append(s)
