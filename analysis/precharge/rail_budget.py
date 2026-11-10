"""Rail partition screening ledger, NOT a qualified maximum or energization gate.
Run: python3 analysis/precharge/rail_budget.py [--self-test] [--json]
Sources and conditions: docs/design/rail-partition-milestone.md.
No dependencies; does not execute or modify schematic generators.
"""
from dataclasses import asdict, dataclass
import argparse
import json
import math
from typing import Any

SINK_V = 12.0
LOGIC_V = 3.3
EARLY_SINK_CAP_W = 1.1  # acceptance envelope, not measured
CTRL_CAP_W = 0.8       # separate pack-side acceptance envelope
ETA_SINK = 0.60        # ASSUMPTION; retained R78HB light-load efficiency unqualified
RESERVE_W = 0.30       # historical input reserve, not a physical load
PROOF_ALLOWANCE_W = 0.10  # unimplemented main proof analog, not fitted BOM
BUS_MAX_V = 58.4          # top of the provisional 36-58.4 V screening range
IVDRAIN_TYP_A = 1.9e-3    # TI DRV8353 SLVSDV2 IVDRAIN, VVM=VVDRAIN=48V, ENABLE=3.3V, INHx/INLx=0V
IVDRAIN_MAX_A = 4.0e-3    # same table, MAX column
Q13_QG_TYP_C = 48e-9   # TI CSD19532Q5B SLPS414B section 5.1, 10V/50V/17A
Q13_QG_MAX_C = 62e-9   # same test, NOT a bound at 12V

@dataclass(frozen=True)
class Load:
    name: str
    rail: str
    watts: float
    basis: str


def ledger():
    """Nominal resistors plus explicitly labelled design envelopes; no max sum."""
    v = LOGIC_V
    return [
        Load('R39 preload', 'SINK12', 12**2/1000, 'nominal; protection_circuit.py'),
        Load('R40/U5 LM4040 total branch', 'SINK12', 12*(12-2.5)/4700, 'nominal; includes reference, do not add it twice'),
        Load('R46/R47 monitor', 'SINK12', 12**2/40000, 'nominal'),
        Load('U6 LM339B', 'SINK12', 12*.0016, '1.6mA envelope from 36V maximum, not guaranteed 12V test'),
        Load('U10 UCC27511 static', 'SINK12', 12*.001, 'ASSUMPTION 1mA, not UVLO startup specification'),
        Load('R45 R51 R56 R57 R115 pullups', 'SAFETY3V3', v*(v/1000+2*v/4700+2*v/10000), 'nominal all-low envelope; includes OC_OK pullup'),
        Load('J5 FAULT_CHAIN sense and MCU sense divider', 'SAFETY3V3', v*(v/10000+v/110000), 'closed NC loop, NOT external power allocation'),
        Load('RELEASE_N FAULT_LATCH 100k pulldowns', 'SAFETY3V3', 2*v*v/100000, 'both-high screening, mutually exclusive states not credited'),
        Load('U7 U8 U11-U16 U24 U25 U510 static', 'SAFETY3V3', v*11*20e-6, 'ASSUMPTION 20uA/package; mixed parts require exact limits/dynamic audit'),
        Load('U9 TPS3823', 'SAFETY3V3', v*50e-6, 'ASSUMPTION 50uA, not claimed datasheet maximum'),
        Load('U510 EN resistor chains', 'SAFETY3V3', v*v*(1/182000+1/147000), 'nominal post-proof high; zero while inhibited'),
        Load('U18-U23 TLV3202 twelve channels', 'LOGIC3V3_EXT', v*12*65e-6, '65uA/channel full-temp max at 2.7/5V; 3.3V envelope; typ 40uA'),
        Load('OC_LOW/HIGH reference ladders', 'LOGIC3V3_EXT', 2*v*v/38700, 'nominal fast_oc_circuit.py'),
        Load('Q14-Q25 OC gate 100k pulldowns', 'LOGIC3V3_EXT', 12*v*v/100000, 'all-high resistor envelope; no gate dynamic charge included'),
        Load('U26 U28 OPA333 IQ', 'LOGIC3V3_EXT', v*2*28e-6, '28uA full-temp max; typ17uA; MCU_VREF linked by 0R'),
        Load('U27 U29 TMUX1511 IQ', 'LOGIC3V3_EXT', v*2*70e-6, '70uA max, typ37uA; SCDS390B section5.5'),
        Load('two FSR excitation paths', 'LOGIC3V3_EXT', 2*v*v/21000, 'nominal maximum with FSR=0ohm; 10k+1k+10k'),
        Load('two FSR buffer output paths', 'LOGIC3V3_EXT', 2*v*(v*10000/21000)/11000, 'nominal FSR=0, mux ON, RON neglected; distinct OPA output current'),
        Load('FSR_SAMPLE_ENABLE pulldowns', 'LOGIC3V3_EXT', 2*v*v/100000, 'nominal high; mux internal pulldown/leakage not included'),
        Load('two binary switch biases', 'LOGIC3V3_EXT', 2*v*v/10000, 'nominal cable-short bound, normal NC path includes 4k7 EOL'),
        Load('six Hall plus two encoder pullups', 'LOGIC3V3_EXT', 8*v*v/10000, 'all-low; excludes external sensor supply current'),
        Load('MCU rail monitor 2k/10k', 'LOGIC3V3_EXT', v*v/12000, 'nominal'),
        Load('WDI, ARM, RESET, dump PWM, NRST loads', 'LOGIC3V3_EXT', v*v*(1/1000+4/10000), 'screening high GPIO plus asserted NRST; dynamics excluded'),
        Load('U501 feedback 453k/49k9', 'DRIVE12', 12**2/502900, 'nominal; other conversion losses belong to efficiency'),
        # U1.4/U2.4 VDRAIN stay on DC_LINK (bus-connected, always on) even though VM moved
        # to delayed DRIVE12. Omitting this hid 0.13-0.47 W of always-on bus load.
        Load('U1/U2 VDRAIN operating current', 'DC_LINK',
             2*IVDRAIN_MAX_A*BUS_MAX_V, 'DRV8353 MAX at 58.4V x2 devices; typ 1.9mA = %.3f W' % (2*IVDRAIN_TYP_A*BUS_MAX_V)),
    ]


def gate_power(qg_c, voltage_v, frequency_hz, duty):
    if not all(math.isfinite(x) for x in (qg_c, voltage_v, frequency_hz, duty)) or min(qg_c, voltage_v, frequency_hz) < 0 or not 0 <= duty <= 1:
        raise ValueError('finite nonnegative Q/V/f and duty in [0,1] required')
    return qg_c*voltage_v*frequency_hz + voltage_v**2/10000*duty


def calculate(oc_on_safety=False) -> dict[str, Any]:
    rows = ledger()
    if oc_on_safety:
        rows = [Load(r.name, 'SAFETY3V3' if r.name.startswith(('U18-', 'OC_LOW', 'Q14-')) else r.rail, r.watts, r.basis) for r in rows]
    totals = {rail: sum(r.watts for r in rows if r.rail == rail)
              for rail in ('SINK12','SAFETY3V3','LOGIC3V3_EXT','DRIVE12','DC_LINK')}
    safety_a = totals['SAFETY3V3']/LOGIC_V
    ldo_in = 12*(safety_a+.005)  # TLV760 5mA no-load max used as allowance, loaded unknown
    sink_out = totals['SINK12']+ldo_in+PROOF_ALLOWANCE_W
    sink_input = sink_out/ETA_SINK+RESERVE_W
    return dict(rows=[asdict(r) for r in rows], subtotals_w=totals,
                safety_load_a=safety_a, safety_ldo_input_w=ldo_in,
                sink_output_with_proof_allowance_w=sink_out,
                sink_input_screening_w=sink_input,
                sink_cap_margin_w=EARLY_SINK_CAP_W-sink_input,
                # Always-on bus load that bypasses the sink rail entirely; the 1.1 W
                # sink envelope does NOT bound it and it must be budgeted separately.
                direct_bus_always_w=totals['DC_LINK'],
                ctrl_separate_pack_input_cap_w=CTRL_CAP_W,
                oc_on_safety=oc_on_safety,
                qualified=False,
                unknowns=['U17 MCU operating mode/temperature/IO load',
                          'U1/U2 VM static and switching demand; CSA output loads',
                          'external Hall/encoder consumption and SWD backfeed',
                          'logic/OC/FSR switching and input transition currents',
                          'R78HB efficiency, startup, loaded TLV760 ground current',
                          'Qg at 12V and actual dump frequency/duty',
                          'bus TVS/leakage and inactive domain backfeed',
                          'VDRAIN slew 2 V/us and its interaction with precharge dV/dt'])


def _check(condition, message):
    """Explicit failure so `python3 -O` cannot make this self-test vacuous.

    `assert` is stripped under -O, which previously let a corrupted ledger
    print "self-test: PASS" with rc=0. Everything here raises instead.
    """
    if not condition:
        raise RuntimeError('self-test failed: ' + message)


def self_test():
    _check(len(ledger()) == 25, 'ledger row count')
    _d = calculate()
    _check(_d['direct_bus_always_w'] > 0.4,
           'DRV8353 VDRAIN always-on bus load must be budgeted (2x4mA at 58.4V)')
    _check(_d['direct_bus_always_w'] < 0.5, 'DRV8353 VDRAIN envelope sanity')
    _check(_d['direct_bus_always_w'] > _d['subtotals_w']['SINK12'],
           'VDRAIN bus load exceeds SINK12 subtotal and cannot be omitted')
    _check(math.isclose(gate_power(48e-9, 12, 20000, .5), .01872), 'gate_power 48nC')
    _check(math.isclose(gate_power(62e-9, 12, 20000, .5), .02208), 'gate_power 62nC')
    a, b = calculate(), calculate(True)
    _check(b['sink_input_screening_w'] > a['sink_input_screening_w'],
           'OC-on-safety must raise sink input power')
    _check(a['qualified'] is False, 'unsourced rail must never self-report qualified')
    _check(a['ctrl_separate_pack_input_cap_w'] == .8, 'CTRL cap must stay separate from sink')
    _check(math.isclose(a['subtotals_w']['SINK12'], .2030553191489362),
           'SINK12 subtotal drifted')
    for args in [(-1,12,1,.5),(1,12,1,2),(1,12,float('nan'),0)]:
        try:
            gate_power(*args)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid gate input accepted')
    print('self-test: PASS (ledger, arithmetic, rail relocation, validation)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--oc-on-safety', action='store_true', help='screen candidate OC migration, not a wiring claim')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    result = calculate(args.oc_on_safety)
    if args.json:
        print(json.dumps(result, indent=2))
        return
    for row in result.pop('rows'):
        print(f"{row['rail']:14s} {row['watts']:.9f} W  {row['name']} [{row['basis']}]")
    for k,v in result.items():
        print(f'{k}: {v}')
    for q in (Q13_QG_TYP_C,Q13_QG_MAX_C):
        print(f'Q13 sensitivity Q={q*1e9:g}nC: Q*12V*20kHz + 12^2/10k*0.5 = {gate_power(q,12,20000,.5):.6f} W (NOT 12V bound)')
    for bus in (35.,57.4):
        print(f'Direct bus at {bus:g}V: R118={bus**2/10000:.9f} W; sense series approximation={bus**2/235000:.9f} W; TVS unknown')
    print('Whole-rail worst case UNKNOWN; no release or early-envelope compliance claimed.')

if __name__ == '__main__':
    main()
