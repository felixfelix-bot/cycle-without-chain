# Executable brake intent model — not firmware

Run from this directory with Python 3.10+ (stdlib only):

```
python3 -B test_model.py
python3 -B -O test_model.py
```

`model.py` is a normalized, discrete-time state/permission specification. It does not establish hardware safety, thermal capacity, stopping distance, watchdog latency, switching behavior, or analog plausibility thresholds. Mechanical brakes remain necessary, particularly when no electrical sink is available.

## Inputs and trust boundaries

Both levers must be healthy. Either lever can request braking, using the larger normalized Hall demand (0..1). A released switch must pair with zero Hall demand; an asserted switch must pair with positive Hall demand. Actual Hall deadbands, hysteresis, calibration and disagreement timing must be engineered separately. `None` means a **diagnosed** open circuit; this requires supervised wiring. An ordinary unsupervised switch cannot distinguish released from broken wire. Nonfinite/out-of-range Hall readings fail closed. Correlated switch/Hall failures that agree are not detected by this abstraction.

`battery_accepts` is an independently established charge-acceptance permission (cell voltage, temperature, charge current limits and pack/BMS state), never inferred from the brake request. `dump_available_cool` means a functioning dump with verified thermal capacity, not merely a commanded MOSFET. Both are idealized trusted boolean inputs, not controllers implemented here. Throttle is a normalized valid 0..1 upstream demand.

## Policy

| Conditions | Positive torque | Battery regen | Commanded dump braking |
|---|---|---|---|
| Healthy, no brake | Allowed | Zero | Zero |
| Brake, battery accepts | Forbidden | Requested amount | Zero (battery priority) |
| Brake, battery refuses, cool dump available | Forbidden | Zero | Requested amount |
| Brake, battery refuses, dump hot/unavailable | Forbidden | Zero | Zero |
| Any sensor fault or hardware kill | Forbidden | Zero | Zero |

Disagreement/open-wire faults and E-stop, hard overcurrent or expired external watchdog latch the gate inhibit. Returning signals to healthy does not restart. A manual reset is honored only when both levers are healthy/released, throttle is zero, and all kills are clear; a simultaneous fault wins over reset. Reset is an abstract explicit operator event, not an auto-clear timer.

The external watchdog, hard-OC comparator and E-stop gate are modeled as hardware-dominant inputs. The stuck-MCU tests hold a high torque demand while asserting the watchdog kill. This proves the model's precedence only: real hardware must remove gate enable independently of MCU instruction execution. Calling `step()` in software is not such an implementation.

Emergency overvoltage clamping is **separate** from commanded braking: `emergency_clamp` and `uncommanded_drag_possible` can be true with no rider request, a hot dump, or disabled inverter gates. This represents an independent protective path that may induce drag; it is not permission to command normal dump braking. The model makes no promise that this path can absorb unlimited energy or survive overheating. Clamp component sizing, topology, thermal protection and residual passive drag need separate physical validation.

## Test evidence

Tests were written before `model.py`. `red.log` records 8 intentional assertion failures because the implementation was absent (not an import crash). `green.log` and `optimized.log` record successful normal and optimized executions. All checks use unittest assertions, so `python -O` does not remove them. Tests cover each lever, both levers, full pack, hot dump, both sinks unavailable, missing/invalid sensors, latch/reset, each independent kill with/without braking, and emergency-clamp independence.
