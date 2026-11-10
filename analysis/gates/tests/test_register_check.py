"""Tests for analysis/gates/register_check.py — the open-gates register linter.

The linter is a *document consistency* check: it proves the register table is
complete enough to be read (every row has a bucket in {A,B,C,D}, a citation and
a unique ID, and the summary counts agree with the rows). It is not a proof
that any engineering claim in the register is correct.

Exit-code contract, exercised here through the real CLI:

=====  ==================================================================
0      PASS
1      FAIL: row-level fault or summary/row count mismatch
2      NOT RUN: missing file, missing gate table, missing summary table
=====  ==================================================================
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "analysis" / "gates" / "register_check.py"
REGISTER = REPO_ROOT / "docs" / "design" / "open-gates-register.md"

HEADER = (
    "| ID | Subsystem | What is unproven | Consequence if wrong | Bucket "
    "| Evidence that closes it | Status | Source |\n"
    "|---|---|---|---|---|---|---|---|\n"
)

SUMMARY_HEADER = (
    "\n## Bucket summary\n\n"
    "| Bucket | Meaning | Count |\n"
    "|---|---|---|\n"
)


def row(gate_id="TST-01", bucket="A", source="precharge-review.md §Verdict"):
    return (
        f"| {gate_id} | test | something | bad things | {bucket} "
        f"| a calculation | open | {source} |\n"
    )


def build(rows, counts=None):
    """Assemble a synthetic register with a summary table."""
    if counts is None:
        counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for line in rows:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 8 and cells[4] in counts:
                counts[cells[4]] += 1
    summary = SUMMARY_HEADER + "".join(
        f"| {b} | meaning | {counts[b]} |\n" for b in ("A", "B", "C", "D")
    )
    return "# Synthetic register\n\n" + HEADER + "".join(rows) + summary


class RegisterCheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def run_check(self, text, optimized=False):
        path = self.tmp / "register.md"
        path.write_text(text, encoding="utf-8")
        cmd = [sys.executable]
        if optimized:
            cmd.append("-O")
        cmd += [str(SCRIPT), str(path)]
        return subprocess.run(cmd, capture_output=True, text=True)

    def assert_fails(self, result, needle):
        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        self.assertIn(needle, result.stderr + result.stdout)

    # -- the real document ------------------------------------------------
    def test_real_register_passes(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(REGISTER)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_real_register_passes_optimized(self):
        result = subprocess.run(
            [sys.executable, "-O", str(SCRIPT), str(REGISTER)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    # -- row-level faults -------------------------------------------------
    def test_empty_bucket_fails(self):
        text = build([row(bucket="")], counts={"A": 1, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "empty bucket")

    def test_bucket_outside_abcd_fails(self):
        text = build([row(bucket="E")], counts={"A": 1, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "not one of A/B/C/D")

    def test_bucket_with_prose_fails(self):
        text = build([row(bucket="A maybe")], counts={"A": 1, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "not one of A/B/C/D")

    def test_missing_citation_fails(self):
        text = build([row(source="")], counts={"A": 1, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "no citation")

    def test_citation_without_document_fails(self):
        text = build([row(source="see the review")], counts={"A": 1, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "no citation")

    def test_citation_without_section_fails(self):
        text = build([row(source="precharge-review.md")], counts={"A": 1, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "no citation")

    def test_duplicate_id_fails(self):
        rows = [row(gate_id="TST-01"), row(gate_id="TST-01")]
        text = build(rows, counts={"A": 2, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "duplicate ID")

    def test_short_row_fails(self):
        bad = "| TST-01 | test | only four cells |\n"
        text = build([bad], counts={"A": 0, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "column")

    # -- summary consistency ----------------------------------------------
    def test_bucket_count_mismatch_fails(self):
        text = build([row(bucket="A")], counts={"A": 5, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "summary count")

    def test_missing_summary_bucket_fails(self):
        text = build([row(bucket="C")], counts={"A": 0, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text), "summary count")

    # -- cannot grade ------------------------------------------------------
    def test_missing_file_is_not_run(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(self.tmp / "nope.md")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_missing_gate_table_is_not_run(self):
        result = self.run_check("# nothing here\n")
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    def test_missing_summary_table_is_not_run(self):
        text = "# Synthetic\n\n" + HEADER + row()
        result = self.run_check(text)
        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)

    # -- the check is not vacuous under -O --------------------------------
    def test_faults_still_detected_under_optimized(self):
        text = build([row(bucket="E")], counts={"A": 1, "B": 0, "C": 0, "D": 0})
        self.assert_fails(self.run_check(text, optimized=True), "not one of A/B/C/D")


if __name__ == "__main__":
    unittest.main()
