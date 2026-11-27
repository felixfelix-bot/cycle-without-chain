"""Provisional arithmetic, not a validated drivetrain model."""
from math import pi
print(f"crank torque=250/(80*2*pi/60)={250/(80*2*pi/60):.2f} Nm")
for p in (250,500):
 print(f"generator torque={p}/(2000*2*pi/60)={p/(2000*2*pi/60):.3f} Nm")
for kv in (41.3,33.4):
 print(f"approx EMF=2000/{kv}={2000/kv:.2f} V; conventions unverified")
print(f"bus current=500/36={500/36:.2f} A")
print(f"Li-ion full=13*4.2={13*4.2:.1f} V; LFP=16*3.65={16*3.65:.1f} V")
print(f"bridge conduction=3*15**2*(.0049*2)={3*15**2*.0049*2:.3f} W; hot factor2 assumed")
print(f"gate power=12*48e-9*10*20000={12*48e-9*10*20000:.4f} W")
print(f"chopper R=60**2/500={60**2/500:.1f} ohm; energy=500*10={500*10} J")
assert 30*.002*20 == 1.2
