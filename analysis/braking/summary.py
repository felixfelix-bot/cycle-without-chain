"""Regenerate the document's rounded screening tables; stdlib only."""
from model import G, descent, resistor_bank, rows, split, thermal_step

print('Pbrake=max(0,mgv*sin(theta)-Crr*mgv*cos(theta)-.5*rho*CdA*v**3)')
print('grade, km/h, brake W, seconds per 100m; m=150, Crr=.006, CdA=.6, rho=1.2, wind=0')
for grade in (.05,.10,.15):
    for speed in (10,20,30):
        x=descent(150,grade,speed,100)
        print(grade,speed,round(x['brake_w'],1),round(x['seconds'],1))
print('mgh / 1000 [kJ]')
for mass in (140,150):
    print(mass,[round(mass*G*h/1000,1) for h in (100,300,600)])
print('Stopping KE=.5*m*v**2 [J]:',.5*150*(30/3.6)**2)
print('Bank P=V**2/R; series 9.4 ohm, parallel 2.35 ohm; tolerance +/-5%')
for voltage in (36,58.4,60,65): print(voltage,resistor_bank(voltage))
print('Thermal T=Ta+P*R+(T0-Ta-P*R)*exp(-t/(R*C)); Ta=T0=40, P=300, C=900')
for r in (.1,.2,.3,.6):
    print(r,[round(thermal_step(40,40,300,r,900,t),1) for t in (60,300,600)],'steady',40+300*r)
print('Full pack, 300W dump, 150kg 15% 30km/h, requested share=1:')
for eta in (.6,.8,.9): print(eta,split(descent(150,.15,30,100)['brake_w'],1,eta))
values=[x['brake_w'] for x in rows()]
print('Sensitivity rows:',len(values),'brake W range:',min(values),max(values))
print('Required Rth=(80-40)/300 [K/W]:',(80-40)/300)
print('Dump E=P*t [kJ]:',300*600/1000,'adiabatic rise E/C [K]:',300*600/900)
print('PWM duty=Pavg/(V**2/R):',300/(60**2/9.4))
print('DC test V=sqrt(P*R):',[(p,(p*9.4)**.5) for p in (25,50,100,300)])
