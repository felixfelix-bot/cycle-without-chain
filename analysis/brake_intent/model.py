"""Normalized brake-request state model, NOT firmware or electrical proof."""
from dataclasses import dataclass
import math
from typing import cast


@dataclass(frozen=True)
class Lever:
    switch: bool | None
    hall: float | None

    def plausible(self) -> bool:
        # None represents a diagnosed open wire, not an ordinary released switch.
        return (type(self.switch) is bool and self.hall is not None
                and math.isfinite(self.hall) and 0 <= self.hall <= 1
                and self.switch == (self.hall > 0))


@dataclass(frozen=True)
class Inputs:
    left: Lever
    right: Lever
    throttle: float = 0.0
    battery_accepts: bool = True
    dump_available_cool: bool = True
    estop: bool = False
    hard_overcurrent: bool = False
    watchdog_expired: bool = False
    manual_reset: bool = False
    emergency_overvoltage: bool = False


@dataclass(frozen=True)
class Outputs:
    gate_enabled: bool
    fault_latched: bool
    positive_allowed: bool
    negative_allowed: bool
    torque_command: float
    regen: float
    dump_command: float
    emergency_clamp: bool
    uncommanded_drag_possible: bool


class BrakeIntent:
    def __init__(self):
        self.fault_latched = False

    def step(self, inputs: Inputs) -> Outputs:
        """Advance one idealized sample, including the independent hardware gates."""
        plausible = inputs.left.plausible() and inputs.right.plausible()
        kill = inputs.estop or inputs.hard_overcurrent or inputs.watchdog_expired
        request = max(cast(float, inputs.left.hall), cast(float, inputs.right.hall)) if plausible else 0.0
        if kill or not plausible:
            self.fault_latched = True
        elif inputs.manual_reset and request == 0 and inputs.throttle == 0:
            self.fault_latched = False

        gate = not (kill or self.fault_latched)
        positive = gate and request == 0
        negative = gate and request > 0 and (inputs.battery_accepts or inputs.dump_available_cool)
        regen = request if negative and inputs.battery_accepts else 0.0
        dump = request if negative and not inputs.battery_accepts else 0.0
        torque = -(regen + dump)
        if positive:
            torque = max(0.0, min(1.0, inputs.throttle))
        return Outputs(gate, self.fault_latched, positive, negative, torque,
                       regen, dump, inputs.emergency_overvoltage,
                       inputs.emergency_overvoltage)
