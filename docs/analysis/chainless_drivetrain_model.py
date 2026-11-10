#!/usr/bin/env python3
"""
Chainless (series-hybrid) bicycle drivetrain + energy-buffer trade study.

Every input is a named constant with its provenance in a comment.
Every output prints the formula it used, then the number.

stdlib only. Run:  python3 chainless_drivetrain_model.py
"""

import math

# ----------------------------------------------------------------------------
# VEHICLE / RIDER
# ----------------------------------------------------------------------------
M_RIDER = 78.0        # kg  # [ASSUMPTION] adult rider
M_BIKE = 16.0         # kg  # [ESTIMATE] chromoly commuter + hub motor + pack
M_TOTAL = M_RIDER + M_BIKE
G = 9.81              # m/s2
RHO = 1.20            # kg/m3 # [CITED] air density at 20 C, sea level
CDA = 0.50            # m2    # [ESTIMATE] upright commuter, Cd 0.8 x A 0.62
CRR = 0.006           # -     # [ESTIMATE] good slick on asphalt, 0.005-0.008
ETA_DRIVETRAIN_CHAIN = 0.98   # [CITED] see EFF_CHAIN rows below

V_CRUISE_KMH = 25.0
V_CRUISE = V_CRUISE_KMH / 3.6

# ----------------------------------------------------------------------------
# MEASURED DRIVETRAIN EFFICIENCIES
# [CITED] Casteel & Archibald, "A Study on the Efficiency of Bicycle Hub Gears",
#          ASME IMECE2013-64507 / J. Mech. Des: single-speed chain 99.71 %,
#          belt 98.0 %, 7-speed derailleur 97.7-99.4 %, Rohloff 95.8-99.5 %,
#          Shimano Alfine 11: 90.4-96.6 %.
# [CITED] CyclingAbout drivetrain test (pedal-power vs hub-power): derailleur
#          95.0-96.1 %, waxed 96.1 %, OSPW 97.5 %, worn chain 90.6 %,
#          recumbent with two idlers 94.3-94.7 %.
# ----------------------------------------------------------------------------
EFF_CHAIN = {
    "single-speed chain":      0.997,   # [CITED] Casteel 99.71 %
    "derailleur, new, waxed":  0.961,   # [CITED] CyclingAbout
    "derailleur, worn chain":  0.906,   # [CITED] CyclingAbout
    "IGH Rohloff (best)":      0.995,   # [CITED] Casteel
    "IGH Alfine 11 (worst)":   0.904,   # [CITED] Casteel
    "belt drive":              0.980,   # [CITED] Casteel
    "recumbent + 2 idlers":    0.945,   # [CITED] CyclingAbout
}

# ----------------------------------------------------------------------------
# ELECTRIC MACHINE EFFICIENCIES
# [CITED] Grin Technologies motor simulator + "Deep Dive into Ebike Motor and
#          System Efficiency": All-Axle direct drive = 86 % SYSTEM efficiency
#          (controller + motor) at 31 km/h; small geared hub peaks 81 %.
# [CITED] sportdevices dyno note: MXUS 1.5 kW direct drive = 75 % at half of
#          top speed.
# [CITED] Hacker A20-22L outrunner datasheet: max efficiency 85 %.
# [CITED] InTechOpen, "Power Electronic Solutions to Improve the Performance
#          of Lundell Automotive Alternators": 100 A claw-pole alternator =
#          53 % at idle, 42 % at 6000 rpm, 42.4 % AVERAGE over the EPA drive
#          cycle; loss split at 1800 rpm = 2 % mechanical, 7 % excitation,
#          21 % magnetic, 49 % stator copper, 21 % rectifier.
# [CITED] Bosch/ADVISOR alternator map: peak efficiency occurs at 30-40 % of
#          max output and 2000-2500 rpm; efficiency collapses below ~1500 rpm.
# ----------------------------------------------------------------------------
ETA_GEN_PM_HUB = 0.86     # [CITED] PM hub machine used as generator, good pt
ETA_GEN_PM_HUB_PART = 0.78  # [ESTIMATE] off-peak / low rpm, -8 pts
ETA_GEN_CLAWPOLE = 0.55   # [CITED] car alternator in its good window only
ETA_GEN_CLAWPOLE_LOW = 0.30  # [CITED] blow 1500 rpm / low load
ETA_RECTIFIER = 0.96      # [ESTIMATE] 3-phase bridge + controller front end
ETA_CONTROLLER = 0.95     # [ESTIMATE] FOC inverter, part load
ETA_MOTOR_HUB = 0.85      # [CITED] DD hub electrical->mechanical
ETA_BATTERY_RT = 0.92     # [ESTIMATE] LFP round trip incl. BMS
ETA_CAP_RT = 0.97         # [ESTIMATE] supercap round trip at bike currents


def flat_power(v, m=M_TOTAL):
    """Mechanical power at the wheel to hold speed v on the flat, in W."""
    f_roll = CRR * m * G
    f_aero = 0.5 * RHO * CDA * v * v
    return (f_roll + f_aero) * v


def kinetic_energy(v, m=M_TOTAL):
    """Joules of kinetic energy at speed v."""
    return 0.5 * m * v * v


print("=" * 78)
print("1. VEHICLE POWER AND ENERGY AT THE BASELINE SPEED")
print("=" * 78)
print(f"mass total = {M_RIDER} rider + {M_BIKE} bike = {M_TOTAL:.1f} kg")
p_flat = flat_power(V_CRUISE)
f_roll = CRR * M_TOTAL * G
f_aero = 0.5 * RHO * CDA * V_CRUISE ** 2
print(f"P_flat = (Crr*m*g + 0.5*rho*CdA*v^2)*v")
print(f"       = ({f_roll:.2f} N + {f_aero:.2f} N) * {V_CRUISE:.2f} m/s")
print(f"       = {p_flat:.1f} W at the wheel at {V_CRUISE_KMH:.0f} km/h")
print()

ke = kinetic_energy(V_CRUISE)
ke_wh = ke / 3600.0
print(f"KE at {V_CRUISE_KMH:.0f} km/h = 0.5*m*v^2 = {ke:.0f} J = {ke_wh:.3f} Wh")
print("  ^ this is the whole prize for 'recover energy at the traffic light'")
print()

# One commute: 10 km, 20 stop-starts
COMMUTE_KM = 10.0
N_STOPS = 20
t_commute = (COMMUTE_KM * 1000) / V_CRUISE
e_flat_wh = p_flat * t_commute / 3600.0
print(f"10 km at {V_CRUISE_KMH:.0f} km/h: {t_commute/60:.1f} min, "
      f"E_flat = {e_flat_wh:.1f} Wh at the wheel (no hills, no stops)")
e_to_ke = N_STOPS * ke_wh
print(f"{N_STOPS} stop-starts x {ke_wh:.3f} Wh = {e_to_ke:.1f} Wh gross "
      f"kinetic energy available to regen")
REGEN_CAPTURE = 0.65   # [ESTIMATE] motor->battery at low speed, DD hub
e_regen = e_to_ke * REGEN_CAPTURE
print(f"  capture {REGEN_CAPTURE:.0%} of that = {e_regen:.1f} Wh, "
      f"i.e. {100*e_regen/e_flat_wh:.1f} % of the flat-road energy")
print("  [CITED] ebikes.ca: 3-8 % real-world regen recovery, up to ~14 % in")
print("          dense stop-go; recumbent trike 20 %. Same order. Confirms.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("2. SERIES-HYBRID EFFICIENCY CHAIN vs CHAIN DRIVE")
print("=" * 78)


def series_hybrid_eta(eta_gen, eta_buf, label):
    eta = eta_gen * ETA_RECTIFIER * eta_buf * ETA_CONTROLLER * ETA_MOTOR_HUB
    print(f"{label}")
    print(f"  = {eta_gen:.2f} gen x {ETA_RECTIFIER:.2f} rect x "
          f"{eta_buf:.2f} buf x {ETA_CONTROLLER:.2f} ctrl x "
          f"{ETA_MOTOR_HUB:.2f} motor")
    print(f"  = {eta:.3f}  ({100*eta:.1f} %)")
    return eta


eta_pm = series_hybrid_eta(ETA_GEN_PM_HUB, ETA_BATTERY_RT,
                           "PM generator (hub motor as generator), good point")
eta_pm_p = series_hybrid_eta(ETA_GEN_PM_HUB_PART, ETA_BATTERY_RT,
                             "PM generator, off-peak rpm")
eta_cap = series_hybrid_eta(ETA_GEN_PM_HUB, ETA_CAP_RT,
                            "PM generator + supercap buffer (no battery)")
eta_car = series_hybrid_eta(ETA_GEN_CLAWPOLE, ETA_BATTERY_RT,
                            "car claw-pole alternator, in its good window")
eta_car_low = series_hybrid_eta(ETA_GEN_CLAWPOLE_LOW, ETA_BATTERY_RT,
                                "car claw-pole alternator, below 1500 rpm")
print()

P_HUMAN = 150.0   # W at the pedals, [ESTIMATE] commuting effort
print(f"Rider input {P_HUMAN:.0f} W at the pedals. Power arriving at the road:")
for label, eta in (("chain, single-speed 99.7 %", 0.997),
                   ("chain, derailleur 96.1 %", 0.961),
                   ("chain, worn 90.6 %", 0.906),
                   ("series hybrid, PM gen + battery", eta_pm),
                   ("series hybrid, car alternator", eta_car)):
    print(f"  {label:38s} {P_HUMAN*eta:6.1f} W   "
          f"(loss {P_HUMAN*(1-eta):5.1f} W)")
print()
print("Inverted: what must the rider produce to put 150 W on the road?")
for label, eta in (("chain, single-speed 99.7 %", 0.997),
                   ("series hybrid, PM gen + battery", eta_pm),
                   ("series hybrid, car alternator", eta_car)):
    print(f"  {label:38s} {P_HUMAN/eta:6.1f} W at the pedals "
          f"(+{100*(1/eta-1):.0f} %)")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("3. DOES 'OPTIMAL CADENCE' PAY FOR THAT LOSS?")
print("=" * 78)
# [CITED] Dunst et al. 2024, "Understanding optimal cadence dynamics":
#   optimal cadence rises with intensity, from ~45 rpm at very low power.
# [CITED] ODU thesis: 66 rpm most economical at 100-200 W, 78 rpm at 300 W.
# [CITED] Marsh & Martin / medium summary: at 60 rpm higher gross efficiency
#   and lower HR than 100 rpm for trained riders.
# => the metabolic cost of riding at, say, 50 rpm instead of 70 rpm is a few
#    percent. The derailleur already spans ~400-500 % ratio and keeps a rider
#    within a few rpm of optimum.
METABOLIC_PENALTY_OFF_CADENCE = 0.04   # [ESTIMATE] 4 % gross-eff penalty, 20 rpm off
print("Best-case benefit of infinitely-variable gearing = metabolic penalty of")
print(f"riding ~20 rpm off optimum, ESTIMATE {METABOLIC_PENALTY_OFF_CADENCE:.0%}.")
print(f"Cost of the series hybrid vs a derailleur = "
      f"{100*(0.961-eta_pm):.1f} points of the rider's power.")
ratio = (0.961 - eta_pm) / METABOLIC_PENALTY_OFF_CADENCE
print(f"Ratio cost/benefit = {ratio:.1f}x  -> the transmission LOSES.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("4. WHAT STORES THE ENERGY: MASS OF THE BUFFER")
print("=" * 78)
# [CITED] Maxwell BMOD0165 P048 C0B datasheet: 165 F, 48 V, 53 Wh, 13.8 kg,
#          ESR 6.0 mOhm, 1e6 cycles / 10 yr.
# [CITED] Maxwell BMOD0500 P016 B01: 500 F, 16 V, 5.51 kg, ESR 2.1 mOhm,
#          leakage 5.2 mA max (VMS version).
# [CITED] Skeleton SkelMod 51V 177F: 63.9 Wh, 15.8 kg = 4.0 Wh/kg.
# [CITED] Eaton XV3560-2R7407-R: 400 F, 2.7 V, 3.2 mOhm, USD 16.27 @ qty 1.
# [CITED] LiFePO4 cell 3.3 V 2.5 Ah 8.3 Wh 76 g = 108 Wh/kg (avdweb.nl).
#         Pack-level 90 Wh/kg after BMS/enclosure.
# [CITED] LTO 2.4 V 20 Ah, 20 000 cycles, ~USD 31/cell on Alibaba.
CAP_CELL_F = 400.0
CAP_CELL_V = 2.7
CAP_CELL_ESR = 0.0032
CAP_CELL_PRICE = 16.27
CAP_CELL_MASS = 0.062     # kg # [ESTIMATE] 35 mm x 63 mm snap-in can
CAP_PACK_MASS_FACTOR = 1.35  # [ESTIMATE] busbars, balancing, enclosure
LFP_PACK_WH_PER_KG = 90.0    # [CITED/ESTIMATE] pack level
LTO_PACK_WH_PER_KG = 70.0    # [ESTIMATE] LTO pack level, 2.4 V cells

e_cell = 0.5 * CAP_CELL_F * CAP_CELL_V ** 2
print(f"one {CAP_CELL_F:.0f} F {CAP_CELL_V} V cell: E = 0.5*C*V^2 = "
      f"{e_cell:.0f} J = {e_cell/3600:.3f} Wh, mass {CAP_CELL_MASS*1000:.0f} g")
print(f"  -> {e_cell/3600/CAP_CELL_MASS:.2f} Wh/kg at CELL level")
print(f"  -> {e_cell/3600/(CAP_CELL_MASS*CAP_PACK_MASS_FACTOR):.2f} Wh/kg at "
      f"PACK level")
wh_per_kg_cap = e_cell / 3600 / (CAP_CELL_MASS * CAP_PACK_MASS_FACTOR)
print()

print("Mass to store X Wh (usable at 100 % DoD, which for a cap means 0 V):")
print(f"  {'target':>8s} {'supercap pack':>16s} {'LFP pack':>12s} {'LTO pack':>12s}")
for target in (10, 20, 50, 150, 300, 500):
    m_cap = target / wh_per_kg_cap
    m_lfp = target / LFP_PACK_WH_PER_KG
    m_lto = target / LTO_PACK_WH_PER_KG
    print(f"  {target:6.0f} Wh {m_cap:14.1f} kg {m_lfp:10.2f} kg {m_lto:10.2f} kg")
print()
print(f"ratio supercap/LFP mass = {LFP_PACK_WH_PER_KG/wh_per_kg_cap:.0f}x")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("5. HOW BIG DOES THE BUFFER HAVE TO BE FOR ONE STOP?")
print("=" * 78)
# Absorb one stop's KE into a capacitor bank between two voltage limits.
# Bank voltage window: a 48 V nominal pack run 40 V -> 50 V is a normal
# controller/cap window (Maxwell module abs max 51 V).
V_MIN = 40.0
V_MAX = 50.0
need_j = ke
c_needed = 2 * need_j / (V_MAX ** 2 - V_MIN ** 2)
print(f"absorb one stop = {need_j:.0f} J")
print(f"E = 0.5*C*(Vmax^2 - Vmin^2) -> C = 2E/(Vmax^2-Vmin^2)")
print(f"  with Vmin {V_MIN:.0f} V, Vmax {V_MAX:.0f} V: C = {c_needed:.2f} F")
n_series = math.ceil(48.0 / CAP_CELL_V)
c_string = CAP_CELL_F / n_series
print(f"one string of {n_series} cells in series = {c_string:.1f} F at "
      f"{n_series*CAP_CELL_V:.1f} V")
print(f"  -> ONE string already covers {c_string/c_needed:.1f}x the single-stop "
      f"requirement")
print(f"  string mass (cell only) = {n_series*CAP_CELL_MASS:.2f} kg, "
      f"price = USD {n_series*CAP_CELL_PRICE:.0f}")
print(f"  stored at full = 0.5*{c_string:.1f}*{n_series*CAP_CELL_V:.0f}^2 "
      f"= {(0.5*c_string*(n_series*CAP_CELL_V)**2)/3600:.2f} Wh")
print()
print("CONCLUSION: the *power buffer* requirement is tiny (a handful of cells).")
print("            The mass problem is the *range* requirement, not the buffer.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("6. IS THE BUFFER EVEN NEEDED? CURRENT AND ESR LOSSES")
print("=" * 78)
P_MOTOR = 250.0   # W electrical, [CITED] EU e-bike continuous rating class
V_NOM = 48.0
i_motor = P_MOTOR / V_NOM
i_regen = i_motor   # symmetric for a symmetric controller
print(f"250 W at 48 V -> {i_motor:.1f} A. On a 500 Wh pack that is "
      f"{i_motor*V_NOM/500:.2f} C.")
print("  A 500 Wh LFP pack rated 1 C = 10 A continuous; 3 C burst = 30 A.")
print("  -> the motor current is NOT a stress on the pack. No buffer needed.")
print()
BATT_IR = 0.100   # ohm # [ESTIMATE] 500 Wh pack, 16s, incl. BMS + wiring
esr_string = CAP_CELL_ESR * n_series
p_batt = i_regen ** 2 * BATT_IR
p_cap = i_regen ** 2 * esr_string
print(f"I^2R at {i_regen:.1f} A:  battery {p_batt:.2f} W   "
      f"cap string {p_cap:.3f} W   saving {p_batt-p_cap:.2f} W")
print("  during braking only, for a few seconds per stop. Negligible.")
print()
# Cap leakage, the real cost of a permanently-connected cap bank
LEAK_MA = 5.2   # [CITED] Maxwell BMOD0500 P016 B01, VMS version, max
p_leak = LEAK_MA / 1000 * V_NOM
print(f"cap bank leakage (worst case per Maxwell 500 F module) = "
      f"{LEAK_MA:.1f} mA x {V_NOM:.0f} V = {p_leak:.2f} W")
print(f"  over a 40 min commute that is {p_leak*40/60:.2f} Wh, i.e. "
      f"{100*(p_leak*40/60)/e_flat_wh:.2f} % of the trip energy. Acceptable,")
print("  but it is a permanent tax the battery does not impose.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("7. EXCITATION: CAN IT START WITH NO BATTERY AT ALL?")
print("=" * 78)
# [CITED] InTechOpen Lundell alternator paper: rotor field ~6 A at 14 V at
#   full excitation; generation-starting speed 910-1670 rpm depending on
#   winding. Below that speed the machine makes no output.
# [CITED] sakes-parts/industry: alternators produce minimal output below
#   ~1500 alternator rpm = ~500-600 engine rpm at a 2.5-3x pulley ratio.
I_FIELD = 6.0
V_FIELD = 14.0
p_field = I_FIELD * V_FIELD
print(f"claw-pole alternator field winding: {I_FIELD:.0f} A x {V_FIELD:.0f} V "
      f"= {p_field:.0f} W of excitation BEFORE any output exists.")
print("  A claw-pole machine is SEPARATELY EXCITED: with zero field current it")
print("  makes zero volts. It cannot bootstrap from a dead bus. Its regulator")
print("  also needs a supply rail to run at all.")
print("  A PM machine is SELF-EXCITED: residual magnet flux -> back-EMF at any")
print("  rpm -> rectify it -> you have a rail. PM removes the bootstrap problem.")
print()
CADENCE_RPM = 75.0
ALT_RPM_MIN = 1500.0
ratio = ALT_RPM_MIN / CADENCE_RPM
print(f"cadence {CADENCE_RPM:.0f} rpm, alternator needs {ALT_RPM_MIN:.0f} rpm")
print(f"  -> step-up ratio {ratio:.0f}:1 through a belt/gearbox, with its own")
print(f"     losses and whine. (The Mando Footloose was criticised for exactly")
print(f"     this: 'very loud (motor and pedaling generator system)'.)")
print()
# Housekeeping power for a battery-less system
P_HOUSE = 3.0   # W # [ESTIMATE] controller MCU + gate drivers + sensors
print(f"a battery-less build still needs ~{P_HOUSE:.0f} W of housekeeping")
print(f"  (MCU, gate drivers, hall sensors, CAN) whenever it is switched on.")
print(f"  From a cap bank holding {c_string:.1f} F at 48 V "
      f"({(0.5*c_string*48**2)/3600:.2f} Wh) that is "
      f"{(0.5*c_string*48**2)/3600/P_HOUSE*60:.1f} min of standby.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("8. WEAR: CYCLES PER YEAR")
print("=" * 78)
RIDES_PER_YEAR = 300
print(f"{N_STOPS} regen events/ride x {RIDES_PER_YEAR} rides = "
      f"{N_STOPS*RIDES_PER_YEAR} micro-events/year")
print("  LFP 2000-3000 full cycles  ~= 6-9 years of daily full cycling")
print("  LTO 20 000-50 000 cycles   ~= never, in a bicycle's life")
print("  supercap ~1 000 000 cycles ~= never")
print("  => LTO, not supercaps, is the honest answer to 'I want it to last'.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("9. THE ARCHITECTURE THAT KEEPS BOTH BENEFITS")
print("=" * 78)
# Parallel hybrid: pedals drive the wheel mechanically (chain), motor is in
# the hub and does regen. Rider power never passes through a generator.
print("parallel hybrid (chain to the wheel + hub motor + regen):")
print(f"  rider path      = {EFF_CHAIN['derailleur, new, waxed']:.3f} chain only")
print(f"  motor path      = {ETA_MOTOR_HUB:.2f} motor x {ETA_CONTROLLER:.2f} ctrl "
      f"x {ETA_BATTERY_RT:.2f} batt = "
      f"{ETA_MOTOR_HUB*ETA_CONTROLLER*ETA_BATTERY_RT:.3f}")
print("  rider watts are protected; regen and gearing come from the motor side.")
print("  This is a normal e-bike. [CITED] regen gain 3-8 % (ebikes.ca).")
print()
print("series hybrid only wins where a chain cannot reach:")
print("  - very long wheelbase / cargo / velomobile with several idlers")
print("    (already down to 94.3-94.7 % and mechanically awkward)")
print("  - independent left/right or two-wheel drive")
print("  - a design where you WANT the crank free of the wheel (e.g. the crank")
print("    drives a generator at constant rpm while the wheel speed varies)")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("10. SENSITIVITY: PUSH EVERY ESTIMATE TO ITS FAVOURABLE END")
print("=" * 78)
print("The series hybrid is only competitive if EVERY stage is at its best")
print("simultaneously. Best credible values on the market:")
best = 0.90 * 0.98 * 0.98 * 0.98 * 0.90
print(f"  gen 0.90 (best PM at exactly its peak rpm, ESTIMATE)")
print(f"  x rect 0.98 x buf 0.98 (cap) x ctrl 0.98 x motor 0.90 (peak)")
print(f"  = {best:.3f} ({100*best:.1f} %)  vs chain 0.961 -> still "
      f"{100*(0.961-best):.1f} pts WORSE")
print()
print("Conversely, if the rider is only 20 rpm off optimum on a derailleur,")
print(f"the chain path is {0.961:.3f} x {1-METABOLIC_PENALTY_OFF_CADENCE:.2f}"
      f" = {0.961*(1-METABOLIC_PENALTY_OFF_CADENCE):.3f} effective.")
print(f"  series hybrid at its BEST = {best:.3f} -> "
      f"{100*(0.961*(1-METABOLIC_PENALTY_OFF_CADENCE)-best):.1f} pts worse STILL.")
print("  The conclusion survives the entire plausible parameter box.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("11. RECOMMENDED BOM, REAL MARKET PARTS")
print("=" * 78)
bom = [
    ("hub motor, DD, regen-capable", "Grin All-Axle / GMAC", 1, 3.9, 380),
    ("motor controller, FOC, regen", "Grin Phaserunner", 1, 0.28, 295),
    ("battery, LFP 48 V 10 Ah", "generic LFP pack, 480 Wh", 1, 5.3, 320),
    ("torque sensor (BB)", "Grin / Sempu", 1, 0.25, 150),
    ("cycle analyst / display", "Grin CA3", 1, 0.10, 145),
    ("chain + cassette + derailleur", "existing, keep", 1, 0.9, 0),
]
print(f"  {'item':32s} {'part':24s} {'kg':>6s} {'USD':>6s}")
tkg = tusd = 0.0
for name, part, qty, kg, usd in bom:
    print(f"  {name:32s} {part:24s} {kg*qty:6.2f} {usd*qty:6.0f}")
    tkg += kg * qty
    tusd += usd * qty
print(f"  {'TOTAL (incremental, bike excluded)':32s} {'':24s} {tkg:6.2f} {tusd:6.0f}")
print()
print("Supercap alternative for the SAME function:")
print(f"  18x Eaton XV3560 400F 2.7V + busbar/balance board")
print(f"  mass {n_series*CAP_CELL_MASS*CAP_PACK_MASS_FACTOR:.2f} kg, "
      f"parts USD {n_series*CAP_CELL_PRICE:.0f} + board ~USD 60")
print(f"  delivers {0.5*c_string*(n_series*CAP_CELL_V)**2/3600:.2f} Wh, i.e. "
      f"{0.5*c_string*(n_series*CAP_CELL_V)**2/3600/0.48:.0f} % of the "
      f"pack it replaces")
print("  -> it is a POWER buffer, not an energy store. It cannot replace the pack.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("12. IF YOU STILL WANT THE CHAIN GONE: THE CHEAPEST HONEST VERSION")
print("=" * 78)
print("Do not use a car alternator. Use the SAME kind of PM machine at both")
print("ends, and put ONE small battery in the middle:")
print("  crank -> PM generator (belt, ~4:1, run it near its peak)")
print("        -> 3-phase rectifier")
print("        -> 48 V LFP pack, 5 Ah (240 Wh, 2.7 kg)")
print("        -> FOC controller -> DD hub motor")
print()
print("Why a small battery and not only caps:")
print("  1. the pack supplies excitation-free, always-available housekeeping")
print("     power and the controller's pre-charge; a cap bank at 0 V cannot")
print("     bring up its own controller")
print("  2. it absorbs the generator's speed-dependent output without the bus")
print("     voltage swinging 40-50 V on every pedal stroke")
print("  3. LTO if you want the wear profile of a capacitor with the energy of")
print("     a battery: 6s LTO = 14.4 V nominal, 20 000-50 000 cycles")
print()
print(f"efficiency you will actually get: {100*eta_pm:.1f} % at best, ")
print(f"{100*eta_pm_p:.1f} % typical, vs {100*0.961:.1f} % for the chain you")
print("removed. Expect to lose about a third of your pedalling.")
print()
print("=" * 78)
print("13. RECONCILING WITH THE TWO PRODUCTION SYSTEMS")
print("=" * 78)
print("Neither Mando nor Schaeffler publishes a generator efficiency number.")
print("Schaeffler DOES publish a system claim: 'approximately 5 % less")
print("efficient than chain drives' [CITED: Schaeffler rep to Electrek, 2021-08-31,")
print("repeated by BikeRadar and New Atlas].")
print()
print("Test whether 5 % is reachable as a DRIVETRAIN efficiency claim:")
print(f"  it would need eta_series = 0.961 - 0.05 = 0.911")
need = 0.911
print(f"  with rect 0.97, buf 0.97, ctrl 0.97, motor 0.93 -> generator alone")
print(f"  would have to be {need/(0.97**3*0.93):.3f}  (>1.0 = impossible)")
print("  -> 91 % end-to-end is THERMODYNAMICALLY IMPOSSIBLE for two")
print("     machine conversions plus a battery. So the 5 % is NOT a")
print("     drivetrain-efficiency claim. It must be a VEHICLE-level claim.")
print()

# Vehicle-level dilution: the rider's power is only PART of the traction energy.
# r = share of wheel energy supplied by the rider
# chain:  E_batt = E_wheel*(1-r)/eta_motorpath
# series: E_batt = (E_wheel - E_rider*eta_series)/eta_motorpath
# with r = E_rider*0.961/E_wheel  ->  ratio = r*(1-eta_s/0.961)/(1-r)
print("Vehicle-level penalty as a function of the RIDER'S SHARE of traction")
print("energy, r.  ratio = r*(1 - eta_s/0.961) / (1 - r)")
print()
print(f"  {'r':>6s} {'bike class':>36s} {'battery penalty':>16s}")
rows = [
    (1.00, "rider does all the work (flat battery)"),
    (0.60, "light commuter, strong rider"),
    (0.44, "cargo bike, 250 W motor + 150 W rider"),
    (0.30, "motor-dominant pedelec"),
    (0.12, "heavily motor-dominant (matches 5 %)"),
]
for r, label in rows:
    if r >= 1.0:
        pen = (0.961 / eta_pm) - 1.0
        print(f"  {r:6.2f} {label:36s} {100*pen:14.0f} % MORE PEDAL EFFORT")
    else:
        pen = r * (1 - eta_pm / 0.961) / (1 - r)
        print(f"  {r:6.2f} {label:36s} {100*pen:14.1f} % more battery")
print()
r_for_5 = 0.05 / ((1 - eta_pm / 0.961) + 0.05)
print(f"To reproduce Schaeffler's 5 %:  r = {r_for_5:.3f}  "
      f"(rider supplies {100*r_for_5:.1f} % of traction energy)")
print("  That is a genuinely motor-dominant vehicle. Read the 5 % as a")
print("  VEHICLE-range claim on a loaded cargo bike, not as drivetrain eta.")
print("  It is ALSO not reproducible on a light commuter where the rider")
print("  supplies most of the energy -- which is exactly the Mando case.")
print()

# Component estimate for the Schaeffler pedal generator
print("Component-level estimate for Schaeffler's 'pedal generator':")
print("  cycloid gearbox, ratio 1:29  [CITED: Heinzmann Free Drive leaflet]")
print("  single-stage cycloid eta: 0.75-0.85")
print("  [CITED: Rice Univ. thesis 2018, compact pin-in-housing cycloid peak")
print("          81 %; Matec 2019 experimental 0.61-0.75 across 150-850 rpm;")
print("          Blagojevic 2012: 0.77 at mu=0.2]")
print("  alternator at 75 rpm x 29 = 2175 rpm -> INSIDE the claw-pole sweet")
print("  spot (2000-2500 rpm, 30-40 % load) = 0.50-0.55")
print("  => pedal generator alone = 0.80 x 0.52 = 0.42  (0.38-0.47 range)")
print(f"  => end-to-end with rect/ctrl/motor = "
      f"{0.80*0.52*ETA_RECTIFIER*ETA_CONTROLLER*ETA_MOTOR_HUB:.3f}")
print("  The 1:29 step-up is a smart move: it puts the alternator exactly")
print("  where a claw-pole is least bad. It does not make it a PM machine.")
print()
print("Mando Footloose (2015): Korean car-parts basis -- the manufacturer's")
print("own product page lists 'Alternator + Regulator' and 'ECU' as")
print("automotive-derived parts [CITED: mandofootloose.co.kr spec page].")
print("  It used a real automotive alternator, so eta_gen = 0.42-0.53.")
print("  Owner reports: 'very loud (motor and pedaling generator system)'")
print("  [CITED: ElectricBikeReview] -- consistent with a claw-pole spinning")
print("  at a multiple of cadence.")
print("  'once the battery dies, the bike is rendered completely unrideable'")
print("  [CITED: idropnews] -- DIRECT EVIDENCE for the section 7 bootstrap")
print("  finding: a separately-excited generator cannot bootstrap itself,")
print("  and the pedal path cannot carry the rider home.")
print()

# ----------------------------------------------------------------------------
print("=" * 78)
print("DONE")
print("=" * 78)
