"""Implemented resistor network, ideal buffer: no force curve or SPICE claim."""
import math
import json

def adc(r):
    if r < 0: raise ValueError('negative sensor resistance')
    return 3.3*10000/(r+21000)*10000/11004.5

def results():
    return {'model':'ideal DC and first-order RC, not measured or vendor SPICE',
            'adc_V':{str(r):adc(r) for r in [math.inf,1e7,1e6,1e5,1e4,1e3,100,0]},
            'sense_tau_max_s':10000*100e-9,
            'adc_tau_s':(1004.5*10000/11004.5)*100e-9,
            'sense_half_lsb_settle_s':math.log(8192)*10000*100e-9,
            'off_discharge_tau_s':10000*100e-9,
            'off_leakage_V':2e-6*10100,
            'return_ground_fault_current_A':3.465/9900}
if __name__ == '__main__': print(json.dumps(results(),indent=2))
