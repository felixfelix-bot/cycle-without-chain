"""IDEAL behavioral OC regression: no comparator/CSA/vendor latency qualification."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHANNELS = ('GEN_SOA', 'GEN_SOB', 'GEN_SOC', 'HUB_SOA', 'HUB_SOB', 'HUB_SOC')


def simulate(channel, level, width='100u'):
    deck = ROOT / 'fast_oc_transient.cir'
    if not deck.exists(): raise RuntimeError('Missing independent fast OC transient model')
    if not shutil.which('ngspice'):
        raise RuntimeError('ngspice required; safety regression must not skip')
    text = deck.read_text().replace('.param FAULT_LEVEL=2.6 PULSE_WIDTH=100u',
                                   f'.param FAULT_LEVEL={level} PULSE_WIDTH={width}')
    for name in CHANNELS:
        text = text.replace(f'.param INJECT_{name}=0', f'.param INJECT_{name}={int(name == channel)}')
    # Temporary input remains in the owned exports namespace, not system /tmp.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cir', prefix='fast-oc-spice-',
                                     dir=ROOT / 'exports') as f:
        f.write(text)
        f.flush()
        run = subprocess.run(['ngspice', '-b', f.name], cwd=ROOT, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
    label = f'{channel.lower()}-{level}-{width}'
    (ROOT / 'exports' / f'fast-oc-spice-{label}.log').write_text(run.stdout)
    if run.returncode != 0 or re.search(r'(?im)^error|failed', run.stdout): raise RuntimeError(run.stdout)
    return {k: float(v) for k, v in re.findall(r'(?m)^([a-z_0-9]+)\s*=\s*([-+0-9.eE]+)', run.stdout)}


class FastOCSpice(unittest.TestCase):
    def assert_low(self, m, *names):
        for name in names:
            self.assertIn(name, m)
            self.assertLessEqual(m[name], .8, name)

    def assert_high(self, m, *names):
        for name in names:
            self.assertIn(name, m)
            self.assertGreaterEqual(m[name], 2., name)

    def test_all_six_inputs_both_polarities_latch_despite_stuck_mcu(self):
        for channel in CHANNELS:
            for level in (.7, 2.6):
                with self.subTest(channel=channel, level=level):
                    m = simulate(channel, level)
                    self.assert_high(m, 'armed', 'mcu_stuck_high', 'oc_recovered', 'fresh_cycle')
                    self.assert_low(m, 'startup_held', 'oc_during', 'healthy_during',
                                    'permit_after', 'gen_after', 'hub_after',
                                    'tim1_after', 'tim8_after', 'held_recovery')
                    self.assert_high(m, 'fault_latched')

    def test_saturated_output_trips_but_stuck_midpoint_is_not_diagnosed(self):
        for level in (0.0, 3.05):
            m = simulate('GEN_SOA', level)
            self.assert_low(m, 'permit_after', 'gen_after', 'hub_after')
        # A short outside low-side observability can leave SO at midpoint.
        m = simulate('GEN_SOA', 1.65)
        self.assert_high(m, 'permit_after', 'gen_after', 'hub_after')

    def test_inside_provisional_window_does_not_trip(self):
        for level in (.86, 2.44):
            m = simulate('GEN_SOA', level)
            self.assert_high(m, 'oc_during', 'permit_after', 'gen_after', 'hub_after',
                             'tim1_after', 'tim8_after', 'held_recovery')

    def test_resolved_one_microsecond_pulse_latches_in_ideal_model_only(self):
        for level in (.7, 2.6):
            m = simulate('HUB_SOC', level, '1u')
            self.assert_low(m, 'oc_during', 'permit_after', 'gen_after', 'hub_after',
                            'tim1_after', 'tim8_after', 'held_recovery')

    def test_model_explicitly_excludes_short_pulse_and_vendor_qualification(self):
        deck = ROOT / 'fast_oc_transient.cir'
        self.assertTrue(deck.exists(), 'Missing independent fast OC transient model')
        text = deck.read_text()
        for disclaimer in ('IDEAL', 'NOT vendor', 'minimum pulse', 'CSA bandwidth',
                           'propagation delay', '0.8527131783', '2.4472868217'):
            self.assertIn(disclaimer, text)


if __name__ == '__main__':
    unittest.main()
