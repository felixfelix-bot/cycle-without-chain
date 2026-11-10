"""Gyro screening arithmetic only; not a vehicle/controller safety simulation.
All sweep inputs are explicit hypothetical scenarios, not hardware ratings.
"""
import math

G = 9.80665  # standard gravity, m/s²
MASSES = (140, 150)  # assumed total kg; operator confirms only 120 kg rider+luggage
HEIGHTS = (0.8, 1.0)  # assumed combined COM height m above contact-line pivot
LEANS = (0.5, 1, 3, 5)  # scenario degrees


def gravity_torque(mass, height, lean_deg):
    return mass * G * height * math.sin(math.radians(lean_deg))


def omega(rpm):
    if rpm <= 0:
        raise ValueError('positive rpm required')
    return rpm * 2 * math.pi / 60


def momentum(energy_j, rpm):
    if energy_j < 0:
        raise ValueError('nonnegative energy required')
    return 2 * energy_j / omega(rpm)


def reserve(usable_j, max_rpm, min_rpm):
    if usable_j <= 0 or not 0 < min_rpm < max_rpm:
        raise ValueError('positive usable energy and 0 < min rpm < max rpm required')
    ratio = min_rpm / max_rpm
    full_j = usable_j / (1 - ratio**2)
    return full_j, full_j * ratio**2, momentum(full_j, max_rpm), momentum(full_j * ratio**2, min_rpm)


def ideal_roll_impulse(h, start_deg, end_deg):
    """One ideal CMG orientation: roll momentum component = H*sin(delta).
    Signed exchange magnitude; not a universally available roll impulse.
    """
    return abs(h * (math.sin(math.radians(end_deg)) - math.sin(math.radians(start_deg))))


def spinup_seconds(energy_j, input_w, efficiency=1.0):
    if energy_j < 0 or input_w <= 0 or not 0 < efficiency <= 1:
        raise ValueError('invalid spinup parameters')
    return energy_j / (input_w * efficiency)


def report():
    print('Gravity torque = m*g*h*sin(lean), Nm; g=9.80665')
    print('mass_kg height_m | lean_deg:', LEANS)
    for m in MASSES:
        for h in HEIGHTS:
            print(m, h, '|', ' '.join(f'{gravity_torque(m,h,a):.3f}' for a in LEANS))
    e = 0.5 * 150 * (25 / 3.6)**2
    h = momentum(e, 60000)
    tau = gravity_torque(150, 1, 5)
    print(f'KE=.5*m*v²: {e:.3f} J; H=2E/omega at 60000 rpm: {h:.6f} Nms')
    print(f'Best-case tau=H*gimbal_rate: at 1 rad/s {h:.6f} Nm; rate for {tau:.3f} Nm: {tau/h:.3f} rad/s')
    print('Ideal momentum-change bound 2H/tau:', f'{2*h/tau:.6f} s')
    print('1 Wh usable reserve sweep: min/max rpm | full J reserve J full H min H')
    for low in (0.5, 0.8, 0.9):
        print(low, '|', ' '.join(f'{x:.3f}' for x in reserve(3600,60000,60000*low)))
    print('Sizing: exact m=150,h=1,lean=5 torque used')
    for rate in (1, 3, 10):
        required_h = tau / rate
        energy = required_h * omega(60000) / 2
        print(f'rate {rate} rad/s: H=tau/rate {required_h:.3f} Nms; E=H*omega/2 {energy/3600:.3f} Wh')
    print('Ideal +/-45deg travel impulse=H*(sin45-sin(-45)); example H=10 Nms')
    impulse = ideal_roll_impulse(10,-45,45)
    print(f'{impulse:.3f} Nms; time at tau(150,1,1deg) {impulse/gravity_torque(150,1,1):.3f} s')
    print('Spinup E/P, 100 W ideal:')
    for energy in (e, reserve(3600,60000,48000)[0]):
        print(f'{energy:.3f} J -> {spinup_seconds(energy,100):.3f} s')
    print('One-hour sensitivity ONLY, assumed extra W -> Wh (P*t); not measured drain:')
    for power in (1,5,10,25,50,100):
        print(power, '->', power * 1)


if __name__ == '__main__':
    report()
