# Independent raw-CSA overcurrent circuit milestone — UNSAFE partial design

Base `30560f6a9f54788365362db412c66c81e60d009b`; branch `pr/fast-oc`. No PCB, routing, fabrication, energization or riding authorization. This is a real component/connectivity increment, **not a qualified short-circuit protector**.

## Implemented circuit

Three new KiCad sheets implement U18–U23 TLV3202IDR: twelve comparisons on six raw GEN/HUB SOA/B/C outputs, before ADC RC filters. Each comparator output drives its own Q14–Q25 2N7002 gate; sources PGND, drains shared OC_OK. Separate FETs avoid shorting push-pull comparator outputs. OC_OK has 4.7k to SAFETY3V3 and replaces the former high tie at U14.6. This physically reaches HEALTHY, both U7/U8 asynchronous clears, U16 inhibit, both bridge ENABLE branches and **both U17 timer-break pins 46/84 on the same TIMER_BREAK_OK net**. MCU stuck-high ARM cannot override a low HEALTHY.

Actual comparator supply is **LOGIC3V3_EXT**, not the SAFETY3V3 candidate in the source consultant report. This keeps nominal input range aligned to DRV VREF and avoids intentionally powering comparators from a different nominal 3.3V rail. It does not prove power-off injection safe. The source report is historical candidate analysis; this document and exported netlist describe implementation. Comparator local decouplers are 100nF. Divider references are 28.7k/10k and 10k/28.7k, 0.1%, from actual DRV VREF rail, without added filtering or PWM blanking.

2N7002 primary pin evidence: [Nexperia Rev7 datasheet](https://assets.nexperia.com/documents/data-sheet/2N7002.pdf), Table2: gate1/source2/drain3. Its datasheet on-resistance specification at higher VGS is **not a guaranteed 3.3V loaded sink qualification**. Nominal OC_OK sink current is only 3.3/4700=0.702mA, but worst-temperature sink VOL, gate drive, aggregate drain capacitance and propagation remain explicit electrical-review blockers. The SPICE 10-ohm sink is an IDEAL abstraction, not that guarantee.

## Threshold, polarity and coverage

[Primary-source analysis and extracted evidence](fast-oc-source-analysis.md) covers exact comparator pins, DRV sign, timing tables, configuration fields, tolerance screen and inductance sensitivity. Critical correction: positive SP-to-SN current **decreases** SO: `I=(VREF/2−VSO)/(gain*Rshunt)`. Lower comparator therefore detects positive current; upper detects reverse current.

At 3.3V, gain20 and 2mΩ: references 0.8527131783/2.4472868217V imply ±19.93217A nominal. Provisional ±30A measurement gives SO=0.45…2.85V, inside DRV specified linear range 0.25…3.05V at nominal supply. Proposed **10A absolute commissioning operating cap** stays below the illustrative 16.926…23.084A tolerance screen; it is NOT permission to commission now and is not a guaranteed rating. Rail ±3%, divider±0.1%, shunt±1%, gain19.4…20.6, CSA input offset±3mV and comparator±6mV enter that screen. Unbounded midpoint error, thermal drift, dynamic errors and common reference faults prevent a worst-case safety claim.

Each raw SO has 100k to PGND: a disconnected output upstream of the common comparator/ADC node tends low and trips; normal loading is 16.5µA at midpoint. Open-node detection time depends on actual parasitic capacitance and leakage. A broken individual comparator branch, open shunt/Kelvin lead, stuck-valid midpoint or shorted reference is **not** comprehensively diagnosed. Output saturation beyond either window trips if comparator and supply remain alive. Gain/calibration errors can hide real faults. No blanket sensor fail-safe claim.

Low-side shunts do not continuously observe phase current during high-side conduction or every freewheel/deadtime/short path. A continuously high-side state can leave SO at midpoint despite destructive current. Maintain local DRV VDS OCP: both drivers require explicit latched OCP mode, lowest candidate 1µs deglitch, linked shutdown response and complete write/readback after reset, plus gain20/VREF_DIV/CSA_CAL=0 contract (CSA register candidate0x280). VDS threshold still needs hot RDS(on), gate-drive and switching-spike qualification; it is deliberately not assigned an invented current equivalent. Lowest SEN_OCP0.25V means nominal125A at2mΩ, not20A. Firmware implementing/readback-locking this contract remains missing.

## Timing / survival boundary

No added PWM blanking means no additional intentional blind time; it also means noise or CSA settling can nuisance-latch. TLV3202 has 1.2mV typical internal hysteresis only, no claimed guaranteed external hysteresis. Datasheet comparator maximum55ns applies to specified temperature/overdrive/load conditions; CSA1µs settling is typical, not maximum. Comparator delay alone is not end-to-end shutdown. Include sensing/blind interval, overdrive acquisition, sink, gates/DFF, ENABLE/BKIN response, gate discharge and commutation. ENABLE-to-off maximum under these conditions remains unproved. Ideal latch tests do not bound actual minimum capture pulse.

At58.4V, assumed L=0.1/1/10/100µH yields584/58.4/5.84/0.584A per µs. One hypothetical µs after20A yields604/78.4/25.84/20.584A. These are sensitivity scenarios, not measured inductance minima. Local shoot-through inductance is not motor inductance. No allowable MOSFET fault joules are invented: CSD19532Q5B hot pulsed SOA, actual clamp/commutation waveforms, transient thermal impedance and repetitive stress remain **unclosed**. The milestone cannot guarantee survival.

## Verification and evidence

- RED before wiring: `exports/fast-oc-topology-red.txt` fails specifically for missing U18 TLV3202. Separate SPICE missing-model RED retained.
- Native exports regenerated: 18 PDF/SVG pages, 246 components,153 connected nets,784 connected endpoints and45 explicit NC endpoints. Exact read-only checker compares component/value/footprint and every endpoint to BOM/pin-map; fixed-pin OC mutation tests independently break comparator/sink/latch/both break paths.
- `fast_oc_transient.cir` uses same six raw nets, actual reference resistor network, twelve separately controlled ideal sink branches, OC_OK→U14→HEALTHY, retained release-before-rearm DFF memory and actual shared break net. **IDEAL, NOT vendor models.** No CSA, comparator or MOSFET vendor timing is claimed.
- Tests inject each channel in both polarities, inside-window controls, saturation, stuck-midpoint negative coverage, stuck MCU high, held reset, fresh release/press recovery and1µs pulses. Successful ideal1µs capture is not guaranteed silicon pulse capture.
- Normal and `python -O` complete suites **25/25 pass**; results recorded in `exports/fast-oc-tests*.txt`; strict native ERC in `exports/fast-oc-strict-erc.json`. Existing four undriven supply errors remain unsuppressed: U1.24,VREF; U1.25,AGND; U3.1,IN; U17.37,VDDA. No PWR_FLAG or downgrade.

## Still blocked

Independent cold electrical review (actual model family not established), comparator/sink corners and minimum pulse testing, source/reference faults, measured latency, actual short-loop minimum inductance and MOSFET SOA, qualified VDS threshold/configuration firmware, analog sequencing/backfeed, protected entry/reverse isolation/fuse, precharge/contactor/discharge, storage/BMS acceptance, supply-loss regenerative sink, thermal limits and all control firmware. **NOT SAFE TO ENERGIZE.** Parent owns publication/integration; clean feature commit is returned for review, not silently merged.
