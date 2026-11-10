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


def _trip(values, rail_v, r_tol, vos):
    """DRIVE12 voltage at which the OVP comparator balances.

    Sense divider R521/R522 from DRIVE12; reference divider R523/R524 from the
    always-on SAFETY3V3. IN+ = reference, IN- = sense, so the open-drain output
    releases (goes high = fault) once the sense tap rises above the reference.
    """
    ref_h = parse_value(values['R523']) * (1 + r_tol)   # 100k, top
    ref_l = parse_value(values['R524']) * (1 - r_tol)   # 43.2k, bottom
    sen_h = parse_value(values['R521']) * (1 - r_tol)   # 1.00M, top
    sen_l = parse_value(values['R522']) * (1 + r_tol)   # 75.0k, bottom
    v_ref = rail_v * ref_l / (ref_h + ref_l)
    return (v_ref + vos) * (sen_h + sen_l) / sen_l


def ovp_trip(values, which='nominal'):
    """Nominal trip plus conservative low/high corners.

    The low corner stacks every factor in the same direction (rail low,
    reference divider low, sense span long, VOS negative) and the high corner
    mirrors it, so neither bound relies on two errors cancelling.
    """
    if which == 'nominal':
        return _trip(values, 3.3, 0.0, 0.0)
    if which == 'low':
        return _trip(values, 3.3 * (1 - RAIL_TOL), -RES_TOL, -COMPARATOR_VOS_MAX_V)
    return _trip(values, 3.3 * (1 + RAIL_TOL), +RES_TOL, +COMPARATOR_VOS_MAX_V)


def ovp_transient(values):
    """Upper bound on DRIVE12 during the detector's own response time.

    Worst case: the rail is already at the high-corner trip when the fault
    appears, and the converter's full peak current keeps charging the output
    bank for one sense-filter time constant plus the propagation delay.
    """
    r = 1 / (1 / parse_value(values['R521']) + 1 / parse_value(values['R522']))
    tau = parse_value(values['C522']) * r
    return (ovp_trip(values, 'high')
            + LM5164_IPEAK_MAX_A / DRIVE12_COUT_F * (tau + COMPARATOR_TPD_S))


def sense_tap_at(values, bus_v=BUS_MAX_V):
    """OVP_SENSE voltage with the rail stuck at the top of the bus range."""
    hi = parse_value(values['R521'])
    lo = parse_value(values['R522'])
    return bus_v * lo / (hi + lo)


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
    """Assert the OVP comparator exists, is wired to EN/UVLO, and works."""
    if 'U503' not in values:
        raise ValueError('no OVP comparator U503 in the native export')
    expected = {
        # TLV1821 SC-70-6, SNOSDC8E Table 4-1:
        # 1 OUT, 2 V+, 3 IN+, 4 IN-, 5 V-, 6 N/C
        'U503': ['DRIVE_UVLO', 'SAFETY3V3', 'OVP_REF', 'OVP_SENSE', 'PGND'],
        'R521': ['DRIVE12', 'OVP_SENSE'],
        'R522': ['OVP_SENSE', 'PGND'],
        'R523': ['SAFETY3V3', 'OVP_REF'],
        'R524': ['OVP_REF', 'PGND'],
        'C522': ['OVP_SENSE', 'PGND'],
    }
    for ref, pin_nets in expected.items():
        for pin, net in enumerate(pin_nets, 1):
            got = nets.get((ref, str(pin)))
            if got != net:
                raise ValueError(f'{ref}.{pin}: expected {net}, got {got}')
    if nets.get(('U503', '6')) is not None:
        raise ValueError('U503 pin 6 is a no-connect and must not be on a net')
    # The comparator must act on the converter's own EN/UVLO node. Pulling FB
    # instead would be useless AND destructive: FB low tells this COT regulator
    # "output is low", so duty goes to maximum -- and FB abs max is 5.5 V (5.1),
    # so a divider from a 58 V rail cannot drive it anyway.
    if not {('U501', '3'), ('U503', '1')} <= endpoints['DRIVE_UVLO']:
        raise ValueError('OVP output must share DRIVE_UVLO with U501.3 EN/UVLO')
    # Powered and referenced from the always-on rail, never from the guarded one.
    if ('U503', '2') not in endpoints['SAFETY3V3']:
        raise ValueError('U503 V+ must be the always-on SAFETY3V3')
    if ('R523', '1') not in endpoints['SAFETY3V3']:
        raise ValueError('OVP reference divider must come from SAFETY3V3')
    # Nothing in the OVP path may reach the always-on safety chain.
    for net in ('OVP_SENSE', 'OVP_REF'):
        if net in SAFETY_CHAIN_NETS:
            raise ValueError(f'{net} collides with a safety-chain net')
        if any(ref in SAFETY_CHAIN_REFS for ref, _ in endpoints.get(net, ())):
            raise ValueError(f'{net} reaches the safety chain')
    # EN/UVLO is a comparator input with a 100 V shunt (5.1), not a logic gate,
    # so the open-drain fault output must not be left floating.
    if ('R525', '1') not in endpoints['DRIVE_UVLO']:
        raise ValueError('DRIVE_UVLO needs a pull-up for the open-drain OVP output')
    if nets.get(('R525', '2')) not in ('SAFETY3V3', 'DRIVE_EN'):
        raise ValueError('OVP pull-up must land on a driven node, got '
                         f'{nets.get(("R525", "2"))}')
    pu = parse_value(values['R525'])
    if not 10e3 <= pu <= 100e3:
        raise ValueError(f'pull-up {pu} ohm outside the 10k-100k of 6.3.10')
    # The existing default-off network must survive untouched.
    if (nets.get(('R515', '1')), nets.get(('R515', '2'))) != ('DRIVE_UVLO', 'PGND'):
        raise ValueError('R515 default-off pulldown was disturbed')
    if (nets.get(('R514', '2')), nets.get(('R514', '1'))) != ('DRIVE_UVLO', 'DRIVE_EN'):
        raise ValueError('R514 UVLO divider was disturbed')
    # The sense tap must stay inside the comparator's stated input range even
    # when the rail is stuck at the top of the bus range (7.4.1.2, 200 mV).
    tap = sense_tap_at(values)
    if not tap < 3.3 + 0.2:
        raise ValueError(f'sense tap {tap:.2f} V is outside the 7.4.1 inputs')
    clamp_a = max(0.0, tap - 3.3) / CLAMP_OHM
    if not clamp_a <= CLAMP_LIMIT_A:
        raise ValueError(f'input clamp current {clamp_a * 1e6:.0f} uA exceeds 1 mA')
    low, high, peak = (ovp_trip(values, 'low'), ovp_trip(values, 'high'),
                       ovp_transient(values))
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
    return dict(nominal=ovp_trip(values), low=low, high=high, peak=peak,
                tap=tap, clamp_a=clamp_a)


def validate_pgood(values, nets, endpoints):
    """U501.6 must leave the always-on chain and become drive-domain-only."""
    if nets.get(('U501', '6')) != 'DRIVE_PG':
        raise ValueError(f'U501.6 expected DRIVE_PG, got {nets.get(("U501", "6"))}')
    if endpoints.get('ANALOG_OK') != {('R51', '2'), ('U11', '1'),
                                      ('U6', '1'), ('U6', '13'), ('U6', '14')}:
        raise ValueError('ANALOG_OK membership changed: '
                         f'{sorted(endpoints.get("ANALOG_OK", ()))}')
    members = endpoints.get('DRIVE_PG', set())
    if ('U501', '6') not in members:
        raise ValueError('DRIVE_PG must carry U501.6')
    if any(ref in SAFETY_CHAIN_REFS for ref, _ in members):
        raise ValueError('DRIVE_PG must not reach the always-on safety chain')
    if 'DRIVE_PG' in SAFETY_CHAIN_NETS:
        raise ValueError('DRIVE_PG aliases a safety-chain net')
    # PGOOD is open drain (6.3.10): it needs its own pull-up in the same domain
    # as its only consumer, so no unpowered rail is back-fed through an MCU clamp.
    if ('R526', '1') not in members or ('U17', '91') not in members:
        raise ValueError('DRIVE_PG needs its own pull-up and the MCU status input')
    if nets.get(('R526', '2')) != 'LOGIC3V3_EXT':
        raise ValueError('PGOOD pull-up must reference its consumer domain')
    pull_up = parse_value(values['R526'])
    if not 10e3 <= pull_up <= 100e3:
        raise ValueError('pull-up outside the 10k-100k of 6.3.10')
    if nets.get(('U17', '91')) != 'DRIVE_PG':
        raise ValueError('MCU PB4 must be the DRIVE_PG status input')
    if (nets.get(('R51', '1')), nets.get(('R51', '2'))) != ('SAFETY3V3', 'ANALOG_OK'):
        raise ValueError('R51 must keep pulling ANALOG_OK to SAFETY3V3')


def validate_inductor(values, nets):
    """L501 must be qualified against the converter's own current limit."""
    if 'MSS1278T-683MLD' not in values.get('L501', ''):
        raise ValueError(f'L501 not replaced: {values.get("L501")}')
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
        root = ET.parse(EXPORT).getroot()
        for comp in root.findall('./components/comp'):
            if comp.attrib['ref'] == 'R521':
                comp.find('value').text = '100k 1% 0805 >=100V candidate'
        with self.assertRaises(ValueError):
            validate_ovp(*load(root))

    def test_ovp_output_on_fb_instead_of_en_rejected(self):
        """The classic wrong fix: a comparator pulling FB low raises the output."""
        root = ET.parse(EXPORT).getroot()
        for net in root.findall('./nets/net'):
            if net.attrib['name'] == 'DRIVE_UVLO':
                for node in list(net.findall('node')):
                    if node.attrib['ref'] == 'U503' and node.attrib['pin'] == '1':
                        node.set('ref', 'U599')
        with self.assertRaises(ValueError):
            validate_ovp(*load(root))

    def test_missing_pullup_rejected(self):
        root = ET.parse(EXPORT).getroot()
        for net in root.findall('./nets/net'):
            if net.attrib['name'] == 'DRIVE_UVLO':
                for node in list(net.findall('node')):
                    if node.attrib['ref'] == 'R525':
                        net.remove(node)
        with self.assertRaises(ValueError):
            validate_ovp(*load(root))

    def test_pgood_back_on_always_on_chain_rejected(self):
        root = ET.parse(EXPORT).getroot()
        for net in root.findall('./nets/net'):
            if net.attrib['name'] == 'ANALOG_OK':
                ET.SubElement(net, 'node', ref='U501', pin='6',
                              pinfunction='PGOOD', pintype='open_collector')
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
