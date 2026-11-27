"""Conservative screening envelope; not certified safety timing."""
import itertools, math, json

def thresholds(rt=225000, rb=10000, rh=330000, ref=2.5, high=3.3, low=.2):
    gain=1+rt/rb+rt/rh
    return ref*gain-low*rt/rh, ref*gain-high*rt/rh

def corners():
    # .1% initial + 25ppm/K * 50K; reference .1% + 100ppm/K *50K
    pairs=[]
    for a,b,c,d,e,f in itertools.product([-1,1], repeat=6):
        rt=225000*(1+a*.00225); rb=10000*(1+b*.00225); rh=330000*(1+c*.00225)
        ref=2.5*(1+d*.006)+e*(.0055+50e-9*10000)
        pairs.append(thresholds(rt,rb,rh,ref,3.3*(1+f*.04),.55 if f>0 else 0))
    return dict(on_min=min(x[0] for x in pairs),on_max=max(x[0] for x in pairs),off_min=min(x[1] for x in pairs),off_max=max(x[1] for x in pairs))

def latch_next(fault_latched, healthy, reset):
    return not healthy or (fault_latched and not reset)

def energy_rise(v,c,p,t):
    if v<0 or c<=0 or p<0 or t<0: raise ValueError('invalid physical input')
    return math.sqrt(v*v+2*p*t/c)

if __name__=='__main__':
    print(json.dumps(dict(nominal=thresholds(),corners=corners(),bus_after_10us_500W=energy_rise(60,.0001,500,.00001)),indent=2))
