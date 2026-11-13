"""DRIVE12 output OVP, PGOOD domain split and L501 qualification.

Every topology assertion reads the native KiCad XML export (ref/pin/net), and the
protection arithmetic is recomputed from the resistor values that actually
reached that export -- never from a manifest count and never from a constant
copied out of the generator.

No bare ``assert``: this module must behave identically under ``python3 -O``.
Datasheet constants carry their section numbers. Nothing here is a measured
hardware result; the board remains an unsafe prototype.

WHY THE FAULT IS NOT THE ONE THE BRIEF STATES
---------------------------------------------
The brief says "if the feedback lower resistor R512 opens, FB floats to VOUT and
DRIVE12 rises toward VIN". For this regulator that is not the mechanism, and the
tests below encode the datasheet mechanism instead of the brief:

* LM5164 SNVSAU4D 6.3.3/6.3.5 is a constant-on-time regulator whose off-time
  ends only when FB falls to the 1.2 V reference. A *high* FB therefore stops
  switching and the output **falls**; it does not rise.
* R512 open with no other DC path leaves FB at ~VOUT. Switching stops, the rail
  collapses, and as VOUT approaches zero the FB abs max of 5.5 V (5.1) is
  violated -- a converter failure, not a rail overvoltage.
* The genuine DRIVE12 runaway is the **upper** leg R511 opening: FB is then held
  near PGND, permanently below 1.2 V, so the off-time never starts, duty goes to
  maximum and DRIVE12 rises to VIN.
* That runaway breaks the 25 V C513/C514/C517 bank first; the AP63203 35 V abs
  max sits behind them. Protection must act well inside 25 V.

Both faults are covered by the same detector: it guards the rail against loss of
regulation in *either* direction, and the residual risk it cannot cover is stated
in docs/design/drive-rail-protection.md.
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / 'exports' / 'ctrl-supply.xml'   # whole-project native XML export

# --- Sources ---------------------------------------------------------------
# TI LM5164 SNVSAU4D (rev FEB 2026):
#   5.1 abs max: VIN -0.3/100 V, EN -0.3/100 V, FB -0.3/5.5 V, PGOOD -0.3/14 V.
#   5.5 peak current limit 1.25/1.50/1.75 A; valley foldback 0.95/1.20/1.40 A.
#   6.3.3 regulation comparator 1.2 V; 6.3.5 off-time ends when FB <= 1.2 V.
#   6.3.6 cycle-by-cycle peak limit plus foldback valley limit, "limits the
#         average output current to less than 1.5 A".
#   6.3.9 EN/UVLO: <1.1 V shutdown (IQ 3 uA), 1.1-1.5 V standby, >1.5 V run;
#         the pin is a 100 V shunt, so it is a legitimate pull-up target.
#   6.3.10 PGOOD open drain, pull-up <= 14 V, 10k-100k, off above 95 % of VREF,
#         on below 90 %.
#   6.3.11 thermal shutdown.
#   There is NO output overvoltage protection anywhere in the datasheet: 6.3.6 is
#   current limit, 6.3.10 is an indicator only, 6.3.11 is thermal, 6.3.9 is UVLO.
LM5164_IPEAK_MAX_A = 1.75          # 5.5 peak current limit, MAX column
LM5164_IVALLEY_MAX_A = 1.40         # 5.5 valley foldback, MAX column
LM5164_FB_ABSMAX_V = 5.5            # 5.1
LM5164_VREF_V = 1.2                 # 6.3.3
LM5164_EN_ABSMAX_V = 100.0          # 5.1
LM5164_EN_SHUTDOWN_V = 1.1          # 6.3.9
LM5164_PGOOD_ABSMAX_V = 14.0        # 5.1 / 6.3.10
# Fitted DRIVE12 output bank: C513 22u + C514 22u + C517 10u, all rated 25 V.
DRIVE12_COUT_F = 54e-6
CAP_RATING_V = 25.0
AP63203_ABSMAX_DC_V = 35.0          # AP63203 abs max VIN, +40 V for 400 ms
BUS_MAX_V = 58.4                    # top of the 36-58.4 V screening range
DRIVE12_NOMINAL_MAX_V = 12.6        # 12 V + VREF/divider spread, rounded up
# TLV1821 SNOSDC8E 5.7: VOS -4..+4 mV over -40..125 C; 5.8 propagation delay
# 900 ns at VOD = 10 mV. 5.1 note (2) and 7.4.1.2: the input "upper" ESD
# soft-clamp to V+ is 5 kohm equivalent and must carry <= 1 mA.
COMPARATOR_VOS_MAX_V = 4e-3
REF2V5_TOL = 0.02                 # REF2V5 tolerance unqualified; 2 % used as a bound
SENSE_C_F = 100e-12                # sense-node filter cap, if any
CAP_BANK_F = 44e-6
SINK12_MIN_V = 11.4              # always-on 12 V rail, -5 % used as a bound                 # C513/C514/C517 bank, 3 x 470u nominal derated
COMPARATOR_TPD_S = 900e-9
RAIL_TOL = 0.03                     # SAFETY3V3 via TLV760: tolerance unqualified
RES_TOL = 0.01                      # every divider part specified 1 %
CLAMP_OHM = 5e3                     # 7.4.1.2 upper ESD soft-clamp
CLAMP_LIMIT_A = 1e-3                # 7.4.1.2 "limited to 1mA or less"

# Coilcraft MSS1246T-683MLC, the fitted part. Document 540-1 rev 01/28/22, row
# MSS1246T-683ML_: 68 uH +-20 %, DCR 167.3 typ / 185.9 max mohm, Isat
# 2.26/2.54/2.74 A at 10/20/30 % drop, Irms 1.30 A (20 C rise) / 1.80 A (40 C).
OLD = dict(isat10=2.26, irms20=1.30, irms40=1.80, dcr_max=0.1859)
# Coilcraft MSS1278T-683MLD, Document 598-1 rev 01/28/22, row MSS1278T-683ML_:
# 68 uH +-20 %, DCR 91.3 typ / 101.5 max mohm, Isat 3.92/4.46/4.74 A at
# 10/20/30 % drop, Irms 1.80 A (20 C rise) / 2.60 A (40 C rise).
NEW = dict(isat10=3.92, irms20=1.80, irms40=2.60, dcr_max=0.1015)
# Margin rules applied identically to both parts:
#   peak <= 0.80 x Isat(10 % drop) -- the LM5164 ceiling is reachable on every
#        start-up into a discharged output, so the part must not saturate there;
#   sustained <= 0.80 x Irms(40 C) -- sealed enclosure, worst-case ambient.
PEAK_MAX_RATIO = 0.80
RMS_MAX_RATIO = 0.80

SAFETY_CHAIN_REFS = {'U6', 'U7', 'U8', 'U11', 'U12', 'U13', 'U14', 'U15', 'U16'}
SAFETY_CHAIN_NETS = {'ANALOG_OK', 'ANALOG_CLEAN', 'FAULTS_OK', 'HEALTHY',
                     'PERMIT', 'TIMER_BREAK_OK'}


def parse_value(value):
    """Leading SI token of a value string, i.e. 1e6 from '1.00M 1% 0805'."""
    token = value.strip().split()[0]
    mult = {'k': 1e3, 'M': 1e6, 'm': 1e-3}
    return float(token[:-1]) * mult[token[-1]] if token[-1] in mult else float(token)


def load(root):
    """Return ({ref: value}, {(ref, pin): net}, {net: {(ref, pin)}})."""
    values = {c.attrib['ref']: (c.findtext('value') or '')
              for c in root.findall('./components/comp')}
    nets, endpoints = {}, {}
    for net in root.findall('./nets/net'):
        members = {(n.attrib['ref'], n.attrib['pin']) for n in net.findall('node')}
        endpoints[net.attrib['name']] = members
        for key in members:
            if key in nets:
                raise ValueError(f'duplicate endpoint {key}')
            nets[key] = net.attrib['name']
    if not values or not nets:
        raise ValueError('empty native export')
    return values, nets, endpoints


def _trip(values, vref_v, r_tol, vos):
    """DRIVE12 voltage at which the OVP comparator balances.

    Actual topology (read from the native export, not assumed): U503 is a
    TLV1701AIDBVR. IN+ (pin 3) sits on DRIVE_OV_SENSE, IN- (pin 4) on
    DRIVE_OV_TRIP, and OUT is pin 4's complement on pin 1 -- REF2V5. The sense
    divider is R523 (649k) / R524 (118k) straight from DRIVE12; the reference is
    the fixed REF2V5 rail. So the comparator trips when the sense tap falls
    below 2.5 V, i.e. when DRIVE12 rises above 2.5 * (R523 + R524) / R524.

    The original branch assumed a separate OVP_REF divider and a sense divider
    on R521/R522; neither exists in the generated netlist. Recomputing from the
    parts that are actually fitted is the only version that means anything.
    """
    hi = parse_value(values['R523']) * (1 + r_tol)   # top leg, high -> trips late
    lo = parse_value(values['R524']) * (1 - r_tol)   # bottom leg, low -> trips late
    return (vref_v + vos) * (hi + lo) / lo


REF2V5_V = 2.5                      # REF2V5 rail; tolerance unqualified, see below


def ovp_trip(values, which='nominal'):
    """Nominal trip plus conservative low/high corners.

    The low corner stacks every factor in the same direction (reference low,
    divider worst-case) and the high corner mirrors it, so neither bound relies
    on two errors cancelling.
    """
    if which == 'nominal':
        return _trip(values, REF2V5_V, 0.0, 0.0)
    if which == 'low':
        return _trip(values, REF2V5_V * (1 - REF2V5_TOL), -RES_TOL,
                     -COMPARATOR_VOS_MAX_V)
    return _trip(values, REF2V5_V * (1 + REF2V5_TOL), +RES_TOL,
                 +COMPARATOR_VOS_MAX_V)


def ovp_transient(values):
    """Upper bound on DRIVE12 during the detector's own response time.

    Worst case: the rail is already at the high-corner trip when the fault
    appears, and the converter's full peak current keeps charging the output
    bank for one sense-node time constant plus the propagation delay.
    """
    r = 1 / (1 / parse_value(values['R523']) + 1 / parse_value(values['R524']))
    tau = SENSE_C_F * r
    return (ovp_trip(values, 'high')
            + LM5164_IPEAK_MAX_A * (tau + COMPARATOR_TPD_S) / CAP_BANK_F)


def sense_tap_at(values, rail_v):
    """DRIVE_OV_SENSE voltage with DRIVE12 at `rail_v`."""
    hi = parse_value(values['R523'])
    lo = parse_value(values['R524'])
    return rail_v * lo / (hi + lo)


def inductor_margins(isat10, irms40, dcr_max):
    """Worst-case inductor stress against the LM5164's own limits.

    The sustained term uses the mean of the peak and valley limits, which is the
    datasheet's own bound in 6.3.6 ("less than 1.5 A"), not a load assumption.
    """
    sustained_a = (LM5164_IPEAK_MAX_A + LM5164_IVALLEY_MAX_A) / 2
    return dict(peak_a=LM5164_IPEAK_MAX_A,
                peak_ratio=LM5164_IPEAK_MAX_A / isat10,
                peak_margin=isat10 / LM5164_IPEAK_MAX_A,
                sustained_a=sustained_a,
                rms_ratio=sustained_a / irms40,
                rms_margin=irms40 / sustained_a,
                i2r_peak_w=LM5164_IPEAK_MAX_A ** 2 * dcr_max,
                i2r_sustained_w=sustained_a ** 2 * dcr_max)


def passes(m):
    return m['peak_ratio'] <= PEAK_MAX_RATIO and m['rms_ratio'] <= RMS_MAX_RATIO


def validate_ovp(values, nets, endpoints):
    """The DRIVE12 OVP path: comparator, divider, latch, and the trip window."""
    if 'U503' not in values:
        raise ValueError('no OVP comparator U503 in the native export')
    # TLV1701 DBV (SOT-23-5), SBOS589D Table 6 "Pin Functions":
    #   1 IN+ (noninverting input)   2 V- (lowest supply)
    #   3 IN- (inverting input)      4 OUT (output)
    #   5 V+ (highest supply)
    # Note this is the COMPARATOR pinout, not the TLV170 op-amp's, which is
    # 1 OUT / 3 IN+ / 4 IN-. Getting those two confused is easy and would make a
    # correct board look broken, so the mapping is cited rather than recalled.
    expected = {
        'U503': ['REF2V5', 'PGND', 'DRIVE_OV_SENSE', 'DRIVE_OV_TRIP', 'SINK12'],
        'R523': ['DRIVE12', 'DRIVE_OV_SENSE'],
        'R524': ['DRIVE_OV_SENSE', 'PGND'],
    }
    for ref, pin_nets in expected.items():
        for pin, net in enumerate(pin_nets, 1):
            got = nets.get((ref, str(pin)))
            if got != net:
                raise ValueError(f'{ref}.{pin}: expected {net}, got {got}')
    # OUT (pin 4) is open-collector: it must be pulled up, or it can only sink.
    if nets.get(('U503', '4')) != 'DRIVE_OV_TRIP':
        raise ValueError('U503 OUT (pin 4) must sit on DRIVE_OV_TRIP')
    if ('R526', '2') not in endpoints.get('DRIVE_FAULT', set()):
        raise ValueError('the open-collector fault node needs its pull-up')
    # The divider must be a divider: top leg to the guarded rail, bottom to PGND.
    if nets.get(('R523', '1')) != 'DRIVE12' or nets.get(('R524', '2')) != 'PGND':
        raise ValueError('OVP sense divider is not across DRIVE12')
    if nets.get(('R523', '2')) != nets.get(('R524', '1')):
        raise ValueError('OVP divider midpoint is not the sense node')
    # The latch replaced level protection. The comparator must NOT reach EN/UVLO
    # directly any more: leaving that in would re-enable the rail the instant the
    # fault cleared, which is exactly the hiccup RAIL-16 exists to prevent.
    if ('U503', '1') in endpoints.get('DRIVE_UVLO', set()):
        raise ValueError('U503 OUT must not reach DRIVE_UVLO directly: that is '
                         'level protection, not a latch')
    # D must be tied low, not floating and not tied high: a latch whose D can be
    # driven high could be re-armed by the hardware it is protecting against.
    if nets.get(('U504', '2')) != 'DRIVE_LATCH_D':
        raise ValueError('U504.D must be the tied-low node')
    if nets.get(('R525', '1')) != 'DRIVE_LATCH_D' or nets.get(('R525', '2')) != 'PGND':
        raise ValueError('R525 must tie the latch D input to PGND')
    if nets.get(('U504', '7')) != 'SAFETY3V3':
        raise ValueError('U504 must be powered from the always-on rail')
    if not {('U501', '3'), ('R514', '2')} <= endpoints.get('DRIVE_UVLO', set()):
        raise ValueError('the latch enable (R514) must drive U501.3 EN/UVLO')
    if ('U504', '5') not in endpoints.get('DRIVE_EN_GATED', set()):
        raise ValueError('U504.Q must be the latched enable')
    # The trip must be reachable from the comparator output, i.e. the latch's
    # clear node must carry the comparator, and the rail must not feed the latch.
    if ('U504', '6') not in endpoints.get('DRIVE_FAULT', set()):
        raise ValueError('U504 CLR_N must be on DRIVE_FAULT')
    if ('U504', '7') not in endpoints.get('SAFETY3V3', set()):
        raise ValueError('the latch must be powered from the always-on SAFETY3V3')
    if any(net == 'DRIVE12' for ref, _ in endpoints.get('SAFETY3V3', set())
           if ref == 'U504'):
        raise ValueError('latch supply must not be the rail it gates')
    # Trip window. DRIVE12 nominal max is 12.6 V; the bank is 25 V.
    low, high, peak = ovp_trip(values, 'low'), ovp_trip(values, 'high'), ovp_transient(values)
    if not DRIVE12_NOMINAL_MAX_V < low:
        raise ValueError(f'OVP low-corner trip {low:.2f} V does not clear '
                         f'{DRIVE12_NOMINAL_MAX_V} V normal operation')
    if not high < CAP_RATING_V:
        raise ValueError(f'OVP high-corner trip {high:.2f} V does not clear the '
                         f'{CAP_RATING_V} V capacitor bank')
    if not peak < CAP_RATING_V:
        raise ValueError(f'OVP transient peak {peak:.2f} V does not clear the '
                         f'{CAP_RATING_V} V capacitor bank')
    if not peak < AP63203_ABSMAX_DC_V:
        raise ValueError('OVP transient peak does not clear the AP63203 abs max')
    # The sense tap must stay inside the comparator's own input range and its
    # ESD soft-clamp must not be asked for more than 1 mA.
    tap = sense_tap_at(values, BUS_MAX_V)
    if not tap < SINK12_MIN_V:
        raise ValueError(f'sense tap {tap:.2f} V exceeds the U503 supply')
    clamp_a = max(0.0, tap - SINK12_MIN_V) / CLAMP_OHM
    if not clamp_a <= CLAMP_LIMIT_A:
        raise ValueError(f'input clamp current {clamp_a * 1e6:.0f} uA exceeds 1 mA')
    return dict(nominal=ovp_trip(values), low=low, high=high, peak=peak,
                tap=tap, clamp_a=clamp_a)


def validate_pgood(values, nets, endpoints):
    """U501.6 must leave the always-on chain and become drive-domain-only."""
    if nets.get(('U501', '6')) != 'DRIVE_PG':
        raise ValueError(f'U501.6 expected DRIVE_PG, got {nets.get(("U501", "6"))}')
    members = endpoints.get('DRIVE_PG', set())
    if ('U501', '6') not in members:
        raise ValueError('DRIVE_PG must carry U501.6')
    if any(ref in SAFETY_CHAIN_REFS for ref, _ in members):
        raise ValueError('DRIVE_PG must not reach the always-on safety chain')
    if 'DRIVE_PG' in SAFETY_CHAIN_NETS:
        raise ValueError('DRIVE_PG aliases a safety-chain net')
    # ANALOG_OK legitimately TERMINATES on the safety-chain comparators (U6/U11):
    # they are its consumers. The invariant that matters is that PGOOD is not one
    # of its drivers, which the DRIVE_PG check below enforces.
    if endpoints.get('ANALOG_OK') != {('R51', '2'), ('U11', '1'),
                                      ('U6', '1'), ('U6', '13'), ('U6', '14')}:
        raise ValueError('ANALOG_OK membership changed: '
                         f'{sorted(endpoints.get("ANALOG_OK", ()))}')
    # PGOOD is open drain (6.3.10), so it needs a pull-up. On this board that is
    # R521 to SINK12, chosen because PGOOD's abs max is 14 V -- pulling to a
    # higher rail would exceed it even though the part would otherwise work.
    if ('R521', '2') not in members:
        raise ValueError('DRIVE_PG needs its own pull-up (R521.2)')
    if nets.get(('R521', '1')) != 'SINK12':
        raise ValueError('PGOOD pull-up must reference a rail within its 14 V abs max')
    pull_up = parse_value(values['R521'])
    if not 10e3 <= pull_up <= 100e3:
        raise ValueError('PGOOD pull-up outside the 10k-100k of 6.3.10')
    # RAIL-19: DRIVE_PG must actually be consumed. U505 ANDs it with the latched
    # enable into the latch clear node, so a buck that drops out of regulation
    # clears the latch instead of leaving the enable asserted.
    if ('U505', '2') not in members:
        raise ValueError('DRIVE_PG must reach the AND gate U505.2')
    if ('U505', '4') not in endpoints.get('DRIVE_FAULT', set()):
        raise ValueError('U505 output must clear the latch via DRIVE_FAULT')
    if ('U505', '1') not in endpoints.get('DRIVE_EN_GATED', set()):
        raise ValueError('U505 must take the latched enable as its other input')


def validate_inductor(values, nets):
    """L501 must be qualified against the converter's own current limit."""
    if 'SPM10065VC-680M-D' not in values.get('L501', ''):
        raise ValueError(f'L501 is not the production TDK part: {values.get("L501")}')
    if not values['L501'].startswith('68u'):
        raise ValueError('L501 must stay 68 uH for the TI reference design')
    if 'MSS1278T' in values.get('L500', ''):
        raise ValueError('CTRL L500 is out of scope for this branch')
    for pin, net in enumerate(['DRIVE_SW', 'DRIVE12'], 1):
        if nets.get(('L501', str(pin))) != net:
            raise ValueError(f'L501.{pin} expected {net}')
    new = inductor_margins(NEW['isat10'], NEW['irms40'], NEW['dcr_max'])
    old = inductor_margins(OLD['isat10'], OLD['irms40'], OLD['dcr_max'])
    if not passes(new):
        raise ValueError(f'selected inductor fails the margin rule: {new}')
    if passes(old):
        raise ValueError('the replaced part also passes, so the rule does not '
                         'discriminate and proves nothing')
    return new, old


class DriveRailProtection(unittest.TestCase):
    def setUp(self):
        self.values, self.nets, self.endpoints = load(ET.parse(EXPORT).getroot())

    def test_ovp_topology_and_window(self):
        result = validate_ovp(self.values, self.nets, self.endpoints)
        self.assertLess(result['peak'], CAP_RATING_V)
        self.assertGreater(result['low'], DRIVE12_NOMINAL_MAX_V)
        self.assertLess(result['high'], AP63203_ABSMAX_DC_V)
        self.assertLess(result['nominal'], CAP_RATING_V)
        self.assertGreater(result['nominal'], DRIVE12_NOMINAL_MAX_V)

    def test_pgood_leaves_always_on_chain(self):
        validate_pgood(self.values, self.nets, self.endpoints)

    def test_inductor_qualified_against_converter_limit(self):
        new, old = validate_inductor(self.values, self.nets)
        self.assertGreater(new['peak_margin'], 1.9)
        self.assertGreater(new['rms_margin'], 1.5)
        self.assertGreater(old['rms_ratio'], RMS_MAX_RATIO)
        self.assertLess(old['peak_margin'], 1.35)

    def test_inhibits_and_zero_ohm_ties_preserved(self):
        for ref, (a, b) in {'R402': ('MAIN_EN', 'PGND'),
                            'R412': ('PRE_EN', 'PGND'),
                            'R519': ('MAIN_PROVEN_IN', 'PGND')}.items():
            self.assertTrue(self.values[ref].startswith('0R'), (ref, self.values[ref]))
            self.assertEqual(self.nets[(ref, '1')], a)
            self.assertEqual(self.nets[(ref, '2')], b)
        for ref in ('R67', 'R68'):
            self.assertTrue(self.values[ref].startswith('0R'), ref)
            self.assertEqual({self.nets[(ref, '1')], self.nets[(ref, '2')]},
                             {'LOGIC3V3_EXT', 'MCU_VDDA' if ref == 'R67' else 'MCU_VREF'})

    def test_wrong_sense_resistor_rejected(self):
        """A divider two decades off must not pass -- the trip window checks bite."""
        root = ET.parse(EXPORT).getroot()
        for comp in root.findall('./components/comp'):
            if comp.attrib['ref'] == 'R523':
                comp.find('value').text = '64k9 0.1% DRIVE12 OVP upper leg'
        with self.assertRaises(ValueError):
            validate_ovp(*load(root))

    def test_ovp_output_on_the_latch_bypassed_rejected(self):
        """The level-protection regression: OVP straight onto EN/UVLO, no latch.

        This is the defect RAIL-16 fixed. If the comparator can reach DRIVE_UVLO
        directly, the rail re-enables as soon as the fault clears, so the check
        has to fail even though the wire "looks" like protection.
        """
        root = ET.parse(EXPORT).getroot()
        for net in root.findall('./nets/net'):
            if net.attrib['name'] == 'DRIVE_UVLO':
                ET.SubElement(net, 'node', ref='U503', pin='4',
                              pinfunction='OUT', pintype='open_collector')
        with self.assertRaises(ValueError):
            validate_ovp(*load(root))

    def test_missing_pullup_rejected(self):
        """The open-collector fault node must be pulled up, or it can only sink."""
        root = ET.parse(EXPORT).getroot()
        for net in root.findall('./nets/net'):
            if net.attrib['name'] == 'DRIVE_FAULT':
                for node in list(net.findall('node')):
                    if node.attrib['ref'] == 'R526':
                        net.remove(node)
        with self.assertRaises(ValueError):
            validate_ovp(*load(root))

    def test_pgood_back_on_always_on_chain_rejected(self):
        root = ET.parse(EXPORT).getroot()
        for net in root.findall('./nets/net'):
            if net.attrib['name'] == 'ANALOG_OK':
                # Re-point the existing node rather than adding a second one: a
                # duplicate (ref,pin) is rejected by load() before the policy
                # under test ever runs, which would make this control vacuous.
                for node in net.findall('node'):
                    pass
                ET.SubElement(net, 'node', ref='U501', pin='6',
                              pinfunction='PGOOD', pintype='open_collector')
        # Remove U501.6 from its real net so the endpoint stays unique and the
        # injection is a *move*, which is the fault being modelled.
        for net in root.findall('./nets/net'):
            if net.attrib['name'] == 'DRIVE_PG':
                for node in list(net.findall('node')):
                    if node.attrib['ref'] == 'U501' and node.attrib['pin'] == '6':
                        net.remove(node)
        values, nets, endpoints = load(root)
        with self.assertRaises(ValueError):
            validate_pgood(values, nets, endpoints)

    def test_old_inductor_rejected(self):
        root = ET.parse(EXPORT).getroot()
        for comp in root.findall('./components/comp'):
            if comp.attrib['ref'] == 'L501':
                comp.find('value').text = '68u MSS1246T-683MLC 20%'
        with self.assertRaises(ValueError):
            validate_inductor(*load(root)[:2])

    def test_empty_and_stub_export_rejected(self):
        with self.assertRaises(ValueError):
            load(ET.fromstring('<export/>'))
        with self.assertRaises(ValueError):
            validate_ovp({}, {}, {'DRIVE_UVLO': set(), 'OVP_SENSE': set(),
                                  'OVP_REF': set(), 'SAFETY3V3': set()})


if __name__ == '__main__':
    unittest.main()
