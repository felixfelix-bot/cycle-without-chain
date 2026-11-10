"""Component acceptance envelopes, not guaranteed manufacturer maxima.
Source/conditions: docs/design/precharge-power-sources.md. No price data.
"""
from math import ceil
EFFICIENCY_FLOOR = .60  # qualification requirement, not datasheet minimum
CTRL_LOADS_A = dict(tpsi3052_pair=2*.050, lm339b_pair=2*.0016,
                   tlv9002=2*.000085, tlc555=.001, latches=3*.000010,
                   supervisor_logic_reference=.005)
SINK_LOADS_W = dict(r39=12**2/1000, reference=12*(12-2.5)/4700,
                   lm339b=12*.0016, ucc27511=12*.001,
                   monitor=12**2/40000, safety_ldo=12*(.006+.005),
                   main_proof_analog=.10)
# Analog proof candidate is fed by SINK12 (NOT nonexistent CTRL12).
# .10 W includes OPA4197/TLV1702/reference allowance; qualify actual max.
def roundup(w):
    return ceil(w*10)/10
CTRL_INPUT_W = roundup(3.3*sum(CTRL_LOADS_A.values())/EFFICIENCY_FLOOR+.10)
SINK_INPUT_W = roundup(sum(SINK_LOADS_W.values())/EFFICIENCY_FLOOR+.30)
# .10 tolerance/bias reserve + .20 safety-logic/startup uncertainty reserve.
BUS_LEAKAGE_W = .04
SINK_STARTUP_W = 2.0
SINK_STARTUP_S = .030
