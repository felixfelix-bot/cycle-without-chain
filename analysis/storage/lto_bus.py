"""LTO (lithium-titanate) storage decision: series count, bus maximum, and
every downstream number that moves as a result.

WHAT THIS IS
------------
Arithmetic only. Every cell constant is a value transcribed from a named
primary document (see ``CANDIDATES``); every downstream formula is the same
formula the existing precharge / protection / storage models already use, so
that an old value and a new value can be compared term for term.

WHAT THIS IS NOT
----------------
Not cell qualification, not a BMS specification, not a pack design, not a
purchase, and not a claim that any candidate cell is orderable. Where a
candidate lacks a documented value the field is ``None`` — no value is
inferred. ``python3 -O`` behaviour is identical because no ``assert``
statement appears in this module (``assert_bus_maximum_admissible`` raises
``ValueError`` explicitly).

Usage::

    python3 analysis/storage/lto_bus.py

Sources are listed in ``docs/design/adr-storage-lto.md`` §2 with the
document number, section and page for each field.
"""

from dataclasses import dataclass, field
from math import pi, sqrt

# --------------------------------------------------------------------------
# Primary-source cell constants.
#
# Each value below is quoted from the document in the ``document`` field.
# ``None`` means the field is NOT IN the retrieved document for that cell.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    """One candidate cell, as its own datasheet describes it."""

    name: str
    manufacturer: str
    document: str
    nominal_v: float
    charge_ceiling_v: float          # max charge cut-off / standard charge cut-off
    discharge_floor_v: float         # standard discharge cut-off
    capacity_ah: float
    mass_g: float
    cont_a: float | None             # max continuous charge == discharge when equal
    pulse_a: float | None            # 10 s pulse
    temp_low_c: float | None
    temp_high_c: float | None
    cycles: int | None
    cycle_doc: str
    ceiling_is_family_level: bool = False
    gaps: str = ''


CANDIDATES = (
    Cell(
        name='yinlong-66160-40ah',
        manufacturer='Hebei Yinlong Energy Co., Ltd.',
        document='YLE-SPEC-LTO66160-04 Ver A/2, 2019-06-20, §4.1 单体电池基本参数 '
                 '/ Cell Specification, rows 3/5/6/7/8/9/10/13, printed pp.3-4',
        nominal_v=2.3,
        charge_ceiling_v=2.9,
        discharge_floor_v=1.5,
        capacity_ah=40.0,
        mass_g=1230.0,
        cont_a=240.0,
        pulse_a=400.0,
        temp_low_c=-40.0,
        temp_high_c=65.0,
        cycles=16000,
        cycle_doc='YLE-SPEC-LTO66160-04 §4.2 row 1, printed p.4: 16000 cycles, '
                  '1I1 charge and 1I1 discharge, 2.9 V<->1.5 V, 25+-5 degC, '
                  '>=80% initial capacity. Depth of discharge NOT stated in '
                  'the document (0 hits for DOD/放电深度).',
        gaps='Charge and discharge temperature are NOT stated separately: one '
             'range (-40~65 degC) covers both, with a remark recommending '
             '<=1I1 (40 A) below 0 degC and cooling above 35 degC.',
    ),
    Cell(
        name='yinlong-66160-30ah',
        manufacturer='Hebei Yinlong Energy Co., Ltd.',
        document='YLE-SPEC-LTO66160-02 Ver A/2, 2019-06-25, §4.1 rows 3/5/6/7/8/9/10/13, '
                 'printed pp.3-4',
        nominal_v=2.3,
        charge_ceiling_v=2.9,
        discharge_floor_v=1.5,
        capacity_ah=30.0,
        mass_g=1180.0,
        cont_a=180.0,
        pulse_a=300.0,
        temp_low_c=-40.0,
        temp_high_c=65.0,
        cycles=16000,
        cycle_doc='YLE-SPEC-LTO66160-02 §4.2 row 1: 16000 cycles at 1I1 (30 A), '
                  '2.9 V<->1.5 V, 25+-5 degC, >=80%. DOD NOT stated.',
        gaps='Charge/discharge temperature not separated.',
    ),
    Cell(
        name='altairnano-70ah',
        manufacturer='Altairnano (document 3341470, the only cell datasheet the '
                     'manufacturer currently publishes)',
        document='Document Number 3341470 (R1), 2017, p.1, §Voltage limits and '
                 '§Life characteristics',
        nominal_v=2.22,
        charge_ceiling_v=2.9,
        discharge_floor_v=1.5,
        capacity_ah=70.0,
        mass_g=1810.0,
        cont_a=500.0,
        pulse_a=900.0,
        temp_low_c=-50.0,
        temp_high_c=65.0,
        cycles=25000,
        cycle_doc='Document 3341470 (R1) p.1: ">25,000 to 80% initial capacity" '
                  'at 2C charge and 2C discharge, 100% DOD, 25 degC.',
        gaps='Charge ceiling 2.9 V and floor 1.5 V are stated over the full '
             '-40 to +55 degC range; no orderable part number is printed.',
    ),
    Cell(
        name='altairnano-60ah',
        manufacturer='Altairnano (document 3334207 R2)',
        document='Document 3334207 R2, 10/03/2011, p.1, §Voltage Limits',
        nominal_v=2.26,
        charge_ceiling_v=2.8,       # at >= +20 degC; 2.9 V below +20 degC
        discharge_floor_v=1.8,      # above +30 degC; 1.5 V at or below
        capacity_ah=64.0,
        mass_g=1840.0,
        cont_a=360.0,
        pulse_a=600.0,
        temp_low_c=-40.0,
        temp_high_c=55.0,
        cycles=16000,
        cycle_doc='Document 3334207 R2 p.1: ">16,000 to 80% initial capacity" at '
                  '2C/2C, 100% DOD, 25 degC.',
        gaps='Ceiling is temperature-dependent (2.8 V at >=+20 degC, 2.9 V '
             'below) and the floor is too (1.5 V <=+30 degC, 1.8 V above). The '
             'values here are the WORST (warm) corners.',
    ),
    Cell(
        name='toshiba-scib-2.9ah',
        manufacturer='Toshiba',
        document='Toshiba SCiB catalog SBT(E)-009a 25-04 (April 2025), '
                 '§"Lineup of Toshiba Rechargeable Battery SCiB / Cell" table, '
                 'printed p.6, for the 2.9 Ah row. The 2.7 V cell charge '
                 'ceiling is stated family-wide in the Battery System '
                 'Components catalog (Feb 2023) printed p.5 footnote *1 — NOT '
                 'in a 2.9 Ah cell datasheet',
        nominal_v=2.4,
        charge_ceiling_v=2.7,
        discharge_floor_v=1.5,
        capacity_ah=2.9,
        mass_g=150.0,
        cont_a=None,
        pulse_a=None,
        temp_low_c=None,
        temp_high_c=None,
        cycles=None,
        cycle_doc='NOT IN DOCUMENT. The "40,000 cycles at 10C/35 degC" sentence '
                  'appears only on a Toshiba HTML product page, has no DOD and '
                  'no defined end-of-life beyond "over 80% of initial capacity", '
                  'and appears in none of the 15 retrieved Toshiba PDFs.',
        ceiling_is_family_level=True,
        gaps='NOT IN DOCUMENT for the 2.9 Ah cell specifically: continuous '
             'charge/discharge current, pulse current, operating temperature '
             'range, cell-level cycle life, and a cell-level charge ceiling. '
             'The catalog prints only capacity, 2.4 V nominal, and 10 s power '
             '(520 W out / 410 W in at 50% SOC, 25 degC) footnoted "calculated '
             'from the internal resistance".',
    ),
    Cell(
        name='toshiba-scib-10ah',
        manufacturer='Toshiba',
        document='Toshiba Review Vol.71 No.2 (Feb 2016), §図3 "10 Ah級 SCiB™ の主な仕様" '
                 '/ "10 Ah-class SCiB cell" specification table, PDF p.2 / printed '
                 'p.45: 電圧範囲 1.5〜2.9 V (10 s), 1.8〜2.8 V (連続)',
        nominal_v=2.4,
        charge_ceiling_v=2.8,       # continuous window upper bound
        discharge_floor_v=1.8,      # continuous window lower bound
        capacity_ah=10.0,
        mass_g=515.0,
        cont_a=None,
        pulse_a=1000.0,             # 1 s, not 10 s
        temp_low_c=None,
        temp_high_c=None,
        cycles=None,
        cycle_doc='NOT IN DOCUMENT for this cell (the 2019 20 Ah/5 Ah paper '
                  'reports 90% retention after 2000 cycles at 1C/1C, 45 degC).',
        gaps='The only Toshiba document printing a CONTINUOUS voltage window '
             'for a high-power SCiB cell. 1000 A is a 1 s limit, not 10 s. '
             'No operating-temperature range and no cycle life in this table.',
    ),
)

_BY_NAME = {cell.name: cell for cell in CANDIDATES}


def cell(name: str) -> Cell:
    """Look up a candidate by name. Raises KeyError for an unknown name."""
    return _BY_NAME[name]


# --------------------------------------------------------------------------
# The selection constants that are decisions, not datasheet values.
# --------------------------------------------------------------------------

#: The bus maximum the electronics and the precharge contract were frozen
#: against. Kept as the ENVELOPE the series count must fit inside; it is not
#: the pack's ceiling any more. [CITED pcb-quality-gates.md §Actionable
#: checklist G0; open-gates-register.md CX-02]
LEGACY_BUS_MAX_V = 58.4

#: The design bus minimum. Loads are specified to work here.
#: [CITED precharge-budget-revision.md §Adopted bounded candidate]
BUS_MIN_V = 36.0

#: Upper bound on the charge ceiling adopted for the design point. This is the
#: strictest verified LTO charge ceiling we could document (Toshiba's own
#: family figure), chosen deliberately: it is the value that also makes the
#: supercapacitor string and the pack string the same length.
#: [CITED as above, 2.7 V cell charging voltage]
ADOPTED_CELL_CEILING_V = 2.7

#: Lower bound used for the deliverable window: the continuous discharge floor
#: of the only Toshiba cell with a published CONTINUOUS window.
#: [CITED Toshiba Review 2016 図3: 1.8〜2.8 V (連続)]
USABLE_FLOOR_V = 1.8

#: Precharge branch values. [CITED precharge-budget-revision.md §Adopted
#: bounded candidate: 22 Ω ±1 %, worst-case low 21.78 Ω; timer 350 ms maximum]
PRECHARGE_OHM_MIN = 21.78
PRECHARGE_OHM_NOM = 22.37          # including the 0.15 Ω source resistance
PRECHARGE_TIMEOUT_MAX_S = 0.350

#: Assembled bus capacitance ceiling. [CITED dc-entry-milestone.md: 1.5 mF
#: maximum verified assembled capacitance including tolerances]
BUS_CAP_F = 1.5e-3

#: Reverse-pack stress is the pack voltage against an equal opposite bus
#: voltage: 2 x Vpack. [CITED precharge-review.md §Electrical architecture]
#: The device rating is the 150 V MOSFET class. [CITED PRE-10 row]
REVERSE_PACK_FACTOR = 2.0
MOSFET_RATING_V = 150.0

#: Dump resistor pair. [CITED protection-milestone-report.md §External sink
#: selection: two HSC3004R7J, 9.4 Ω nominal, 8.93 Ω minimum]
DUMP_OHM_NOM = 9.4

#: OV comparator band as published. [CITED protection-milestone-report.md
#: §OV thresholds and timing: 59.417–61.226 V, hysteresis 2.114 V]
OV_TRIP_MIN_V = 59.417
OV_TRIP_MAX_V = 61.226
OV_HYSTERESIS_V = 2.114

#: The two acceptance envelopes. [CITED precharge-budget-review.md
#: §Independent checks: CTRL 0.8 W, SINK 1.1 W]
CTRL_INPUT_W = 0.8
SINK_INPUT_W = 1.1

@dataclass(frozen=True)
class CapCell:
    """One supercapacitor cell, as its own datasheet describes it."""

    name: str
    manufacturer: str
    document: str
    cell_f: float
    cell_v: float
    surge_v: float
    esr_ohm: float
    cont_a: float
    peak_a: float
    leak_ma: float
    stored_wh: float
    mass_g: float
    diameter_mm: float
    length_mm: float
    temp_low_c: float
    temp_high_c: float
    cycles: int
    cycle_doc: str


#: Eaton XV 400 F cell. [CITED Eaton Technical Data 4424, effective Dec 2017,
#: §Specifications and §Standard Product: XV3560-2R7407-R, 400 F, working
#: 2.7 V, surge 2.85 V, 3.2 mΩ max initial DC ESR, 26 A max continuous
#: (15 °C rise), 220 A peak 1 s, 0.85 mA max leakage, 0.41 Wh stored, 72 g;
#: §Dimensions: 35.00 mm diameter, L = 63 mm]
EATON_XV3560 = CapCell(
    name='eaton-xv3560-2r7407-r',
    manufacturer='Eaton',
    document='Eaton Technical Data 4424, effective December 2017, '
             '§Specifications and §Standard Product table, p.2; §Dimensions, p.3',
    cell_f=400.0,
    cell_v=2.7,
    surge_v=2.85,
    esr_ohm=0.0032,
    cont_a=26.0,
    peak_a=220.0,
    leak_ma=0.85,
    stored_wh=0.41,
    mass_g=72.0,
    diameter_mm=35.0,
    length_mm=63.0,
    temp_low_c=-40.0,
    temp_high_c=65.0,
    cycles=500000,
    cycle_doc='TD4424 §Performance: 500,000 charge/discharge cycles to <=20% '
              'capacitance change, cycling between max operating voltage and '
              '50% of max operating voltage at room temperature.',
)
SUPERCAP_SURGE_V = EATON_XV3560.surge_v
SUPERCAP_ESR_OHM = EATON_XV3560.esr_ohm
SUPERCAP_MASS_G = EATON_XV3560.mass_g
SUPERCAP_DIAMETER_MM = EATON_XV3560.diameter_mm
SUPERCAP_LENGTH_MM = EATON_XV3560.length_mm
#: Pack-level mass/volume factor. [CITED chainless-drivetrain.md §5: "cell
#: 6.53 Wh/kg ÷ 1.35 pack factor"] An ESTIMATE for a busbar/balance/mount
#: allowance, not a measured assembly.
PACK_FACTOR = 1.35


# --------------------------------------------------------------------------
# Series selection
# --------------------------------------------------------------------------


def _positive(value, label):
    if value is None or value <= 0:
        raise ValueError(f'{label} must be positive, got {value!r}')
    return value


def _floor_count(total: float, per_item: float, eps: float = 1e-9) -> int:
    """Integer count that fits, tolerant of float representation error.

    ``36.0 // 1.8`` is 19 in floating point because 36/1.8 is 19.999999999999996.
    A series count must not be decided by that artefact.
    """
    return int((total + eps) // per_item)


def select_series(bus_envelope_v: float = LEGACY_BUS_MAX_V,
                  bus_min_v: float = BUS_MIN_V,
                  ceiling_v: float = ADOPTED_CELL_CEILING_V,
                  floor_v: float = USABLE_FLOOR_V) -> int:
    """Largest integer N that fits the envelope AND can still reach the bus minimum.

    Two independent bounds, and the smaller one governs:

      N * ceiling_v <= bus_envelope_v   the pack cannot be charged past the
                                        frozen electronics envelope
      N * floor_v   <= bus_min_v        the pack must still be able to deliver
                                        at the design bus minimum

    For the adopted constants these give 21 and 20, so the FLOOR binds and the
    answer is 20. The count is therefore not a preference: a 21st cell would
    raise the continuous floor to 37.8 V and the pack could no longer supply
    the 36 V bus minimum the rest of the design is specified at.
    """
    _positive(bus_envelope_v, 'bus envelope')
    _positive(bus_min_v, 'bus minimum')
    _positive(ceiling_v, 'cell ceiling')
    _positive(floor_v, 'cell floor')
    by_ceiling = _floor_count(bus_envelope_v, ceiling_v)
    by_floor = _floor_count(bus_min_v, floor_v)
    n = min(by_ceiling, by_floor)
    if n < 2:
        raise ValueError('no usable series count')
    return n


def series_bounds(bus_envelope_v: float = LEGACY_BUS_MAX_V,
                  bus_min_v: float = BUS_MIN_V,
                  ceiling_v: float = ADOPTED_CELL_CEILING_V,
                  floor_v: float = USABLE_FLOOR_V) -> dict:
    """The two bounds, shown separately so the governing one is visible."""
    return {
        'by_ceiling': _floor_count(bus_envelope_v, ceiling_v),
        'by_floor': _floor_count(bus_min_v, floor_v),
        'governs': 'ceiling' if _floor_count(bus_envelope_v, ceiling_v)
                   <= _floor_count(bus_min_v, floor_v) else 'floor',
        'selected': select_series(bus_envelope_v, bus_min_v, ceiling_v, floor_v),
    }


def series_for_window(bus_min_v: float, bus_max_v: float,
                      usable_floor_v: float, ceiling_v: float) -> int:
    """Series count that fits [bus_min_v, bus_max_v]. Raises if infeasible.

    Infeasible means no count simultaneously keeps the top under ``bus_max_v``
    and lets the pack reach ``bus_min_v``.
    """
    _positive(bus_min_v, 'bus minimum')
    _positive(bus_max_v, 'bus maximum')
    _positive(usable_floor_v, 'usable floor')
    _positive(ceiling_v, 'cell ceiling')
    by_ceiling = _floor_count(bus_max_v, ceiling_v)
    by_floor = _floor_count(bus_min_v, usable_floor_v)
    n = min(by_ceiling, by_floor)
    if n < 2 or n * ceiling_v < bus_min_v:
        raise ValueError(
            f'infeasible: {bus_min_v}-{bus_max_v} V cannot be spanned by cells '
            f'of {usable_floor_v}-{ceiling_v} V')
    return n


SERIES_N = select_series()


def design_bus_maximum_v(series: int = SERIES_N,
                         ceiling_v: float = ADOPTED_CELL_CEILING_V) -> float:
    """Pack ceiling = N x cell charge ceiling. The new bus maximum."""
    _positive(series, 'series')
    _positive(ceiling_v, 'ceiling')
    return round(series * ceiling_v, 6)


def bus_minimum_v(series: int = SERIES_N,
                  floor_v: float = USABLE_FLOOR_V) -> float:
    """Lowest bus voltage the pack can deliver in its continuous window."""
    _positive(series, 'series')
    _positive(floor_v, 'floor')
    return round(series * floor_v, 6)


def implied_cell_ceiling_for(bus_v: float, series: int = SERIES_N) -> float:
    """The per-cell ceiling a given bus maximum demands. The falsifier."""
    _positive(bus_v, 'bus voltage')
    _positive(series, 'series')
    return round(bus_v / series, 6)


def required_series_for_floor(bus_min_v: float, floor_v: float) -> int:
    """Minimum series count that can still reach ``bus_min_v``."""
    _positive(bus_min_v, 'bus minimum')
    _positive(floor_v, 'floor')
    return int(-(-bus_min_v // floor_v))  # ceil, exact for these values


def alternative_bus_maximum_v(ceiling_v: float,
                              series: int = SERIES_N) -> float:
    """Bus maximum if a different candidate cell ceiling were adopted."""
    _positive(ceiling_v, 'ceiling')
    _positive(series, 'series')
    return round(series * ceiling_v, 6)


#: Minimum headroom the adopted ceiling must leave below the frozen envelope.
#: A pack whose ceiling EQUALS the envelope has no tolerance for charge
#: overshoot, balance error or a cell at the top of its tolerance band.
MIN_TOP_MARGIN_V = 1.0


def alternative_ceiling_has_margin(ceiling_v: float,
                                   series: int = SERIES_N,
                                   envelope_v: float = LEGACY_BUS_MAX_V,
                                   margin_v: float = MIN_TOP_MARGIN_V) -> bool:
    """Would adopting this ceiling still leave margin below the envelope?"""
    return envelope_v - alternative_bus_maximum_v(ceiling_v, series) >= margin_v


def assert_bus_maximum_admissible(bus_v: float,
                                  series: int = SERIES_N,
                                  ceiling_v: float = ADOPTED_CELL_CEILING_V) -> float:
    """NEGATIVE CONTROL. Refuse a bus maximum the selected chemistry cannot reach.

    Written as an explicit ``raise``, never an ``assert`` statement, so that
    ``python3 -O`` cannot strip it. Returns the voltage when admissible.
    """
    _positive(bus_v, 'bus voltage')
    needed = implied_cell_ceiling_for(bus_v, series)
    if needed > ceiling_v + 1e-9:
        raise ValueError(
            f'bus maximum {bus_v} V requires {needed} V/cell at {series}S, '
            f'above the {ceiling_v} V ceiling of the selected chemistry and '
            f'above every verified LTO ceiling — rejected')
    return bus_v


# --------------------------------------------------------------------------
# Downstream numbers
# --------------------------------------------------------------------------


def precharge_fault_power(pack_v: float,
                          r_pre_ohm: float = PRECHARGE_OHM_MIN) -> float:
    """Zero-source-impedance PRE dissipation into a hard short: V^2 / R."""
    _positive(pack_v, 'pack voltage')
    _positive(r_pre_ohm, 'precharge resistance')
    return pack_v ** 2 / r_pre_ohm


def precharge_fault_energy(pack_v: float,
                           seconds: float = PRECHARGE_TIMEOUT_MAX_S,
                           r_pre_ohm: float = PRECHARGE_OHM_MIN) -> float:
    """Worst PRE fault energy: V^2 / R * t. Scales with V squared."""
    _positive(seconds, 'seconds')
    return precharge_fault_power(pack_v, r_pre_ohm) * seconds


def capacitor_energy_j(bus_v: float, cap_f: float = BUS_CAP_F) -> float:
    """Energy stored in the assembled bus capacitance: 1/2 C V^2."""
    _positive(bus_v, 'bus voltage')
    _positive(cap_f, 'capacitance')
    return 0.5 * cap_f * bus_v ** 2


def precharge_close_time(pack_v: float, dt: float = 1e-6, t_max: float = 5.0,
                         delta_v: float = 1.0,
                         r_total_ohm: float = PRECHARGE_OHM_NOM,
                         r_bleed_ohm: float = 10_000.0,
                         cap_f: float = BUS_CAP_F,
                         load_w: float = 1.04) -> float:
    """Time to reach ``pack_v - delta_v`` through the 22 ohm branch.

    Integrates C dV/dt = (Vs-V)/R - V/Rbleed - P/V with P starting once the
    bus is above the 16 V sink UVLO, exactly as precharge-power-sources.md §4
    describes its own cross-check. Reproducing the published 0.166955 s
    (36 V) and 0.162515 s (58.4 V) is the control that this is the same model.
    """
    _positive(pack_v, 'pack voltage')
    _positive(dt, 'timestep')
    _positive(r_total_ohm, 'total resistance')
    _positive(r_bleed_ohm, 'bleed resistance')
    _positive(cap_f, 'capacitance')
    if not 0 < delta_v < pack_v:
        raise ValueError('delta_v must be smaller than the pack voltage')
    v = 0.0
    target = pack_v - delta_v
    steps = int(round(t_max / dt))
    for step in range(steps):
        current = (pack_v - v) / r_total_ohm
        if v >= 16.0:
            current -= load_w / max(v, 6.0)
        current -= v / r_bleed_ohm
        v += current * dt / cap_f
        if v >= target:
            return (step + 1) * dt
    raise ValueError('precharge did not converge inside t_max')


def reverse_pack_stress_v(pack_v: float) -> float:
    """Off-device stress with the pack reversed: 2 x pack voltage."""
    _positive(pack_v, 'pack voltage')
    return REVERSE_PACK_FACTOR * pack_v


def mosfet_static_margin_v(pack_v: float, rating_v: float = MOSFET_RATING_V) -> float:
    """Static headroom of the 150 V device against the reverse-pack stress."""
    _positive(rating_v, 'rating')
    return rating_v - reverse_pack_stress_v(pack_v)


def braking_resistor_power(bus_v: float, ohm: float = DUMP_OHM_NOM) -> float:
    """Instantaneous dump power V^2 / R. Depends on the CLAMP voltage."""
    _positive(bus_v, 'bus voltage')
    _positive(ohm, 'resistance')
    return bus_v ** 2 / ohm


def clamp_rise_v(v0: float, power_w: float, cap_f: float, seconds: float) -> float:
    """Bus rise under a constant power source: V = sqrt(V0^2 + 2Pt/C)."""
    _positive(v0, 'initial voltage')
    _positive(cap_f, 'capacitance')
    if power_w < 0 or seconds < 0:
        raise ValueError('power and seconds must be non-negative')
    return sqrt(v0 ** 2 + 2 * power_w * seconds / cap_f)


def bus_input_current_a(power_w: float, bus_v: float) -> float:
    """Rail input current at a given bus voltage: P / V."""
    _positive(power_w, 'power')
    _positive(bus_v, 'bus voltage')
    return power_w / bus_v


def ov_band_margin_v(bus_max_v: float,
                     trip_min_v: float = OV_TRIP_MIN_V) -> float:
    """Margin from the pack ceiling up to the lowest OV trip corner."""
    _positive(bus_max_v, 'bus maximum')
    return trip_min_v - bus_max_v


def ov_band_admissible(bus_max_v: float,
                       trip_min_v: float = OV_TRIP_MIN_V,
                       hysteresis_v: float = OV_HYSTERESIS_V) -> bool:
    """Does the published band clear the pack ceiling by its own hysteresis?

    The clamp must not be able to sit inside its own release band while the
    pack is at its ceiling, or a legitimately full pack would hold the sink on.
    """
    return ov_band_margin_v(bus_max_v, trip_min_v) >= hysteresis_v


def supercap_surge_ceiling_v(cells: int, surge_v: float = SUPERCAP_SURGE_V) -> float:
    """String surge ceiling: N x per-cell surge voltage."""
    _positive(cells, 'cells')
    _positive(surge_v, 'surge voltage')
    return round(cells * surge_v, 6)


def supercap_needs_own_clamp(cells: int,
                             surge_v: float = SUPERCAP_SURGE_V,
                             trip_min_v: float = OV_TRIP_MIN_V) -> bool:
    """True when the string's surge ceiling sits BELOW the OV trip.

    Then the bus OV clamp cannot protect the capacitor string: it fires after
    the capacitors are already above their surge rating.
    """
    return supercap_surge_ceiling_v(cells, surge_v) < trip_min_v


# --------------------------------------------------------------------------
# Supercapacitor buffer
# --------------------------------------------------------------------------


def single_cell_energy_wh(cap_f: float, volts: float) -> float:
    """1/2 C V^2 in Wh. Datasheet check: Eaton prints 0.41 Wh for 400 F / 2.7 V."""
    _positive(cap_f, 'capacitance')
    _positive(volts, 'voltage')
    return 0.5 * cap_f * volts ** 2 / 3600


def capacitance_for_excursion(energy_wh: float, v_high: float,
                              v_low: float) -> float:
    """C = 2E / (Vhi^2 - Vlo^2). The buffer sizing equation."""
    _positive(energy_wh, 'energy')
    if not 0 < v_low < v_high:
        raise ValueError('need 0 < v_low < v_high')
    return 2 * energy_wh * 3600 / (v_high ** 2 - v_low ** 2)


def supercap_cell_energy_wh(cell_f: float, v_high: float, v_low: float) -> float:
    """Usable energy of ONE cell over its own window; scales linearly with N.

    Because C_string = C_cell/N and the window scales as N x per-cell voltage,
    ``E_string = N * E_cell``. Cell count buys voltage, not energy per cell.
    """
    _positive(cell_f, 'cell capacitance')
    if not 0 < v_low < v_high:
        raise ValueError('need 0 < v_low < v_high')
    return 0.5 * cell_f * (v_high ** 2 - v_low ** 2) / 3600


def min_cells_for_excursion(energy_wh: float, cell_f: float = 400.0,
                            v_high: float = 2.7, v_low: float = 1.8) -> int:
    """Fewest series cells whose usable swing covers ``energy_wh``."""
    _positive(energy_wh, 'energy')
    per_cell = supercap_cell_energy_wh(cell_f, v_high, v_low)
    return max(1, int(-(-energy_wh // per_cell)))


def supercap_options(excursion_wh: float, bus_max_v: float, bus_min_v: float,
                     cell: CapCell = EATON_XV3560) -> list[dict]:
    """Three honest interface options for the buffer, costed with the same cell.

    A key property falls out of the series choice: with a 2.7 V cell ceiling
    and a 1.8 V continuous floor, a string long enough to reach the bus
    maximum (20 cells) has EXACTLY the bus window — 54 V top, 36 V bottom.
    No converter is needed for voltage matching; the string swing and the bus
    swing are the same swing. Everything then turns on how the string is
    connected, not on conversion ratio.

    OPTION A — permanently in parallel with the bus. No switch, no converter.
    REJECTED: 20 F becomes part of the assembled bus, 13 333x the 1.5 mF
    ceiling, a 447 s precharge time constant through the 22 ohm branch and
    29.16 kJ the precharge resistor must dissipate on every connection.

    OPTION B — the same string behind its own contactor and its own precharge.
    RECOMMENDED shape. The entry connector sees only the pack, so the 1.5 mF
    ceiling and every precharge number that depends on it are unchanged. The
    string has to carry its own precharge, its own OV clamp (its 2.85 V/cell
    surge ceiling is 57.0 V, BELOW the 59.417 V bus OV trip, so the bus clamp
    cannot protect it) and its own balance.

    OPTION C — the minimum cell count for the energy, behind a converter.
    Four cells carry 0.9 Wh, more than the 0.7709 Wh excursion, but the string
    is 7.2-10.8 V and needs a ~5:1 bidirectional stage at 500 W. Included to
    show that minimising cells is the wrong objective.
    """
    options = []

    n_full = int(round(bus_max_v / cell.cell_v))
    per_cell_low = bus_min_v / n_full
    full = supercap_string(cell.cell_f, cell.cell_v, cell.esr_ohm, cell.mass_g,
                           cell.diameter_mm, cell.length_mm,
                           bus_max_v, bus_min_v, excursion_wh=excursion_wh)
    common = {
        'cells': n_full,
        'string_v_max': round(n_full * cell.cell_v, 3),
        'string_v_min': round(n_full * per_cell_low, 3),
        'capacitance_f': full['capacitance_f'],
        'esr_ohm': full['esr_ohm'],
        'usable_wh': full['usable_wh'],
        'usable_over_excursion': full['excursion_margin'],
        'cell_mass_kg': full['cell_mass_kg'],
        'pack_mass_kg': full['pack_mass_kg'],
        'cell_volume_l': full['cell_volume_l'],
    }

    options.append(dict(common, **{
        'name': 'A: permanently in parallel with the bus',
        'bus_cap_ratio': round(full['capacitance_f'] / BUS_CAP_F, 1),
        'precharge_tau_s': round(PRECHARGE_OHM_NOM * full['capacitance_f'], 1),
        'precharge_j': round(0.5 * full['capacitance_f'] * bus_max_v ** 2, 1),
        'needs_own_switch': False,
        'needs_converter': False,
        'verdict': 'REJECT — bus capacitance ceiling exceeded by 4 orders of '
                   'magnitude; every precharge number is invalidated',
    }))

    options.append(dict(common, **{
        'name': 'B: same string behind its own contactor + precharge',
        'bus_cap_ratio': 0.0,
        'precharge_tau_s': None,
        'precharge_j': None,
        'needs_own_switch': True,
        'needs_converter': False,
        'own_surge_ceiling_v': supercap_surge_ceiling_v(n_full, cell.surge_v),
        'needs_own_ov_clamp': supercap_needs_own_clamp(n_full, cell.surge_v),
        'verdict': 'RECOMMENDED SHAPE — entry-circuit numbers unchanged; needs '
                   'its own contactor, precharge, clamp and balance',
    }))

    n_min = min_cells_for_excursion(excursion_wh, cell.cell_f, cell.cell_v,
                                    per_cell_low)
    small = supercap_string(cell.cell_f, cell.cell_v, cell.esr_ohm, cell.mass_g,
                            cell.diameter_mm, cell.length_mm,
                            n_min * cell.cell_v, n_min * per_cell_low,
                            excursion_wh=excursion_wh)
    v_low = n_min * per_cell_low
    i_low = 500.0 / v_low
    options.append({
        'name': f'C: minimum {n_min}-cell string + bidirectional converter',
        'cells': n_min,
        'string_v_max': round(n_min * cell.cell_v, 3),
        'string_v_min': round(v_low, 3),
        'capacitance_f': small['capacitance_f'],
        'esr_ohm': small['esr_ohm'],
        'usable_wh': small['usable_wh'],
        'usable_over_excursion': small['excursion_margin'],
        'cell_mass_kg': small['cell_mass_kg'],
        'pack_mass_kg': small['pack_mass_kg'],
        'cell_volume_l': small['cell_volume_l'],
        'needs_own_switch': True,
        'needs_converter': True,
        'converter_ratio_at_500w': round(bus_max_v / v_low, 2),
        'string_current_at_500w_low_v_a': round(i_low, 2),
        'esr_loss_at_500w_low_v_w': round(i_low ** 2 * small['esr_ohm'], 2),
        'verdict': 'REJECT on the interface — saves 0.72 kg of cells at the '
                   'cost of a 7.5:1 bidirectional 500 W stage and 61.73 W of '
                   'ESR heat at the 500 W corner',
    })
    return options


def supercap_string(cell_f: float, cell_v: float, cell_esr: float,
                    cell_mass_g: float, diameter_mm: float, length_mm: float,
                    bus_max_v: float, bus_min_v: float,
                    pack_factor: float = PACK_FACTOR,
                    excursion_wh: float = 0.7709) -> dict:
    """Series string sized so its working voltage equals the bus maximum."""
    for value, label in ((cell_f, 'cell capacitance'), (cell_v, 'cell voltage'),
                         (cell_mass_g, 'cell mass'), (diameter_mm, 'diameter'),
                         (length_mm, 'length'), (bus_max_v, 'bus max')):
        _positive(value, label)
    if cell_esr < 0:
        raise ValueError('ESR must be non-negative')
    if not 0 < bus_min_v < bus_max_v:
        raise ValueError('need 0 < bus_min < bus_max')
    n = int(round(bus_max_v / cell_v))
    if n < 2:
        raise ValueError('no usable string length')
    c = cell_f / n
    r = cell_esr * n
    usable_wh = 0.5 * c * (bus_max_v ** 2 - bus_min_v ** 2) / 3600
    cell_mass_kg = n * cell_mass_g / 1000
    cell_volume_l = n * pi / 4 * (diameter_mm / 10) ** 2 * (length_mm / 10) / 1000
    cell_wh_per_kg = single_cell_energy_wh(cell_f, cell_v) / (cell_mass_g / 1000)
    return {
        'n': n,
        'strung_voltage_v': n * cell_v,
        'per_cell_at_bus_min_v': round(bus_min_v / n, 6),
        'capacitance_f': c,
        'esr_ohm': round(r, 9),
        'usable_wh': round(usable_wh, 6),
        'excursion_wh': excursion_wh,
        'excursion_margin': round(usable_wh / excursion_wh, 4),
        'cell_mass_kg': round(cell_mass_kg, 6),
        'pack_mass_kg': round(cell_mass_kg * pack_factor, 6),
        'cell_volume_l': round(cell_volume_l, 6),
        'pack_volume_l': round(cell_volume_l * pack_factor, 6),
        'cell_wh_per_kg': round(cell_wh_per_kg, 6),
        'pack_wh_per_kg': round(cell_wh_per_kg / pack_factor, 6),
        'cap_charge_j_at_bus_max': round(0.5 * c * bus_max_v ** 2, 3),
        'precharge_tau_s': round(PRECHARGE_OHM_NOM * c, 3),
    }


def launch_excursion_wh(seconds: float, mass_kg: float = 150.0,
                        kmh: float = 25.0) -> float:
    """Cumulative buffer excursion from the project's own storage model.

    Imported from ``model.py`` rather than re-derived, so the buffer is sized
    against the study the ADR cites, not against a transcription of it.
    """
    import importlib.util
    from pathlib import Path

    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('_storage_model', here / 'model.py')
    if spec is None or spec.loader is None:
        raise ImportError('analysis/storage/model.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.launch(mass_kg, kmh, seconds=seconds)['excursion_wh']


# --------------------------------------------------------------------------
# Migration list: every downstream number, old vs new.
# --------------------------------------------------------------------------


def migration_list() -> list[dict]:
    """One row per downstream number. ``moves`` is False where it does not."""
    old = LEGACY_BUS_MAX_V
    new = design_bus_maximum_v()
    rows = []

    def row(item, old_value, new_value, unit, moves, note):
        rows.append({'item': item, 'old': old_value, 'new': new_value,
                     'unit': unit, 'moves': moves, 'note': note})

    row('Bus maximum (pack charge ceiling)', old, new, 'V', True,
        f'N={SERIES_N}S x {ADOPTED_CELL_CEILING_V} V/cell')
    row('Bus minimum (pack continuous floor)', 36.0, bus_minimum_v(), 'V', False,
        f'{SERIES_N} x {USABLE_FLOOR_V} V = the existing 36 V design minimum, unchanged')
    row('PRE fault power (hard short, 21.78 ohm)',
        round(precharge_fault_power(old), 3), round(precharge_fault_power(new), 3),
        'W', True, 'V^2/R')
    row('PRE fault energy (350 ms maximum)',
        round(precharge_fault_energy(old), 3), round(precharge_fault_energy(new), 3),
        'J', True, f'ratio (new/old) = {(new/old)**2:.6f} = V^2 scaling')
    row('Bus capacitor stored energy (1.5 mF)',
        round(capacitor_energy_j(old), 4), round(capacitor_energy_j(new), 4),
        'J', True, '1/2 C V^2')
    row('Precharge closure time to 1 V mismatch',
        round(precharge_close_time(old), 6), round(precharge_close_time(new), 6),
        's', True, 'shorter by 0.8 ms; the 300/350 ms timer budget is unaffected')
    row('1.5 mF assembled capacitance ceiling', 1.5, 1.5, 'mF', False,
        'not voltage-driven; relaxes slightly with V, but a DIRECT-parallel '
        'supercap breaks it by a factor of 13 333 and forces a converter')
    row('CTRL3V3 UVLO (30.181 V rise / 28.169 V fall typical)',
        '30.181/28.169', '30.181/28.169', 'V', False,
        'fixed divider; set below the 36 V bus minimum, which does not move')
    row('SINK12 UVLO (17.36 V on / 16.13 V off)', '17.36/16.13', '17.36/16.13',
        'V', False, 'fixed divider, independent of pack ceiling')
    row('OV trip band', f'{OV_TRIP_MIN_V}/{OV_TRIP_MAX_V}',
        f'{OV_TRIP_MIN_V}/{OV_TRIP_MAX_V}', 'V', False,
        f'band itself does not move, but its margin over the pack ceiling '
        f'grows from {ov_band_margin_v(old):.3f} V to {ov_band_margin_v(new):.3f} V; '
        f'the 2.85 V/cell supercap surge ceiling {supercap_surge_ceiling_v(SERIES_N):.1f} V '
        f'sits INSIDE it, so the OV owner must re-derive the upper justification')
    row('Reverse-pack stress on one off device (2 x Vpack)',
        reverse_pack_stress_v(old), reverse_pack_stress_v(new), 'V', True, '2 x Vpack')
    row('150 V MOSFET static margin', round(mosfet_static_margin_v(old), 3),
        round(mosfet_static_margin_v(new), 3), 'V', True,
        'improves by 8.8 V; still not evidence of SOA at turn-off')
    row('Dump resistor power at the CLAMP voltage (9.4 ohm)',
        round(braking_resistor_power(OV_TRIP_MIN_V), 3),
        round(braking_resistor_power(OV_TRIP_MIN_V), 3), 'W', False,
        'set by the OV clamp voltage, not the pack ceiling; the illustrative '
        f'"60 V / 383 W" line must be re-based to 54 V = '
        f'{braking_resistor_power(new):.3f} W for a pack-voltage example')
    row('1.1 W SINK input envelope', 1.1, 1.1, 'W', False,
        'a power envelope; the governing current is at the 36 V low corner, unchanged')
    row('0.8 W CTRL input envelope', 0.8, 0.8, 'W', False, 'as above')
    row('SINK input current at the high corner',
        round(bus_input_current_a(SINK_INPUT_W, old), 6),
        round(bus_input_current_a(SINK_INPUT_W, new), 6), 'A', True,
        f'rises, but stays below the {bus_input_current_a(SINK_INPUT_W, BUS_MIN_V):.6f} A '
        f'low-corner current that governs the design')
    row('CTRL input current at the high corner',
        round(bus_input_current_a(CTRL_INPUT_W, old), 6),
        round(bus_input_current_a(CTRL_INPUT_W, new), 6), 'A', True, 'as above')
    row('Bus rise under 500 W into 100 uF (10 us)',
        round(clamp_rise_v(60.0, 500.0, 100e-6, 10e-6), 4),
        round(clamp_rise_v(new, 500.0, 100e-6, 10e-6), 4), 'V', True,
        'starts 6 V lower, so the transient ceiling is 5.9 V better')
    return rows


def main() -> None:
    old = LEGACY_BUS_MAX_V
    new = design_bus_maximum_v()
    print('LTO STORAGE DECISION — series count, bus maximum, downstream numbers')
    print('=' * 78)
    print()
    print('1. SERIES SELECTION')
    print(f'  N * ceiling <= envelope : 58.4 / {ADOPTED_CELL_CEILING_V} = '
          f'{old / ADOPTED_CELL_CEILING_V:.4f} -> N <= {int(old // ADOPTED_CELL_CEILING_V)}')
    print(f'  N * floor   <= bus min  : 36.0 / {USABLE_FLOOR_V} = '
          f'{BUS_MIN_V / USABLE_FLOOR_V:.4f} -> N <= {int(BUS_MIN_V // USABLE_FLOOR_V)}')
    print(f'  selected series count   : N = {SERIES_N}')
    print()
    print('2. BUS MAXIMUM')
    print(f'  bus maximum = {SERIES_N} x {ADOPTED_CELL_CEILING_V} = {new} V')
    print(f'  bus minimum = {SERIES_N} x {USABLE_FLOOR_V} = {bus_minimum_v()} V')
    print(f'  58.4 V would need {implied_cell_ceiling_for(58.4)} V/cell at {SERIES_N}S')
    print(f'  58.4 / {ADOPTED_CELL_CEILING_V} = {58.4 / ADOPTED_CELL_CEILING_V:.6f} '
          f'— not an integer, so no series count lands on 58.4 V')
    print('  verdict: 58.4 V does NOT survive the LTO decision')
    print()
    print('  per-candidate ceiling at the same series count:')
    for c in CANDIDATES:
        print(f'    {c.name:24s} {c.charge_ceiling_v:>4.2f} V/cell '
              f'-> {SERIES_N * c.charge_ceiling_v:>5.1f} V, floor '
              f'{c.discharge_floor_v:>3.1f} V -> {SERIES_N * c.discharge_floor_v:>5.1f} V'
              + ('   [ceiling is family-level, not cell-level]'
                 if c.ceiling_is_family_level else ''))
    print()
    print('3. MIGRATION LIST (old 58.4 V design point -> new)')
    header = f'  {"item":48s} {"old":>12s} {"new":>12s} {"unit":>4s}  moves'
    print(header)
    print('  ' + '-' * (len(header) - 2))
    for r in migration_list():
        old_s = r['old'] if isinstance(r['old'], str) else f"{r['old']:.6g}"
        new_s = r['new'] if isinstance(r['new'], str) else f"{r['new']:.6g}"
        print(f'  {r["item"]:48s} {old_s:>12s} {new_s:>12s} {r["unit"]:>4s}  '
              f'{"YES" if r["moves"] else "no"}')
    print()
    print('4. SUPERCAPACITOR BUFFER')
    exc10 = launch_excursion_wh(10.0)
    exc30 = launch_excursion_wh(30.0)
    print(f'  documented cumulative excursion: 10 s launch = {exc10:.4f} Wh; '
          f'30 s launch = {exc30:.4f} Wh')
    print('  (the 0.7709 Wh figure is the 10 s case; sizing against it is the '
          'conservative choice)')
    need = capacitance_for_excursion(exc10, new, bus_minimum_v())
    print(f'  C = 2E/(Vhi^2-Vlo^2) = 2 x {exc10:.4f} x 3600 / '
          f'({new}^2 - {bus_minimum_v()}^2) = {need:.4f} F')
    s = supercap_string(400.0, 2.7, SUPERCAP_ESR_OHM, SUPERCAP_MASS_G,
                        SUPERCAP_DIAMETER_MM, SUPERCAP_LENGTH_MM,
                        new, bus_minimum_v(), excursion_wh=exc10)
    for key in ('n', 'strung_voltage_v', 'per_cell_at_bus_min_v', 'capacitance_f',
                'esr_ohm', 'usable_wh', 'excursion_wh', 'excursion_margin',
                'cell_mass_kg', 'pack_mass_kg', 'cell_volume_l', 'pack_volume_l',
                'cell_wh_per_kg', 'pack_wh_per_kg', 'cap_charge_j_at_bus_max',
                'precharge_tau_s'):
        print(f'    {key:24s} {s[key]}')
    print(f'  surge ceiling = {SERIES_N} x {SUPERCAP_SURGE_V} = '
          f'{supercap_surge_ceiling_v(SERIES_N)} V vs OV trip minimum '
          f'{OV_TRIP_MIN_V} V -> own clamp required: '
          f'{supercap_needs_own_clamp(SERIES_N)}')
    print()
    print('  INTERFACE OPTIONS (same cell, same 0.7709 Wh excursion):')
    for opt in supercap_options(exc10, new, bus_minimum_v()):
        print(f'    {opt["name"]}')
        for key, value in opt.items():
            if key in ('name', 'verdict'):
                continue
            print(f'      {key:34s} {value}')
        print(f'      {"verdict":34s} {opt["verdict"]}')
    print()
    print('5. NEGATIVE CONTROL')
    try:
        assert_bus_maximum_admissible(58.4)
        print('  FAIL: 58.4 V was accepted while LTO is selected')
    except ValueError as exc:
        print(f'  PASS: {exc}')
    print(f'  PASS: {assert_bus_maximum_admissible(new)} V accepted')


if __name__ == '__main__':
    main()
