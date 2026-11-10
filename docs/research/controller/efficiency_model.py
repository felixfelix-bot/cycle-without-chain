"""Provisional allocation; no measured efficiencies. Run with Python 3 stdlib."""
import csv
import math
from pathlib import Path
P = Path(__file__).resolve().parent
stages = [('crank gearing', .98), ('generator', .93), ('rectifier', .98), ('bus wiring', .995), ('auxiliary fixed W', 1.5), ('motor inverter', .98), ('motor and final transmission', .93)]
power = 150.0
rows = []
for name, value in stages:
    before = power
    power = power - value if name == 'auxiliary fixed W' else power * value
    rows.append(dict(stage=name, assumption=value, kind='estimate', source='design-envelope.md: allocation not measurements', output_W=power, loss_W=before-power))
assert abs(sum(r['loss_W'] for r in rows) + power - 150) < 1e-9
with (P/'efficiency-budget.csv').open('w', newline='') as f:
    w=csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader();w.writerows(rows)
a=150*.98*.98*.995*.98
b=1.5*.98
required=lambda target:(b+math.sqrt(b*b+4*a*target))/(2*a)
lines=[f'Wheel: {power:.6f} W; efficiency: {power/150:.6%}', f'Equal machine efficiency for 80%: {required(120):.6%}', f'Equal machine efficiency for assumed 97% mechanical baseline: {required(145.5):.6%}']
for machine in [.85,.90,.93,.95]:
    out=a*machine**2-b*machine
    lines.append(f'Both machines {machine:.0%}: {out:.6f}W, {out/150:.6%}')
energy=.5*.001*(62**2-54.6**2)
lines.append(f'1mF energy headroom: {energy:.6f}J; at 150W {energy/150*1000:.6f}ms; at 500W {energy/500*1000:.6f}ms')
assert .929 < required(120) < .931
assert required(145.5)>1
text='\n'.join(lines)+'\n'
(P/'model-results.txt').write_text(text)
print(text)
