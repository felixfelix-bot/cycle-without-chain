#!/usr/bin/env python3
"""Build approved-mpns.json from the schematic BOM plus a curated MPN table.

WHY A GENERATOR RATHER THAN A HAND-WRITTEN JSON
-----------------------------------------------
The approved list must satisfy PCB-03's "exact reference-set equality", so it has
to be derived from the same source as the BOM. Hand-maintaining 387 entries
guarantees drift the first time a resistor is added.

The curated part is the *mapping* from a schematic value string to a purchasable
part, footprint and source. That mapping is where engineering judgement lives and
where it must be visible. Anything the table cannot resolve is emitted as an
explicit gap rather than a guess, so ``check_bom.py`` fails loudly instead of the
design quietly inheriting an invented part number.

VALUE STRING -> MPN RESOLUTION ORDER
------------------------------------
1. Exact value match in MPN_TABLE.
2. Prefix match on a normalised value, for families where the schematic value
   carries a tolerance/size but the MPN is shared (e.g. every "100k 1%" 0805 is
   the same CRCW0805100KFKEA).
3. Otherwise: unresolved, reported with the value string so a human can decide.

Nothing here invents a datasheet claim. Every mapping records where the part
number came from; "vendor-series" means the MPN follows the published
manufacturer series naming (resistor/capacitor size+tolerance families) and has
not been individually datasheet-audited for this design.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOM_CSV = HERE / "review-bom.csv"
OUT = HERE / "approved-mpns.json"

# Passive families already used consistently in this design. The series naming is
# the manufacturer's own (Vishay CRCW, Panasonic ERA, Murata GRM, TDK C series);
# these are not individual datasheet audits.
R_0805_TOL1 = "CRCW0805{}FKEA"       # Vishay CRCW 0805 1 %
R_0805_TOL1_PAN = "ERA-6AEB{}V"      # Panasonic ERA-6A 0.1 %
C_0805_25V = "GRM21BR71E{}KA01L"     # Murata 0805 25 V X7R
C_0805_16V = "GRM21BR61E{}KA73L"
C_0603_16V = "GRM188R61C{}KA93D"

# explicit, audited mappings: value string -> (mpn, footprint, source, kind)
MPN_TABLE: dict[str, tuple[str, str, str, str]] = {
    # --- power semiconductors already datasheet-audited ---------------
    "CSD19532Q5B": ("CSD19532Q5B", "Package_TO_SOT_SMD:TDSON-8-1",
                    "TI SLPS414 Rev. B", "datasheet"),
    "IPP023N10N5": ("IPP023N10N5AKSA1", "Package_TO_SOT_SMD:TO-263-3_TabPin2",
                    "Infineon unverified - see register", "unverified"),
    "DRV8353SRTAT": ("DRV8353SRTAT", "Package_DFN_QFN:QFN-40-1EP_6x6mm_P0.5mm_EP4.6x4.6mm",
                     "TI SLVSDY6A pp6-7", "datasheet"),
    "DRV8353": ("DRV8353SRTAT", "Package_DFN_QFN:QFN-40-1EP_6x6mm_P0.5mm_EP4.6x4.6mm",
                "TI SLVSDY6A pp6-7", "datasheet"),
    # --- inductors -----------------------------------------------------
    "68u SPM10065VC-680M-D": ("SPM10065VC-680M-D",
                              "Powerboard:L_TDK_SPM10065VC-D",
                              "TDK catalogue 20250303 p3", "datasheet"),
    "3.9u candidate 2A": ("SRN6045TA-3R9M", "Inductor_SMD:L_Bourns_SRN6045TA",
                          "Bourns SRN6045TA series", "series"),
    "68u SPM10065VT-680M-D": ("SPM10065VC-680M-D",
                              "Powerboard:L_TDK_SPM10065VC-D",
                              "superseded by VC variant; TDK catalogue p3",
                              "datasheet"),
    # --- reference / regulator / supervisor ----------------------------
    "LM4040AIM3-2.5/NOPB": ("LM4040AIM3-2.5/NOPB", "Package_TO_SOT_SMD:SOT-23",
                            "TI lm4040-n A grade", "datasheet"),
    "TLV76033DBZR": ("TLV76033DBZR", "Package_TO_SOT_SMD:SOT-23",
                     "TI tlv760", "datasheet"),
    "LM5164DDAR": ("LM5164DDAR", "Package_SO:HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm",
                   "TI LM5164", "datasheet"),
    "TPS3823-33DBVR": ("TPS3823-33DBVR", "Package_TO_SOT_SMD:SOT-23-5",
                       "TI tps3823", "datasheet"),
    # --- logic, already pin-audited ------------------------------------
    "LM339BIDR": ("LM339BIDR", "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm",
                  "TI lm339b §6.7", "datasheet"),
    "SN74LVC1G74DCUR": ("SN74LVC1G74DCUR", "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
                        "TI SCES470F", "datasheet"),
    "SN74LVC3G17DCUR": ("SN74LVC3G17DCUR", "Package_SO:VSSOP-8_2.3x2mm_P0.5mm",
                        "TI SCES470F, VT- 0.84 V min @3 V", "datasheet"),
    "SN74LVC1G11DBVR": ("SN74LVC1G11DBVR", "Package_TO_SOT_SMD:SOT-23-6",
                        "TI SCES487I, VIH 2 V / VIL 0.8 V @3 V", "datasheet"),
    "SN74LVC1G04DBVR": ("SN74LVC1G04DBVR", "Package_TO_SOT_SMD:SOT-23-5",
                        "TI SN74LVC1G04", "datasheet"),
    "SN74LVC1G32DBVR": ("SN74LVC1G32DBVR", "Package_TO_SOT_SMD:SOT-23-5",
                        "TI SN74LVC1G32", "datasheet"),
    "SN74LVC1G08DBVR": ("SN74LVC1G08DBVR", "Package_TO_SOT_SMD:SOT-23-5",
                        "TI SN74LVC1G08", "datasheet"),
    "UCC27511DBVR": ("UCC27511DBVR", "Package_TO_SOT_SMD:SOT-23-6",
                     "TI ucc27511, VIN_L 1.0-1.2 V", "datasheet"),
    "TLV1701AIDBVR": ("TLV1701AIDBVR", "Package_TO_SOT_SMD:SOT-23-5",
                      "TI SBOS589D", "datasheet"),
}

# value prefix -> (mpn template, footprint, source, kind)
MPN_PREFIX: list[tuple[str, tuple[str, str, str, str]]] = [
    # 2 mΩ 2512 current shunts
    ("2m 1% 3W", ("WSLP25123L000FEA", "Resistor_SMD:R_2512_6332Metric",
                  "Vishay WSLP2512 series", "series")),
    # generic 0805 1 % resistors: value "NNNk 1%", "NNNR 1%", "NNk"
    ("4k7 1%", ("CRCW08054K70FKEA", "Resistor_SMD:R_0805_2012Metric",
                "Vishay CRCW 0805 1 %", "series")),
    ("1k 1%", ("CRCW08051K00FKEA", "Resistor_SMD:R_0805_2012Metric",
               "Vishay CRCW 0805 1 %", "series")),
    ("100k 1%", ("CRCW0805100KFKEA", "Resistor_SMD:R_0805_2012Metric",
                 "Vishay CRCW 0805 1 %", "series")),
    ("10k 1%", ("CRCW080510K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                "Vishay CRCW 0805 1 %", "series")),
    ("47k 1%", ("CRCW080547K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                "Vishay CRCW 0805 1 %", "series")),
    ("649k 0.1%", ("ERA-6AEB6493V", "Resistor_SMD:R_0805_2012Metric",
                   "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("118k 0.1%", ("ERA-6AEB1183V", "Resistor_SMD:R_0805_2012Metric",
                   "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("112k 0.1%", ("ERA-6AEB1123V", "Resistor_SMD:R_0805_2012Metric",
                   "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("113k 0.1%", ("ERA-6AEB1133V", "Resistor_SMD:R_0805_2012Metric",
                   "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("330k 0.1%", ("ERA-6AEB334V", "Resistor_SMD:R_0805_2012Metric",
                   "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("10k 0.1%", ("ERA-6AEB103V", "Resistor_SMD:R_0805_2012Metric",
                  "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("30k 0.1%", ("ERA-6AEB303V", "Resistor_SMD:R_0805_2012Metric",
                  "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("2k 0.1%", ("ERA-6AEB202V", "Resistor_SMD:R_0805_2012Metric",
                 "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("453k 1%", ("CRCW0805453KFKEA", "Resistor_SMD:R_0805_2012Metric",
                 "Vishay CRCW 0805 1 %", "series")),
    ("49.9k 1%", ("RG1608P-4992-B-T5", "Resistor_SMD:R_0603_1608Metric",
                  "Susumu RG1608P 0.1 %", "series")),
    ("82k 1%", ("CRCW080582K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                "Vishay CRCW 0805 1 %", "series")),
    ("20k 1%", ("CRCW080520K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                "Vishay CRCW 0805 1 %", "series")),
    ("10R 1%", ("CRCW080510R0FKEA", "Resistor_SMD:R_0805_2012Metric",
                "Vishay CRCW 0805 1 %", "series")),
    # RAIL-10: gate resistors sized by size_gate_resistors.py rather than
    # defaulted. 3R3 chosen over 2R2 because 2R2 sits only 1.25 % above the
    # DRV8353 current-limit crossover and so does not control the edge at all.
    # See docs/design/bom-identity-and-gate-sizing.md §3.
    ("3R3 1% gate", ("CRCW08053R30FKEA", "Resistor_SMD:R_0805_2012Metric",
                     "Vishay CRCW 0805 1 % (sized: 3.3 ohm, 60 ns edge)",
                     "series")),
    # cleaned value strings (qualifier removed after the part was decided)
    ("IRFP4568PbF 150V", ("IRFP4568PBF", "Package_TO_SOT_THT:TO-247-3_Vertical",
                          "Infineon IRFP4568 150 V (dump FET)", "series")),
    ("3.9u 2A", ("SRN6045TA-3R9M", "Inductor_SMD:L_Bourns_SRN6045TA",
                  "Bourns SRN6045TA series", "series")),
    ("KLKD020CN 20A 600VDC", ("KLKD020.T", "Fuse:Fuseholder_Littelfuse_100_series_5x20mm",
                               "Littelfuse KLKD 20 A 600 VDC", "series")),
    ("330p 50V C0G 5%", ("GRM2165C1H331JA01D", "Capacitor_SMD:C_0805_2012Metric",
                         "Murata GRM216 C0G 50 V", "series")),
    ("56p 50V C0G", ("GRM2165C1H560JA01D", "Capacitor_SMD:C_0805_2012Metric",
                     "Murata GRM216 C0G 50 V", "series")),
    ("10u 25V X7R", ("GRM21BR61E106KA73L", "Capacitor_SMD:C_0805_2012Metric",
                     "Murata GRM21BR61E 25 V X7R", "series")),
    ("22u 16V X7R", ("GRM31CR61C226KA93L", "Capacitor_SMD:C_1206_3216Metric",
                     "Murata GRM31CR61C 25 V X7R", "series")),
    ("100u 100V", ("UHE2A101MPD", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
                   "Nichicon UHE 100 V 100 uF", "series")),
    ("27.4k 1% 0.1W", ("CRCW080527K4FKEA", "Resistor_SMD:R_0805_2012Metric",
                       "Vishay CRCW 0805 1 %", "series")),
    ("87.3k 1% 0.1W", ("CRCW080587K6FKEA", "Resistor_SMD:R_0805_2012Metric",
                       "Vishay CRCW 0805 1 % (87k6 nearest E96)", "series")),
    ("150k 1% 0.1W >=100V", ("CRCW0805150KFKEA", "Resistor_SMD:R_0805_2012Metric",
                             "Vishay CRCW 0805 1 % 150 k", "series")),
    ("1M 1% 0.1W >=100V", ("CRCW08051M00FKEA", "Resistor_SMD:R_0805_2012Metric",
                           "Vishay CRCW 0805 1 % 1 M", "series")),
    ("52.3k 1% 0.1W", ("CRCW080552K3FKEA", "Resistor_SMD:R_0805_2012Metric",
                       "Vishay CRCW 0805 1 %", "series")),
    ("82k 1% 0.1W >=100V", ("CRCW080582K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                            "Vishay CRCW 0805 1 %", "series")),
    ("4R7 provisional", ("CRCW12064R70FKEA", "Resistor_SMD:R_1206_3216Metric",
                         "Vishay CRCW 1206 1 %", "series")),
    ("100k 1% G-S", ("CRCW0805100KFKEA", "Resistor_SMD:R_0805_2012Metric",
                     "Vishay CRCW 0805 1 %", "series")),
    ("4R7 provisional", ("CRCW12064R70FKEA", "Resistor_SMD:R_1206_3216Metric",
                         "Vishay CRCW 1206 1 % (gate resistor pending)",
                         "series")),
    # capacitors with a named part already
    ("3.3u 100V GRM32", ("GRM32ER72A335KA35L", "Capacitor_SMD:C_1210_3225Metric",
                        "Murata GRM32 100 V X7R", "datasheet")),
    ("10u 25V GRM21BR61E106KA73L", ("GRM21BR61E106KA73L",
                                    "Capacitor_SMD:C_0805_2012Metric",
                                    "Murata GRM21BR61E", "datasheet")),
    ("1u 25V GRM21BR71E105KA99L", ("GRM21BR71E105KA99L",
                                   "Capacitor_SMD:C_0805_2012Metric",
                                   "Murata GRM21BR71E", "datasheet")),
    ("470u 100V UHE2A471MHD", ("UHE2A471MHD", "Capacitor_THT:CP_Radial_D16.0mm_P7.50mm",
                               "Nichicon UHE 100 V", "series")),
    ("22u 25V TMK325B7226KMHT", ("TMK325B7226KMHT", "Capacitor_SMD:C_1210_3225Metric",
                                 "Taiyo Yuden TMK325 25 V X7R", "series")),
    ("2.2u 200V X7R 22252C225KAT2A", ("22252C225KAT2A",
                                      "Capacitor_SMD:C_2225_5664Metric",
                                      "AVX 2225 200 V X7R", "series")),
    # generic ceramics
    ("100n 25V X7R", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                      "Murata GRM21BR71E 25 V X7R", "series")),
    ("1u 16V X7R", ("GRM21BR61C105KA12L", "Capacitor_SMD:C_0805_2012Metric",
                    "Murata GRM21BR61C 16 V X7R", "series")),
    ("1u 100V X7R", ("GRM21BR72A105KA01L", "Capacitor_SMD:C_0805_2012Metric",
                     "Murata GRM21BR72A 100 V X7R", "series")),
    ("47n 100V X7R", ("GRM21BR72A473KA01L", "Capacitor_SMD:C_0805_2012Metric",
                      "Murata GRM21BR72A 100 V X7R", "series")),
    ("100n 25V", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                  "Murata GRM21BR71E 25 V X7R", "series")),
    ("10u 25V X7R", ("GRM21BR61E106KA73L", "Capacitor_SMD:C_0805_2012Metric",
                     "Murata GRM21BR61E 25 V X7R", "series")),
    ("22u 16V X7R", ("GRM31CR61C226KA93L", "Capacitor_SMD:C_1206_3216Metric",
                     "Murata GRM31CR61C 25 V X7R", "series")),
    ("1u 10V X7R", ("GRM185R61A105KA61D", "Capacitor_SMD:C_0603_1608Metric",
                    "Murata GRM185R61A 10 V X7R", "series")),
    ("100n 10V X7R", ("GRM188R61A104KA93D", "Capacitor_SMD:C_0603_1608Metric",
                      "Murata GRM188R61A 10 V X7R", "series")),
    ("100p 50V C0G", ("GRM2165C1H101JA01D", "Capacitor_SMD:C_0805_2012Metric",
                      "Murata GRM216 C0G 50 V", "series")),
    ("3.3n 100V", ("CGA3E2X7R2A332K080AA", "Capacitor_SMD:C_0603_1608Metric",
                   "TDK CGA3E2 100 V X7R", "series")),
    ("2.2n 50V", ("GCM155R71H222KA37D", "Capacitor_SMD:C_0402_1005Metric",
                  "Murata GCM155 50 V X7R", "series")),
    ("56p 50V C0G", ("GRM2165C1H560JA01D", "Capacitor_SMD:C_0805_2012Metric",
                     "Murata GRM216 C0G 50 V", "series")),
    ("10n 5% C0G", ("GRM2165C1H103JA01D", "Capacitor_SMD:C_0805_2012Metric",
                    "Murata GRM216 C0G 50 V", "series")),
    ("100p C0G", ("GRM2165C1H101JA01D", "Capacitor_SMD:C_0805_2012Metric",
                  "Murata GRM216 C0G 50 V", "series")),
    ("100n 25V GRM21BR71E104KA01L", ("GRM21BR71E104KA01L",
                                     "Capacitor_SMD:C_0805_2012Metric",
                                     "Murata GRM21BR71E", "datasheet")),
    # --- diodes --------------------------------------------------------
    ("BAT54S", ("BAT54S-7-F", "Package_TO_SOT_SMD:SOT-23",
                "Diodes Inc BAT54S", "series")),
    ("BAT54WS", ("BAT54WS-7-F", "Package_TO_SOT_SMD:SOD-323",
                 "Diodes Inc BAT54WS", "series")),
    ("PESD3V3U1UL", ("PESD3V3U1UL,315", "Diode_SMD:D_SOD-882",
                     "Nexperia PESD3V3U1UL", "series")),
    # --- connectors / protection ---------------------------------------
    ("KLKD020CN", ("KLKD020.T", "Fuse:Fuseholder_Littelfuse_100_series_5x20mm",
                   "Littelfuse KLKD 20 A 600 VDC", "series")),
    # --- generic resistors: bare value, default 0805 1 % ---------------
    ("100k G-S", ("CRCW0805100KFKEA", "Resistor_SMD:R_0805_2012Metric",
                  "Vishay CRCW 0805 1 % (gate-source pulldown)", "series")),
    ("10k Hall pullup", ("CRCW080510K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                         "Vishay CRCW 0805 1 %", "series")),
    ("1k Hall series", ("CRCW08051K00FKEA", "Resistor_SMD:R_0805_2012Metric",
                        "Vishay CRCW 0805 1 %", "series")),
    ("10k encoder pullup", ("CRCW080510K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                            "Vishay CRCW 0805 1 %", "series")),
    ("1k encoder series", ("CRCW08051K00FKEA", "Resistor_SMD:R_0805_2012Metric",
                           "Vishay CRCW 0805 1 %", "series")),
    ("100R 1%", ("CRCW0805100RFKEA", "Resistor_SMD:R_0805_2012Metric",
                 "Vishay CRCW 0805 1 %", "series")),
    ("28k7 0.1%", ("ERA-6AEB2872V", "Resistor_SMD:R_0805_2012Metric",
                   "Panasonic ERA-6A 0.1 % 25 ppm/K", "series")),
    ("0R analog supply link", ("CRCW08050000Z0EA", "Resistor_SMD:R_0805_2012Metric",
                               "Vishay CRCW 0805 0R jumper", "series")),
    # --- generic capacitors: bare value, default 0805 X7R --------------
    ("1n Hall filter", ("GRM216R71H102KA01D", "Capacitor_SMD:C_0805_2012Metric",
                        "Murata GRM216 50 V X7R", "series")),
    ("1n C0G", ("GRM2165C1H102JA01D", "Capacitor_SMD:C_0805_2012Metric",
                "Murata GRM216 C0G 50 V", "series")),
    ("1n encoder filter", ("GRM216R71H102KA01D", "Capacitor_SMD:C_0805_2012Metric",
                           "Murata GRM216 50 V X7R", "series")),
    ("10n ADC filter", ("GRM216R71H103KA01D", "Capacitor_SMD:C_0805_2012Metric",
                        "Murata GRM216 50 V X7R", "series")),
    ("100n FSR sense", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                        "Murata GRM21BR71E 25 V X7R", "series")),
    ("100n OPA bypass", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                         "Murata GRM21BR71E 25 V X7R", "series")),
    ("100n X7R 25V", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                      "Murata GRM21BR71E 25 V X7R", "series")),
    # --- additional ICs used on the analog / FSR sheets ----------------
    ("2N7002", ("2N7002K-T1-GE3", "Package_TO_SOT_SMD:SOT-23",
                "Vishay 2N7002K", "series")),
    ("TLV3202IDR", ("TLV3202AIDR", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                    "TI TLV3202 40 ns comparator", "series")),
    ("OPA333AIDBVR", ("OPA333AIDBVR", "Package_TO_SOT_SMD:SOT-23-5",
                      "TI OPA333 zero-drift", "series")),
    ("TMUX1511PWR", ("TMUX1511PWR", "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
                     "TI TMUX1511 4x SPST, §5.5 37 uA typ", "datasheet")),
    ("IRFP4568PbF 150V candidate", ("IRFP4568PBF", "Package_TO_SOT_THT:TO-247-3_Vertical",
                                    "Infineon IRFP4568 150 V (dump FET candidate)",
                                    "series")),
    # --- remaining generic passives (bare value, documented default) ---
    ("10k", ("CRCW080510K0FKEA", "Resistor_SMD:R_0805_2012Metric",
             "Vishay CRCW 0805 1 %", "series")),
    ("100k", ("CRCW0805100KFKEA", "Resistor_SMD:R_0805_2012Metric",
              "Vishay CRCW 0805 1 %", "series")),
    ("100k CRCW0805100KFKEA", ("CRCW0805100KFKEA", "Resistor_SMD:R_0805_2012Metric",
                               "Vishay CRCW 0805 1 %", "series")),
    ("10k CRCW080510K0FKEA", ("CRCW080510K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                              "Vishay CRCW 0805 1 %", "series")),
    ("10R CRCW080510R0FKEA", ("CRCW080510R0FKEA", "Resistor_SMD:R_0805_2012Metric",
                              "Vishay CRCW 0805 1 %", "series")),
    ("2R2 CRCW08052R20FKEA", ("CRCW08052R20FKEA", "Resistor_SMD:R_0805_2012Metric",
                              "Vishay CRCW 0805 1 %", "series")),
    ("100k enable default off", ("CRCW0805100KFKEA", "Resistor_SMD:R_0805_2012Metric",
                                 "Vishay CRCW 0805 1 %", "series")),
    ("10k EN default OFF", ("CRCW080510K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                            "Vishay CRCW 0805 1 %", "series")),
    ("10k NRST", ("CRCW080510K0FKEA", "Resistor_SMD:R_0805_2012Metric",
                  "Vishay CRCW 0805 1 %", "series")),
    ("0R FIXED INHIBIT", ("CRCW08050000Z0EA", "Resistor_SMD:R_0805_2012Metric",
                          "Vishay CRCW 0805 0R jumper", "series")),
    ("100n ADC reservoir", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                            "Murata GRM21BR71E 25 V X7R", "series")),
    ("100n mux bypass", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                         "Murata GRM21BR71E 25 V X7R", "series")),
    ("100n NRST", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                   "Murata GRM21BR71E 25 V X7R", "series")),
    ("470n 25V C0G 5%", ("GRM21B5C1H474JA01L", "Capacitor_SMD:C_0805_2012Metric",
                         "Murata GRM21B C0G 50 V", "series")),
    ("100u 100V provisional", ("UHE2A101MPD", "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
                               "Nichicon UHE 100 V 100 uF", "series")),
    # --- remaining ICs --------------------------------------------------
    ("TPSI3052DWZR", ("TPSI3052DWZR", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm",
                      "TI TPSI3052DWZR isolated driver, 8-pin SOIC", "datasheet")),
    ("STM32G474VET6", ("STM32G474VET6", "Package_QFP:LQFP-100_14x14mm_P0.5mm",
                       "ST STM32G474VE", "datasheet")),
    ("R-78HB12-0.5", ("R-78HB12-0.5", "Converter_DCDC:Converter_DCDC_RECOM_R-78HB-0.5_THT",
                      "RECOM R-78HB12-0.5, 17-72 V in", "datasheet")),
    # --- connectors, switches and harness parts ------------------------
    # The schematic uses the VALUE field to carry a net description for these,
    # so each needs an explicit physical part choice.
    ("Anderson 992G1 SB50", ("992G1-BK", "Connector_PinHeader_2.54mm:PinHeader_1x01_P2.54mm_Vertical",
                             "Anderson Powerpole SB50 housing, keyed",
                             "series")),
    ("EXTERNAL_DUMP_RESISTOR", ("HSC3004R7J", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
                                "TE HSC300 4R7 300 W (external, off-board)",
                                "series")),
    ("Kelvin BUS measurement", ("Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                                "2-pin header, instrument Kelvin pair", "series")),
    ("GEN_MACHINE_PHASES", ("Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
                            "3-pin phase header", "series")),
    ("HUB_MACHINE_PHASES", ("Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
                            "3-pin phase header", "series")),
    ("GEN_HALL_3V3_ONLY", ("Conn_01x05", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
                           "5-pin Hall header", "series")),
    ("HUB_HALL_3V3_ONLY", ("Conn_01x05", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
                           "5-pin Hall header", "series")),
    ("OPTIONAL_ENCODER_3V3_ONLY", ("Conn_01x05", "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
                                   "5-pin encoder header", "series")),
    ("BUS_TEST_ONLY_NOT_SOURCE_INPUT", ("Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                                        "2-pin bench bus input", "series")),
    ("MCU_RAIL_TEST_ONLY_NOT_INPUT", ("Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                                      "2-pin MCU rail test point", "series")),
    ("SAFETY_FAULT_CHAIN_NC", ("Conn_01x02", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                               "2-pin NC fault-chain link", "series")),
    ("SWD_3V3_TARGET_REFERENCE", ("Conn_01x06", "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
                                  "6-pin SWD header", "series")),
    ("NC_RELEASE_OPEN_ON_BRAKE_UNSELECTED", ("TL3305AF160QG", "Button_Switch_SMD:SW_SPST_TL3305A",
                                             "E-Switch TL3305 tactile, NC wiring", "series")),
    ("RESET_BUTTON_NORMALLY_OPEN", ("TL3305AF160QG", "Button_Switch_SMD:SW_SPST_TL3305A",
                                    "E-Switch TL3305 tactile, NO wiring", "series")),
    # --- remaining specials --------------------------------------------
    ("4u7 10V X7R bulk", ("GRM21BR61A475KA73L", "Capacitor_SMD:C_0805_2012Metric",
                          "Murata GRM21BR61A 10 V X7R", "series")),
    ("1n brake filter", ("GRM216R71H102KA01D", "Capacitor_SMD:C_0805_2012Metric",
                         "Murata GRM216 50 V X7R", "series")),
    ("22R 1% RH05022R00FE02 pulse UNQUALIFIED",
     ("RH05022R00FE02", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal",
      "Vishay RH050 22R 1 % - PULSE RATING NOT QUALIFIED (PROT-09)", "series")),
    ("2m 1% WSLP2512R0020FEA Kelvin",
     ("WSLP2512R0020FEA", "Resistor_SMD:R_2512_6332Metric",
      "Vishay WSLP2512 2 mOhm 1 % Kelvin", "series")),
    ("STPS30100ST reverse clamp ONLY not reverse blocker",
     ("STPS30100ST", "Package_TO_SOT_SMD:TO-277A",
      "ST STPS30100 100 V Schottky (clamp only)", "series")),
    ("LEFT_BINARY_SWITCH_ONLY", ("TL3305AF160QG", "Button_Switch_SMD:SW_SPST_TL3305A",
                                 "E-Switch TL3305 tactile, binary left", "series")),
    ("RIGHT_BINARY_SWITCH_ONLY", ("TL3305AF160QG", "Button_Switch_SMD:SW_SPST_TL3305A",
                                  "E-Switch TL3305 tactile, binary right", "series")),
    ("100n AND decoupling", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                             "Murata GRM21BR71E 25 V X7R", "series")),
    ("100n OR decoupling", ("GRM21BR71E104KA01L", "Capacitor_SMD:C_0805_2012Metric",
                            "Murata GRM21BR71E 25 V X7R", "series")),
    ("LEFT_FSR_34-00018_EXTERNAL", ("34-00018", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                                    "Interlink FSR 34-00018 (external pad)", "series")),
    ("RIGHT_FSR_34-00018_EXTERNAL", ("34-00018", "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
                                     "Interlink FSR 34-00018 (external pad)", "series")),
    # Named parts whose value string carries a qualifier
    ("S1J-E3/61T 600V 1A", ("S1J-E3/61T", "Diode_SMD:D_SMA",
                            "Vishay S1J 600 V 1 A", "series")),
    ("68u MSS1246T-683MLC 20%", ("MSS1246T-683MLC", "Inductor_SMD:L_Coilcraft_MSS1246T-XXX",
                                 "Coilcraft MSS1246T 68 uH (L500, RAIL-03 open)",
                                 "series")),
    ("330p 50V C0G 5% candidate", ("GRM2165C1H331JA01D", "Capacitor_SMD:C_0805_2012Metric",
                                   "Murata GRM216 C0G 50 V", "series")),
    ("27.4k 1% 0.1W candidate", ("CRCW080527K4FKEA", "Resistor_SMD:R_0805_2012Metric",
                                 "Vishay CRCW 0805 1 %", "series")),
    ("87.3k 1% 0.1W candidate", ("CRCW080587K6FKEA", "Resistor_SMD:R_0805_2012Metric",
                                 "Vishay CRCW 0805 1 % (87k6 nearest E96)", "series")),
    ("150k 1% 0.1W >=100V", ("CRCW0805150KFKEA", "Resistor_SMD:R_0805_2012Metric",
                             "Vishay CRCW 0805 1 % 150 k", "series")),
    ("1M 1% 0.1W >=100V", ("CRCW08051M00FKEA", "Resistor_SMD:R_0805_2012Metric",
                           "Vishay CRCW 0805 1 % 1 M", "series")),
    ("52.3k 1% 0.1W candidate", ("CRCW080552K3FKEA", "Resistor_SMD:R_0805_2012Metric",
                                 "Vishay CRCW 0805 1 %", "series")),
    ("AP63203WU", ("AP63203WU-7", "Package_TO_SOT_SMD:TSOT-23-6",
                   "Diodes Inc AP63203 3.3 V 2 A sync buck", "datasheet")),
    ("68u SPM10065VC-680M-D 20% AEC-Q200",
     ("SPM10065VC-680M-D", "Powerboard:L_TDK_SPM10065VC-D",
      "TDK catalogue 20250303 p3 (VC variant, AEC-Q200)", "datasheet")),
]

# reference prefixes that are mechanical / not populated by the assembler
NON_ELECTRICAL = ("H", "MH", "TP")


def normalise(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


# Size-specific overrides: when the schematic already fixed a footprint smaller
# than the family default, the MPN must follow the *footprint*, not the table.
# Getting this backwards would put an 0805 land under a 0603 choice (or worse,
# quote a part that cannot be placed).
SIZE_OVERRIDE: dict[tuple[str, str], tuple[str, str, str]] = {
    # (value prefix, size token) -> (mpn, footprint, source)
    ("10k", "0603"): ("CRCW060310K0FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("100k", "0603"): ("CRCW0603100KFKEA", "Resistor_SMD:R_0603_1608Metric",
                       "Vishay CRCW 0603 1 %"),
    ("1k", "0603"): ("CRCW06031K00FKEA", "Resistor_SMD:R_0603_1608Metric",
                     "Vishay CRCW 0603 1 %"),
    ("0R", "0603"): ("CRCW06030000Z0EA", "Resistor_SMD:R_0603_1608Metric",
                     "Vishay CRCW 0603 0R jumper"),
    ("10R", "0603"): ("CRCW060310R0FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("100R", "0603"): ("CRCW0603100RFKEA", "Resistor_SMD:R_0603_1608Metric",
                       "Vishay CRCW 0603 1 %"),
    ("120R", "0603"): ("CRCW0603120RFKEA", "Resistor_SMD:R_0603_1608Metric",
                       "Vishay CRCW 0603 1 %"),
    ("22R", "0603"): ("CRCW060322R0FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("47R", "0603"): ("CRCW060347R0FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("1k5", "0603"): ("CRCW06031K50FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("2k2", "0603"): ("CRCW06032K20FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("4k7", "0603"): ("CRCW06034K70FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("47k", "0603"): ("CRCW060347K0FKEA", "Resistor_SMD:R_0603_1608Metric",
                      "Vishay CRCW 0603 1 %"),
    ("22p", "0603"): ("GRM1885C1H220JA01D", "Capacitor_SMD:C_0603_1608Metric",
                      "Murata GRM188 C0G 50 V"),
    ("47p", "0603"): ("GRM1885C1H470JA01D", "Capacitor_SMD:C_0603_1608Metric",
                      "Murata GRM188 C0G 50 V"),
    ("1n", "0603"): ("GRM1885C1H102JA01D", "Capacitor_SMD:C_0603_1608Metric",
                     "Murata GRM188 C0G 50 V"),
    ("2n2", "0603"): ("GRM188R71H222KA01D", "Capacitor_SMD:C_0603_1608Metric",
                      "Murata GRM188 50 V X7R"),
    ("100n", "0603"): ("GRM188R71E104KA01D", "Capacitor_SMD:C_0603_1608Metric",
                       "Murata GRM188R71E 25 V X7R"),
    ("1u", "0603"): ("GRM188R61C105KA12D", "Capacitor_SMD:C_0603_1608Metric",
                     "Murata GRM188R61C 16 V X7R"),
    ("4u7", "0603"): ("GRM188R60J475KE19D", "Capacitor_SMD:C_0603_1608Metric",
                      "Murata GRM188R60J 6.3 V X5R"),
    ("10n", "0603"): ("GRM188R71H103KA01D", "Capacitor_SMD:C_0603_1608Metric",
                      "Murata GRM188R71H 50 V X7R"),
}


def _size_of(footprint: str) -> str | None:
    for size in ("0201", "0402", "0603", "0805", "1206", "1210", "2512"):
        if size in (footprint or ""):
            return size
    return None


def resolve(value: str, footprint: str = "") -> tuple[str, str, str, str] | None:
    v = normalise(value)
    size = _size_of(footprint)
    if size:
        # Longest-prefix so "100R" cannot be shadowed by "10R".
        for prefix, sz in sorted(SIZE_OVERRIDE, key=lambda kv: len(kv[0]),
                                 reverse=True):
            if sz == size and v.startswith(prefix):
                mpn, fp, src = SIZE_OVERRIDE[(prefix, sz)]
                return (mpn, fp, src, "series")
        # Deliberately NOT a generic value->MPN derivation. An enumerated table
        # is auditable; a regex that mints part numbers is not, and it would
        # happily invent a CRCW code for a value no one checked exists. Unlisted
        # values fall through and are reported as unresolved instead.
    if v in MPN_TABLE:
        return MPN_TABLE[v]
    # Longest-prefix match, so a value that carries a stale qualifier still
    # resolves to the part the design already chose. E.g. "PESD3V3U1UL CANDIDATE"
    # and "4R7 provisional" resolve on the part stem rather than being treated as
    # unknown parts. Longest-first prevents "100k" from shadowing "100k 1%".
    for key in sorted(MPN_TABLE, key=len, reverse=True):
        if v.startswith(key):
            return MPN_TABLE[key]
    for prefix, entry in sorted(MPN_PREFIX, key=lambda kv: len(kv[0]), reverse=True):
        if v.startswith(prefix):
            return entry
    return None


def _reconcile(csv_fp: str, table_fp: str) -> str:
    """Decide between the schematic's footprint and the table's.

    Two different conflicts live here and they need opposite answers:

    * **The table is fixing a broken name.** The schematic says
      ``QFN-40-1EP_6x6mm_P0.5mm``, which does not exist in the KiCad library; the
      table says ``..._EP4.6x4.6mm``, which does. The table must win or ERC warns
      that the footprint cannot be found.

    * **The schematic is fixing the table.** The schematic deliberately chose a
      0603 part; the table defaulted to 0805. The schematic must win, or the MPN
      quoted would not fit the land.

    The rule that separates them: if both names refer to the *same* library and
    the table's name is a strict extension of the schematic's (the library
    prefix and shape stem match), the table is correcting a truncated name.
    Otherwise the schematic made a sizing decision, and the schematic wins.
    """
    a, b = (csv_fp or "").strip(), (table_fp or "").strip()
    if not a:
        return b
    if not b:
        return a
    if a == b:
        return a
    lib_a, _, stem_a = a.partition(":")
    lib_b, _, stem_b = b.partition(":")
    # same library, and the table's name extends the schematic's stem => the
    # schematic's name was truncated/incomplete and the table repaired it
    if lib_a == lib_b and stem_b.startswith(stem_a):
        return b
    return a


def build(bom_path: Path = BOM_CSV) -> dict:
    with bom_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    parts: dict[str, dict] = {}
    unresolved: list[dict] = []
    for row in rows:
        ref = row["reference"].strip()
        if not ref:
            continue
        value = normalise(row["value"])
        fp = (row.get("footprint") or "").strip()
        hit = resolve(value, fp)
        if hit is None:
            unresolved.append({"reference": ref, "value": value,
                               "footprint": fp, "sheet": row.get("sheet", "")})
            continue
        mpn, mpn_fp, source, kind = hit
        final_fp = _reconcile(fp, mpn_fp)
        if final_fp != mpn_fp:
            # The footprint that survived is not the one the table assumed, so
            # the part number must be re-resolved for the surviving size.
            again = resolve(value, final_fp)
            if again is not None:
                mpn, mpn_fp, source, kind = again
        parts[ref] = {
            "mpn": mpn,
            "footprint": final_fp,
            "source": source,
            "kind": kind,
            "value": value,
            "sheet": row.get("sheet", ""),
        }

    kinds = Counter(v["kind"] for v in parts.values())
    return {
        "generated_from": BOM_CSV.name,
        "note": ("Derived from the schematic BOM. 'datasheet' means the part "
                 "number was read from the named datasheet; 'series' means the "
                 "MPN follows the manufacturer's published series naming and has "
                 "NOT been individually audited for this design."),
        "counts": {
            "references": len(rows),
            "resolved": len(parts),
            "unresolved": len(unresolved),
            "by_kind": dict(kinds),
        },
        "unresolved": unresolved,
        "parts": dict(sorted(parts.items())),
    }


def main() -> int:
    result = build()
    OUT.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    c = result["counts"]
    print("references : %d" % c["references"])
    print("resolved   : %d" % c["resolved"])
    print("unresolved : %d" % c["unresolved"])
    print("by kind    : %s" % c["by_kind"])
    if result["unresolved"]:
        print("\nunresolved values (need an engineering decision):")
        seen = defaultdict(int)
        for u in result["unresolved"]:
            seen[u["value"]] += 1
        for value, n in sorted(seen.items(), key=lambda kv: -kv[1]):
            print("  x%-3d %s" % (n, value[:70]))
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
