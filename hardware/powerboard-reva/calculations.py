"""Screening arithmetic only: not a transient/thermal simulation or qualification.
Sources/assumptions: docs/evaluation/custom-powerboard-concept.md; docs/mcu-timing-review.md.
Precharge example is NOT a selected fitted circuit. ADC excludes settling/blanking overhead.
"""
import json
import math


def envelope():
    return dict(bus_A=500/36, shunt_W=30**2*.002,
                adc_low_V=1.65-30*.002*20, adc_high_V=1.65+30*.002*20,
                dump_ohm=60**2/500, dump_J=500*10,
                vm_static_margin_V=75-12, vds_static_margin_V=100-58.4)


def precharge(volts, farads, ohms):
    if min(volts, farads, ohms) <= 0:
        raise ValueError('positive physical inputs required')
    return dict(initial_A=volts/ohms, resistor_J=.5*farads*volts**2,
                initial_W=volts**2/ohms, time_99_s=-math.log(.01)*ohms*farads)


def adc_window(clock_hz, sample_cycles, conversion_cycles, ranks):
    if min(clock_hz, sample_cycles, conversion_cycles, ranks) <= 0:
        raise ValueError('positive timing inputs required')
    return ranks*(sample_cycles+conversion_cycles)/clock_hz


if __name__ == '__main__':
    print(json.dumps(dict(screening=envelope(),
          illustrative_precharge=precharge(58.4, .001, 100),
          illustrative_adc_seconds=adc_window(42.5e6, 24.5, 12.5, 3)), indent=2))
