# Active entry — first physical switching slice

**UNREVIEWED DRAFT; NO ENERGIZE / NO PURCHASE / NO PCB / NO RIDING.**
This is an intentionally inhibited component-level slice, NOT completed protected entry.

## Integration

Legibility d07fcbf was merged onto fb100ef as 38d036b2554979bdd5c90d53f08a82750edac0fd.
Presentation-only source diff changes label/field positions, not connectivity. Independent
native XML comparison reproduced 314 parts / 1007 ref-pin-net rows invariant; 34 normal
baseline tests passed. FSR presentation regression remains in the full current suite.
Budget, power-source, MAIN_PROVEN and budget-review documents are preserved unchanged.

## Actual circuit delta

- J41 and J42 passive bypass connectors are REMOVED, not retained in parallel.
- R116 is now the 22 ohm +/-1% RH05022R00FE02 **unqualified pulse candidate**.
- MAIN: ENTRY_FUSED → Q400 drain; Q400/Q401 sources join MAIN_SOURCE;
  Q401 drain → BUS_SHUNT_HI. Existing R117 shunt continues to DC_LINK.
- PRE: ENTRY_FUSED → Q402 drain; Q402/Q403 sources join PRE_SOURCE;
  Q403 drain → PRECHARGE_R → R116 → BUS_SHUNT_HI.
- Four IRFP4568PbF 150 V candidate MOSFETs use G=1, D=2, S=3 stock GDS
  symbol and candidate TO-247-3 footprint. Thermal tab is drain; mounting isolation,
  SOA, gate-transient protection and clamp coordination remain unqualified.
- U400/U401 TPSI3052DWZR: 1 EN, 2 PXFR, 3 CTRL3V3, 4 PGND,
  5 floating common source, 6 VDDM, 7 VDDH, 8 VDRV. Separate 10 ohm gate
  resistors and 100k gate-source pulldowns. PXFR=20k 1%; primary bypass 1uF
  with >=0.22uF effective requirement. Split secondary capacitors 100nF and
  470nF C0G 5%: worst ratio 4.25 >3. Exact capacitor order codes remain open.
- Both EN pins have 10k pulldowns **and fitted fixed 0-ohm inhibit to PGND**.
  There is no command connector and no firmware dependency for this inhibition.
  These resistors are NOT hot jumpers; no instruction to remove/bypass them is authorized.

## Verified sources and evidence limits

TI TPSI3052 SLVSGS3B Table 5-1 and §6.3 downloaded directly from
https://www.ti.com/lit/ds/symlink/tpsi3052.pdf and checked as PDF text.
IR/Infineon IRFP4568PbF PD-96175 manufacturer-authored sheet fetched from distributor
https://docs.rs-online.com/b22f/0900766b8154410c.pdf (G,D,S ordering, 150V).
No alternate manufacturer's similarly named device was substituted.

TPSI secondary supplies are floating; no false PGND tie or PWR_FLAG was added.
Three extra honest ERC errors are CTRL3V3 undriven and both floating source references.
The CTRL rail **has no supply in this slice**. No gate timing, power consumption,
reverse-fault survival or operational driver performance is proven.

## Executed checks

`exports/active-entry-red.txt` records two failing old-topology assertions and one missing
new-component error before implementation (not three behavioral failures).
Native KiCad generation/export produced **29 pages, 338 components, 198 connected nets,
1020 mapped connected endpoints, 51 NC endpoints**. Actual BOM, netlist, PDF and SVG
are checked in. Native XML `exports/active-entry.xml` is parsed independently in three
new tests, including exact driver pins, common sources and no passive bypass.
All **37 tests pass in normal and optimized Python**; logs are
`exports/active-entry-tests{,-O}.txt`. Full suite includes existing ngspice checks,
which do NOT simulate the new TPSI/MOSFET slice. No vendor-model simulation of this
slice was run. The precharge ideal solver still has explicit unimplemented gate-valid,
PM-quiet and diagnostic-current interfaces; it is not circuit evidence.
Strict ERC returns **5**, with **8 errors, 0 warnings**. All eight are retained in the
verifier; acceptance of their identity is not a waiver or release gate passing.

## Required next bounded circuit slices (not implemented here)

1. Protected ENTRY_FUSED branch → fuse → STTH1R02A → LM5164 CTRL3V3:
   exact RON, magnetics, ripple, biased capacitors and tolerance/startup closure.
   This requested buck was **not completed in this bounded slice**.
2. Separate always bus-powered SINK12/safety from delayed DRIVE12/MCU/external rails.
   Existing AUX12V still powers bridge VM and J5 still exposes SAFETY3V3: the
   requested load partition is **not implemented** and current schematic cannot
   claim the 1.1W precharge envelope. 1.1W is only the future sink allocation,
   NOT the whole board load; CTRL 0.8W is separately pack-fed. Efficiency >=60%,
   each driver <=50mA and startup <=2W/30ms are acceptance targets, not measurements.
3. Hardware reset-dominant state logic, absolute 300ms nominal/350ms maximum
   timeout, no hot retry, independently interrupting welded-PRE protection;
   actual 55J mounted hot resistor pulse and MOSFET SOA qualification.
4. MAIN_PROVEN analog/reference/clamps, floating gate feedback, diagnostic load
   and LOW→HIGH→LOW current detection; continuous window and post-proof settle.
   Independent PM/external injection **<=10mA measurement/interlock remains a blocker**.
   No detector was invented and no validity net tied true.
5. Audit backfeed, source/BMS, actual capacitance and clamp transients; independent
   schematic/PCB consultant and visual review before acceptance. No such cold-review
   verdict is claimed for this circuit commit. Parent owns review/publication decision.

This handoff deliberately stops before unbounded supply/sequencer work. It advances
physical topology but is not completion of the requested active-entry milestone.
