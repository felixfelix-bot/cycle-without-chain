"""First-order screening only: constant road speed/grade, no certified vehicle rating.
All default environmental/efficiency/thermal values are ASSUMPTIONS, not measurements.
Run directly for the complete bounded parameter grid as CSV on stdout.
"""
import csv
import itertools
import math
import sys

G = 9.80665  # conventional standard gravity, m/s²

def descent(mass, grade, kmh, vertical, crr=.006, cda=.6, rho=1.2, tailwind=0):
    """grade=rise/horizontal; kmh is speed along road; tailwind in m/s.
    Signed aerodynamic force permits a tailwind faster than vehicle to add load.
    """
    if min(mass, grade, kmh, vertical) <= 0 or min(crr,cda,rho)<0:
        raise ValueError('positive mass/grade/speed/drop; nonnegative drag parameters')
    speed=kmh/3.6
    sin=grade/math.sqrt(1+grade*grade)
    cos=1/math.sqrt(1+grade*grade)
    seconds=vertical/(speed*sin)
    gravity=mass*G*speed*sin
    rolling=crr*mass*G*cos*speed
    relative=speed-tailwind
    aero=.5*rho*cda*relative*abs(relative)*speed
    raw=gravity-rolling-aero
    return dict(gravity_w=gravity, rolling_w=rolling, aero_w=aero,
                brake_w=max(0,raw), propulsion_w=max(0,-raw), seconds=seconds,
                potential_j=mass*G*vertical, road_j=(rolling+aero)*seconds,
                brake_j=max(0,raw)*seconds)

def split(brake_w, regen_fraction, efficiency, battery_accept_w=0, dump_cap_w=300):
    """Generator MECHANICAL share; efficiency lumps motor+controller losses.
    Assumes commanded current is reduced when DC sinks saturate (not implemented).
    Does NOT prove motor torque/current availability or low-speed braking.
    """
    if min(brake_w,battery_accept_w,dump_cap_w)<0 or not 0<=regen_fraction<=1 or not 0<efficiency<=1:
        raise ValueError('invalid power/fraction/efficiency')
    generator=min(brake_w*regen_fraction,(battery_accept_w+dump_cap_w)/efficiency)
    bus=generator*efficiency
    battery=min(bus,battery_accept_w)
    return dict(generator_w=generator,motor_controller_loss_w=generator-bus,
                dump_w=bus-battery,battery_w=battery,mechanical_w=brake_w-generator)

def resistor_bank(volts, ohms=4.7, tolerance=.05):
    if volts<0 or ohms<=0 or not 0<=tolerance<1: raise ValueError('invalid resistor input')
    return dict(series_w=volts**2/(2*ohms),series_max_w=volts**2/(2*ohms*(1-tolerance)),
                series_a=volts/(2*ohms),parallel_w=volts**2/(ohms/2))

def thermal_step(initial, ambient, watts, resistance, capacity, seconds):
    """Exact one-node RC step, K/W and J/K; NOT resistor hot-spot geometry."""
    if resistance<=0 or capacity<=0 or seconds<0 or watts<0: raise ValueError('invalid thermal input')
    steady=ambient+watts*resistance
    return steady+(initial-steady)*math.exp(-seconds/(resistance*capacity))

def rows():
    # ASSUMPTIONS: explicit sensitivity brackets, not site climate/tyre bounds.
    for mass,grade,kmh,drop,crr,cda,rho,tailwind,fraction,eta in itertools.product(
            (140,150),(.05,.10,.15),(10,20,30),(100,300,600),
            (.003,.006,.012),(.4,.6,.8),(1.,1.2,1.3),(0,5),(0,.5,1),(.6,.8,.9)):
        x=descent(mass,grade,kmh,drop,crr,cda,rho,tailwind)
        yield dict(mass_kg=mass,grade=grade,kmh=kmh,drop_m=drop,crr=crr,cda=cda,
                   rho=rho,tailwind_mps=tailwind,regen_fraction=fraction,efficiency=eta,
                   **x,**split(x['brake_w'],fraction,eta))

if __name__=='__main__':
    data=iter(rows()); first=next(data)
    writer=csv.DictWriter(sys.stdout,fieldnames=list(first)); writer.writeheader()
    writer.writerow(first); writer.writerows(data)
