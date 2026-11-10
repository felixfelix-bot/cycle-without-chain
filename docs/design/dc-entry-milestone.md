# DC entry circuit increment — bounded passive bench interface, NOT released protection

**NOT SAFE TO ENERGIZE the integrated motor drive.** This delivers a real 19th KiCad sheet, not a complete road-going protected entry. Automatic reverse blocking, interlocked main switching and BMS permissions remain unimplemented. Passive bench harness is the bounded scope; do not describe it as a finished battery protector.

## Implemented electrical path

SOURCE_POS → F1 source-terminal KLKD020CN → ENTRY_FUSED. Removable J41 main jumper goes to BUS_SHUNT_HI; parallel J42 precharge jumper goes through 100Ω RH050100R0FE02 to BUS_SHUNT_HI. A 2mΩ WSLP2512R0020FEA shunt joins DC_LINK. J43 carries high-side Kelvin taps and bus+/PGND for isolated external instrumentation, **not MCU ADC**. Two UHE2A471MHD 470µF100V capacitors supplement existing bus capacitors. Always-connected 10kΩ RH02510K00FE02 discharges the bus. D20 STPS30100ST (cathode bus, anode ground) is a reverse clamp candidate, NOT a reverse-series blocker or qualified crowbar. Main conductive path passes regen both ways; a series diode would lose this function.

J40/41/42 use Anderson SB50 992G1 housing candidate; contacts, cable gauge, fuse holder/enclosure and mechanical layout remain unselected. A removable plug is **not a DC load-break switch**. It must not be removed under current, particularly PM regeneration. J41 is a two-terminal jumper harness, not a battery connector wired positive/negative. Key/label it differently to prevent interchange. J1 renamed BUS_TEST_ONLY_NOT_SOURCE_INPUT; bypassing entry at J1 defeats the fuse/precharge.

## Source evidence and qualification limits

- [Littelfuse primary KLKD_CN data](https://littelfuse.com/assetdocs/klkd-cn-fuse-datasheet?assetguid=50681ca5-393b-4e53-b7a3-b3397a40ef11): KLKD020CN,20A,600Vac/Vdc, DC10kA under UL248-19 /50kA under UL248-14. Table gives average melting462A²s,total clearing1151A²s at20kA600VDC. These are specified conditions, NOT predicted clearing at58.4V. Unknown battery prospective fault current, wire withstand, low-current clearing, holder DC rating and D20 fuse coordination block release. Install physically at positive source terminal, not after an unprotected cable.
- [Nichicon UHE series](https://www.nichicon.co.jp/english/products/pdfs/e-he.pdf), candidate UHE2A471MHD:470µF±20%,100V. Ripple/ESR/lifetime versus actual PWM and hot enclosure remain unqualified; capacitance is not a15A ripple rating.
- [Vishay RH/NH30201](https://www.vishay.com/docs/30201/rhnh.pdf): RH050100R0FE02 nominal50W depends on specified chassis/heatsink, not free air. Peak34.1W and2.56J below are imposed requirements, NOT a demonstrated pulse/thermal acceptance. RH02510K00FE02 bleed sees0.341W at58.4V; wire insulation/touch temperatures still need review.
- [ST STPS30100S](https://www.st.com/resource/en/datasheet/stps30100s.pdf):100V30A Schottky family. Fault surge waveform and fuse I²t compatibility have NOT been established; this diode cannot make incorrect polarity safe with a battery. Passive keyed harness plus meter polarity check is an operating control, not reverse-polarity protection certification.
- [Anderson SB50](https://www.andersonpower.com/content/dam/ideal-anderson-power-dotcom/product-assets/default/data-sheets/ds-sb50.pdf): connector family candidate; do not infer loaded disconnect capability from insulation voltage/current rating.

## Calculations, actual behavioral run and sequence

Electrical screening remains36–58.4V,15A target only. No chemistry/large battery chosen. Use **1.5mF maximum verified assembled capacitance budget** including tolerances and all downstream loads (new nominal940µF plus existing100µF and ceramics). External additional capacitors invalidate numbers.

At58.4V: E=CV²/2=2.55792J; initial100Ω current0.584A; peak resistor power34.1056W; ideal no-load tau0.15s and to1V mismatch0.610s. Initial resistor pulse approximately capacitor energy, plus bleed/load energy. At15A shunt drop30mV and loss0.45W; this is calculation not current rating. Main bypass without precharge has I=ΔV/(ESR+wiring+contact), **unbounded until those impedances measured**, not0.584A.

10k bleed tau15s at budget;58.4→5V takes36.87s nominal, about37.24s with+1%R, assuming no source/PM/external feed. Bleed power0.341W. Wait at least45s then measure bus below5V; time alone is never proof. Open bleeder leaves stored energy indefinitely.

`entry_transient.cir` actual ngspice passive behavioral run includes10k bleed,1500µF and ideal switch. At0.99s bus57.748V, at39s (38s after source opening)4.585V. Peak source magnitude about0.584A. Not vendor models, not contact/fuse/reverse or thermal proof. The first current-measure expression failed because ngspice did not provide resistor branch current; changed to voltage-source branch current, not invented results.

Manual bench sequence: machines disconnected and physically stopped; source isolated, positive polarity measured, source voltage known; main open; entry precharge connected; measure difference<1V before installing main; remove precharge jumper after main continuity verified. **With auxiliary/logic operating loads the100Ω path may NEVER reach this condition**: available margin is only roughly(1V/100Ω−5.84mA bleed)=4.16mA. Therefore this sequence applies only to a passive isolated capacitor harness with other loads disconnected. The integrated drive needs a genuine load-inhibit/precharge-ready interlock circuit; not yet implemented. Do not energize to see if it works. For shutdown stop/disconnect machines before source, then verify discharge. No contactor opens on a fault in this increment; a future contactor must not sever the only sink during PM generation.

## Energy/interface FMEA and outstanding wiring

| Fault/state | Consequence | Required control / release status |
|---|---|---|
| Reverse source | D20 shorts source; fuse may not clear before damage | No guaranteed automatic protection; battery use blocked pending coordinated reverse isolation |
| J41 early/welded/bypassed | Unlimited capacitive inrush | Manual bench only; interlocked voltage-difference/main switching missing |
| J42 left closed / bus short | Continuous34W resistor at58.4V, thermal hazard | Timed disconnect/thermal cutoff missing; candidate pulse is not indefinite rating |
| BMS open/full/cold pack | No charge acceptance; PM still injects | Separate CHARGE_ALLOWED and DISCHARGE_ALLOWED interfaces required, neither wired; sink stays bus side |
| Supply loss/MCU crash | Gate kill does not stop diode generation; active chopper can lose control | Independent sink power/thermal/SOA qualification remains blocker; no safe disconnect claim |
| Bleeder open / PM turning | Bus remains charged | Meter verification and immobilization mandatory; no safe-time-only assumption |
| Kelvin instrument grounded wrongly | High-side shunt short / hazardous common mode | Isolated differential measurement only; production current amplifier/filter/protection not yet implemented |
| Normal brake request | Existing BRAKE_OK removes both gate enables, prevents controlled hub regen | **Architectural conflict**, not solved by this entry sheet |

Normal braking must eventually use redundant binary brake switches to inhibit positive propulsion plus a non-load-bearing Hall lever sensor for proportional request. Separate emergency/fault gate kill from normal request; do not just delete fault gating. DMS cable-force alternative needs calibration, drift/open/short plausibility and mechanical integrity review; never interrupt the safety-critical brake cable. Autonomous OV chopper remains independent of lever and is bus protection, not guaranteed braking torque. Mechanical brakes remain independently adequate.

Rider+luggage120kg is known; bike mass must be added. No actual descent supplied. External guarded ventilated dump-resistor heatsink requires temperature sensing/derating and sustained mgh/time sizing, not only stop energy; bicycle frame is NOT assumed heatsink. Existing two HSC3004R7J series form9.4Ω,383W at60V electrically, not600W assembly thermal rating; confirm series endpoints before any thermal release. Bare75W each vs300W on specified heatsink is not installed proof.100W initial qualification and300W600s are conditional study points, not ratings. Supply-loss sink and full-pack braking remain blocked.

Storage study remains unresolved small-buffer comparison. The cited16s LithiumWerks candidate charges57.6V,13sP28A54.6V;58.4V is conservative electrical envelope, NOT universal charge setpoint. Full/cold/BMS-open disposal and distinct charge/discharge permissions are mandatory. Optional external bidirectional converter has not been implemented. No inferred acceleration requirement or power uprating.

## Verification

Generated19 pages,257 parts,157 connected nets,808 connected endpoints,45 explicit NC. Exact manifest/export comparison plus fixed fuse/jumper/clamp/Kelvin topology tests. RED missing F1 preserved. Normal and optimized suites rerun after updating exact artifact counts; ERC remains precisely four undriven power errors U1.24,VREF; U1.25,AGND; U3.1,IN; U17.37,VDDA, no waiver. Cross-family approval unavailable. No PCB work. This is a coherent publishable **partial circuit**; complete protected-entry milestone remains blocked by the missing controls listed above.
