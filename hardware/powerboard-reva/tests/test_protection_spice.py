"""Executable ideal-logic SPICE regression; no vendor/timing qualification."""
import pathlib
import re
import shutil
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

def simulate(fixture, log):
    if not shutil.which("ngspice"):
        raise RuntimeError("ngspice is required, not a skipped safety test")
    run = subprocess.run(["ngspice", "-b", str(ROOT / fixture)], cwd=ROOT,
                         text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (ROOT / "exports" / log).write_text(run.stdout)
    if run.returncode or re.search(r"(?im)^error|failed", run.stdout):
        raise AssertionError(run.stdout)
    return {k: float(v) for k, v in re.findall(
        r"(?m)^([a-z_]+)\s*=\s*([-+0-9.eE]+)", run.stdout)}

class ProtectionSpice(unittest.TestCase):
    def test_corrected_restart_contract(self):
        m = simulate("protection_transient.cir", "restart-corrected-spice.log")
        safe = ("initial_safe", "held_high_startup", "fault_immediate", "held_after_fault",
                "brownout_safe", "supervisor_wait", "held_after_brownout",
                "low_through_recovery", "first_rise_rejected", "bounce_rejected",
                "stuck_low_safe", "stuck_high_safe")
        armed = ("fresh_cycle_arms", "fresh_after_fault", "fresh_after_brownout",
                 "fresh_after_low", "fresh_after_bounce")
        for name in safe:
            with self.subTest(name=name):
                self.assertIn(name, m)
                self.assertLessEqual(m[name], .8, name)
        for name in armed:
            with self.subTest(name=name):
                self.assertIn(name, m)
                self.assertGreaterEqual(m[name], 2., name)

    def test_old_held_reset_is_negative_control(self):
        m = simulate("tests/fixtures/protection_old_held_reset.cir", "restart-old-held-reset-spice.log")
        self.assertGreater(m["held_after_fault"], 2., "old level-reset defect must reproduce")
        self.assertLess(m["disabled_during_reset_fault"], .8)

if __name__ == "__main__":
    unittest.main()
