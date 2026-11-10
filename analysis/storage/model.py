"""Screening arithmetic only; constants/sources explained in short-buffer-storage.md.
Run from any directory with Python 3, no dependencies. No cell qualification implied.
"""
from math import sqrt


def cap_string(cell_f, cell_r, n, high, low):
    if n <= 0 or cell_f <= 0 or cell_r < 0 or not 0 <= low < high:
        raise ValueError('invalid string/window')
    c, r = cell_f / n, cell_r * n
    return c, r, .5 * c * (high**2 - low**2) / 3600


def discharge(v, r, power):
    if v <= 0 or r < 0 or power < 0 or v*v < 4*r*power:
        raise ValueError('invalid or infeasible terminal power')
    i = 2*power/(v + sqrt(v*v - 4*r*power))
    return i, i*i*r, v-i*r


def charge(v, r, power):
    if v <= 0 or r < 0 or power < 0:
        raise ValueError('invalid terminal charge power')
    i = 2*power/(v + sqrt(v*v + 4*r*power))
    return i, i*i*r, v+i*r


def launch(mass, kmh, rider=250, seconds=10, regen=.5,
           eta_gen=.9, eta_drive=8/9, aux=5, crr=.006,
           cda=.5, rho=1.225, grade=0):
    # All defaults ASSUMPTIONS, not measured efficiency/road parameters.
    # Linear velocity ramp: distance=v*t/2, integral(v**3 dt)=v**3*t/4.
    if (mass <= 0 or kmh < 0 or seconds <= 0 or rider < 0 or aux < 0
            or not 0 < eta_drive <= 1 or not 0 <= eta_gen <= 1
            or not 0 <= regen <= 1 or crr < 0 or grade+crr < 0
            or cda < 0 or rho < 0):
        raise ValueError('invalid launch; requires nonnegative road resistance')
    v = kmh/3.6
    ke = .5*mass*v*v
    road = mass*9.81*(crr+grade)*v*seconds/2 + .5*rho*cda*v**3*seconds/4
    bus = (ke+road)/eta_drive + aux*seconds - rider*eta_gen*seconds
    peak = (mass*v*v/seconds + mass*9.81*(crr+grade)*v + .5*rho*cda*v**3)/eta_drive + aux-rider*eta_gen
    # Signed cumulative bus deficit Q(t); ideal storage SOC changes by -Q.
    # Nonnegative resistance makes power monotone: at most one interior minimum.
    a = v/seconds
    linear = (mass*a*a + mass*9.81*(crr+grade)*a)/eta_drive
    cubic = .5*rho*cda*a**3/eta_drive
    constant = aux-rider*eta_gen
    def q(t):
        return constant*t + linear*t*t/2 + cubic*t**4/4
    left, right = 0., seconds
    for _ in range(64):
        mid = (left+right)/2
        if constant+linear*mid+cubic*mid**3 < 0:
            left = mid
        else:
            right = mid
    minimum = min(0., bus, q((left+right)/2))
    maximum = max(0., bus)
    return dict(net_bus_wh=bus/3600,
                excursion_wh=(maximum-minimum)/3600,
                charge_headroom_wh=-minimum/3600,
                initial_energy_wh=maximum/3600,
                ke_wh=ke/3600, road_wh=road/3600,
                buffer_wh=max(0,bus)/3600, peak_w=max(0,peak),
                regen_wh=ke*regen/3600)


if __name__ == '__main__':
    print('ASSUMPTIONS: linear 10s launch; crank250W; eta_gen=.9; eta_drive=8/9; aux5W; Crr=.006; CdA=.5; rho1.225; grade0')
    print('KE=.5*m*v²; road=m*g*Crr*v*t/2 + .5*rho*CdA*v³*t/4; buffer=((KE+road)/eta_drive+aux*t-rider*eta_gen*t)/3600')
    for m in (140,150):
        for v in (20,25):
            print(f'launch {m}kg {v}km/h:', {k:round(x,4) for k,x in launch(m,v).items()})
    print('60s bus deficit AFTER rider: E=P*t/3600; converter draw=E/.95')
    for p in (100,250,500): print(f'{p}W: {p/60:.4f}Wh bus; {p/60/.95:.4f}Wh store')
    print('CAPS C=Ccell/N, R=N*Rcell, E=.5*C*(Vhi²-Vlo²)/3600; DC/DC eta=.95 assumption')
    # CITED Eaton XV3550 / XL60-2R7308T-R; links in study.
    for name, c, r, n, hi, lo, mass, leak in (
        ('XV20 converted',300,.0045,20,50,25, .062,.0006),
        ('XV20 direct',300,.0045,20,50,36,.062,.0006),
        ('XV22 direct',300,.0045,22,55,36,.062,.0006),
        ('XL20 converted',3000,.00023,20,50,25,.515,.005)):
        cs, rs, wh = cap_string(c,r,n,hi,lo)
        print(f'{name}: C={cs:.4f}F R={rs:.5f}ohm E={wh:.4f}Wh cellmass={n*mass:.3f}kg leak@hi={hi*leak:.3f}W')
        print('  initial low-V 500W bus discharge (converted:526.316W terminal) I,loss,Vterminal:', tuple(round(x,4) for x in discharge(lo,rs,500/.95 if 'converted' in name else 500)))
        print('  initial low-V 500W input charge I,loss,Vterminal:',tuple(round(x,4) for x in charge(lo,rs,500*.95 if 'converted' in name else 500)))
    print('P28A13s DC R=.26ohm nominal46.8V: 500W discharge I,loss,V:',discharge(46.8,.26,500))
    print('P28A charge8.4A max: at36V=302.4W; at54.6V=458.64W; 500W at36V=13.8889A')
    for label,n,v,ah,kg in [('P28A',13,3.6,2.8,.046),('LFP',16,3.3,2.6,.076),('LTO',20,2.4,2.9,.150)]:
        print(f'{label}: nominal E=N*V*Ah={n*v*ah:.3f}Wh; assumed60%SOC window={n*v*ah*.6:.3f}Wh; cells={n*kg:.3f}kg')
    print('XV20 converted optimistic 60s deficit crossover=3.90625Wh*.95*3600/60=222.65625W (before ESR/guard/aging)')
    print('Converter 500W bus at95%: loss=500/.95-500=',500/.95-500,'W; roundtrip=.95²=',.95**2)
