"""Tests for analysis/cx/regen_recovery.py — the CX-03 regen figure.

CX-03 is a contradiction inside one document: §0/§2 of
``docs/analysis/chainless-drivetrain.md`` print 8.2 Wh capturable at 65 %
(single hop), while §12 recomputes a two-hop 0.791^2 chain to 7.9 Wh and calls
8.2 Wh superseded.  Both were still printed.

The fix is not "pick 7.9 because §12 says so" — it is to run the committed model
and see what it actually produces today.  These tests therefore (a) pin the
two-hop arithmetic, and (b) *parse the real model's stdout* so the helper and
``docs/analysis/chainless_drivetrain_model.py`` cannot drift apart.
"""

import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL = REPO_ROOT / "docs" / "analysis" / "chainless_drivetrain_model.py"
DOC = REPO_ROOT / "docs" / "analysis" / "chainless-drivetrain.md"


def _load():
    path = Path(__file__).with_name("regen_recovery.py")
    if not path.is_file():
        raise AssertionError("regen_recovery.py not implemented")
    spec = importlib.util.spec_from_file_location("regen_recovery", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _model_stdout():
    result = subprocess.run([sys.executable, str(MODEL)], capture_output=True,
                            text=True, check=True)
    return result.stdout


class RegenRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_kinetic_energy_matches_the_model(self):
        ke = self.m.kinetic_energy(94.0, 25.0)
        self.assertAlmostEqual(ke, 2266.5895, places=3)
        self.assertAlmostEqual(ke / 3600.0, 0.62961, places=5)

    def test_two_hop_chain_is_the_models_0_791_squared(self):
        r = self.m.regen_recovery(94.0, 25.0, 20, 0.86, 0.92)
        self.assertAlmostEqual(r["one_hop"], 0.7912, places=6)
        self.assertAlmostEqual(r["round_trip"], r["one_hop"] ** 2, places=12)
        self.assertAlmostEqual(r["stored_wh_per_stop"], 0.49815, places=5)
        self.assertAlmostEqual(r["back_at_wheel_wh_per_stop"], 0.39413,
                               places=5)
        self.assertAlmostEqual(r["total_wh"], 7.88266, places=4)

    def test_single_hop_65_percent_reproduces_the_withdrawn_figure(self):
        # If this drifts, the "superseded" note in the document is describing a
        # figure nobody can reproduce any more.
        r = self.m.regen_recovery(94.0, 25.0, 20, 0.86, 0.92)
        self.assertAlmostEqual(r["single_hop_65_wh"], 8.18491, places=4)

    def test_helper_agrees_with_the_committed_model_stdout(self):
        out = _model_stdout()
        back = re.search(r"x 0\.7912? \(battery->wheel\) = \s*(\d+) J = "
                         r"([\d.]+) Wh back at wheel", out)
        total = re.search(r"20 stops -> ([\d.]+) Wh usable\s*= ([\d.]+) % of the "
                          r"10 km trip energy", out)
        self.assertIsNotNone(back, out[-2000:])
        self.assertIsNotNone(total, out[-2000:])
        r = self.m.regen_recovery(94.0, 25.0, 20, 0.86, 0.92)
        self.assertAlmostEqual(r["back_at_wheel_wh_per_stop"],
                               float(back.group(2)), places=3)
        self.assertAlmostEqual(r["total_wh"], float(total.group(1)), places=1)
        self.assertAlmostEqual(r["percent_of_trip"], float(total.group(2)),
                               places=1)

    def test_trip_energy_denominator_is_the_models_55_6_wh(self):
        r = self.m.regen_recovery(94.0, 25.0, 20, 0.86, 0.92)
        self.assertAlmostEqual(r["trip_wh"], 55.6, delta=0.05)
        self.assertAlmostEqual(r["percent_of_trip"], 14.2, delta=0.05)

    def test_rejects_impossible_inputs(self):
        with self.assertRaises(ValueError):
            self.m.regen_recovery(0.0, 25.0, 20, 0.86, 0.92)
        with self.assertRaises(ValueError):
            self.m.regen_recovery(94.0, -1.0, 20, 0.86, 0.92)
        with self.assertRaises(ValueError):
            self.m.regen_recovery(94.0, 25.0, 20, 1.2, 0.92)


class DocumentStatusTest(unittest.TestCase):
    """The withdrawn figure must be marked, not deleted, and only one current."""

    def setUp(self):
        self.text = DOC.read_text(encoding="utf-8")

    @staticmethod
    def _paragraphs(text):
        block = []
        for line in text.splitlines():
            if line.strip():
                block.append(line)
            elif block:
                yield "\n".join(block)
                block = []
        if block:
            yield "\n".join(block)

    def test_withdrawn_figure_is_still_present_and_marked(self):
        paragraphs = [p for p in self._paragraphs(self.text) if "8.2 Wh" in p]
        self.assertTrue(paragraphs, "the withdrawn figure was deleted, not marked")
        for paragraph in paragraphs:
            self.assertIn("superseded", paragraph.lower(),
                          f"unmarked withdrawn figure: {paragraph!r}")

    def test_every_withdrawn_mention_points_at_section_12(self):
        # Mentions *inside* §12 are already at the correction; mentions before it
        # must send the reader there.
        before_s12 = self.text.split("## §12", 1)[0]
        for paragraph in self._paragraphs(before_s12):
            if "8.2 Wh" not in paragraph:
                continue
            self.assertIn("§12", paragraph,
                          f"no pointer to §12 near: {paragraph!r}")

    def test_section_12_keeps_the_current_figure(self):
        section = self.text.split("## §12", 1)[1]
        self.assertIn("7.9 Wh", section)
        self.assertIn("superseded", section.lower())


if __name__ == "__main__":
    unittest.main()
