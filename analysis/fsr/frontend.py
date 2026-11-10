"""Ideal DC/resistor-noise study; resistance sweep is NOT a force calibration."""
import math
SUPPLY = 3.3  # assumed MCU rail and ADC reference
BITS = 12  # illustrative ADC, not MCU ENOB claim

def divider(r, rm=10000, series=2000, supply=SUPPLY):
    if r < 0: raise ValueError("negative resistance")
    return supply * rm / (r + series + rm)

def conductance(r, rf=10000, excitation=.3, series=0):
    return math.inf if r + series == 0 else excitation*(1+rf/(r+series))

def bridge(r, gain=4, arm=10000):
    return SUPPLY/2 + gain*(divider(r,rm=arm,series=0)-SUPPLY/2)

def code(v):
    return min(4095,max(0,round(v/SUPPLY*4096)))

def inhibit(binary_brake, analog):
    """Specification predicate only: no implemented hardware/firmware claim."""
    return bool(binary_brake)

def johnson(r,bw,temp=300):
    return math.sqrt(4*1.380649e-23*temp*r*bw)

if __name__ == '__main__':
    print('R_ohm,divider_V,ADC12_code,conductance_V_ideal,bridge_G4_V_ideal')
    for r in [math.inf,1e7,1e6,1e5,1e4,1e3,100,0]:
        print(f'{r:g},{divider(r):.6f},{code(divider(r))},{conductance(r):.6f},{bridge(r):.6f}')
    print(f'LSB = 3.3/4096 = {SUPPLY/4096*1e6:.3f} uV; quantization RMS = LSB/sqrt(12) = {SUPPLY/4096/math.sqrt(12)*1e6:.3f} uV')
    print(f'Johnson sqrt(4kTRB), 10k/50Hz/300K = {johnson(10000,50)*1e6:.3f} uV RMS')
    for r in [100,1000,10000,100000,1000000]:
        dvdr=SUPPLY*10000/(r+12000)**2
        print(f'R={r:g}: local dR/LSB=LSB/abs(dV/dR)={SUPPLY/4096/dvdr:.3f} ohm')
    print(f'Sensor short I=3.3/12000={3.3/12000*1e3:.3f} mA')
    print(f'10mm contact area=pi*(0.5cm)^2={math.pi*.5**2:.3f} cm2; current density={3.3/12000*1000/(math.pi*.5**2):.3f} mA/cm2')
    print(f'20N/10mm disk area={20/(math.pi*.005**2)/1000:.3f} kPa (not allowable stress)')
