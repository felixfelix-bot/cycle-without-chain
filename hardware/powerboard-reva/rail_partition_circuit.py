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
                     ['PGND', 'DC_LINK', 'DRIVE_UVLO', 'DRIVE_RON', 'DRIVE_FB', 'ANALOG_OK',
                      'DRIVE_BST', 'DRIVE_SW', 'PGND'])))
    s.text('U501 is TI figure 7-1 (12 V/1 A/300 kHz) with RRON=100k and RFB1/RFB2=453k/49.9k. PGOOD sinks ANALOG_OK.', 20.32, 223.52)

    # --- MCU3V3: AP63203 fixed 3.3 V buck from DRIVE12 -------------------------
    ap = symbol(g, 'AP63203WU', ['FB', 'EN', 'VIN', 'GND', 'SW', 'BST'],
                ['input', 'input', 'power_in', 'power_in', 'power_out', 'passive'])
    s.part(ap, 'U502', 'AP63203WU', 254.0, 165.1,
           {'1': 'LOGIC3V3_EXT', '2': 'MCU3V3_EN', '3': 'DRIVE12', '4': 'PGND', '5': 'MCU_SW', '6': 'MCU_BST'},
           'Package_TO_SOT_SMD:TSOT-23-6')
    s.text('U502 pin map per Diodes TSOT26 table; FB tied to VOUT for the fixed 3.3 V variant.', 20.32, 231.14)

    parts = [
        # ref, value, net A, net B, footprint
        ('L501', '68u MSS1246T-683MLC 20%', 'DRIVE_SW', 'DRIVE12', ''),
        ('L502', '3.9u candidate 2A', 'MCU_SW', 'LOGIC3V3_EXT', 'Inductor_SMD:L_Bourns_SRN6045TA'),
        ('C510', '2.2u 200V X7R 22252C225KAT2A', 'DC_LINK', 'PGND', 'Capacitor_SMD:C_2225_5664Metric'),
        ('C511', '2.2u 200V X7R 22252C225KAT2A', 'DC_LINK', 'PGND', 'Capacitor_SMD:C_2225_5664Metric'),
        ('C512', '2.2n 50V GCM155R71H222KA37D', 'DRIVE_BST', 'DRIVE_SW', ''),
        ('C513', '22u 25V TMK325B7226KMHT', 'DRIVE12', 'PGND', ''),
        ('C514', '22u 25V TMK325B7226KMHT', 'DRIVE12', 'PGND', ''),
        ('C515', '3.3n 100V CGA3E2X7R2A332K080AA', 'DRIVE_RAMP', 'DRIVE12', ''),
        ('C516', '56p 50V C0G candidate', 'DRIVE_RAMP', 'DRIVE_FB', ''),
        ('C517', '10u 25V X7R candidate', 'DRIVE12', 'PGND', ''),
        ('C518', '22u 16V X7R candidate', 'LOGIC3V3_EXT', 'PGND', ''),
        ('C519', '22u 16V X7R candidate', 'LOGIC3V3_EXT', 'PGND', ''),
        ('C520', '100n 25V X7R', 'MCU_BST', 'MCU_SW', ''),
        ('C521', '100n 25V X7R', 'SAFETY3V3', 'PGND', ''),
        ('R510', '100k 1% 0.1W TI reference', 'DRIVE_RON', 'PGND', ''),
        ('R511', '453k 1% 0.1W TI reference', 'DRIVE12', 'DRIVE_FB', ''),
        ('R512', '49.9k 1% RG1608P-4992-B-T5', 'DRIVE_FB', 'PGND', ''),
        ('R513', '453k 1% 0.1W TI reference', 'DRIVE_SW', 'DRIVE_RAMP', ''),
        ('R514', '82k 1% 0.1W >=100V candidate', 'DRIVE_EN', 'DRIVE_UVLO', ''),
        ('R515', '100k 1% DELAY EN pulldown', 'DRIVE_UVLO', 'PGND', ''),
        ('R516', '47k 1% EN series', 'DRIVE_EN', 'MCU3V3_EN', ''),
        ('R517', '100k 1% DELAY EN pulldown', 'MCU3V3_EN', 'PGND', ''),
        ('R518', '100k 1% MAIN_PROVEN default low', 'MAIN_PROVEN_IN', 'PGND', ''),
        ('R519', '0R FIXED INHIBIT - no MAIN_PROVEN detector fitted', 'MAIN_PROVEN_IN', 'PGND', ''),
        ('R520', '10k CTRL PGOOD pullup', 'CTRL3V3', 'CTRL_PG', ''),
    ]
    s.save(); g['sheets'].append(s)
    s = g['Sheet']('rail-passives', 'Rail partition passive networks - unqualified')
    for i, (ref, value, a, b, fp) in enumerate(parts):
        s.part(stock('Device', ref[0]), ref, value, 38.1 + (i % 5) * 76.2, 45.72 + (i // 5) * 33.02,
               {'1': a, '2': b}, fp)

    s.text('R519 0R keeps MAIN_PROVEN_IN low, so DRIVE_EN stays low: both delayed rails are OFF by construction.', 20.32, 271.78)
    s.text('PGOOD feeds ANALOG_OK; no sequencing timer claimed. Fitted R402/R412 inhibits unchanged.', 20.32, 279.4)
    s.save()
    g['sheets'].append(s)
