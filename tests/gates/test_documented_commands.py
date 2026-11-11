"""Guards the documented test commands against false-green.

WHY THIS EXISTS
---------------
``tests/gates`` holds 221 bare module-level test functions and no
``unittest.TestCase`` classes, so ``python3 -m unittest discover -s tests/gates``
exits 0 having graded nothing. That vacuous command is how a stale "198 passed"
figure survived in this repository: it was reproducible, and it could never have
contradicted the claim.

The fix is not to make unittest work here (that would mean rewriting 221
pytest fixtures as TestCase methods for no gain). The fix is to make the
vacuous route impossible to document as if it were valid, and to fail loudly if
a bare-function suite is ever quoted with a unittest command.

WHAT THESE TESTS ASSERT
-----------------------
1. ``tests/gates`` really is a bare-function suite with zero TestCase classes —
   so the documented rule describes the tree as it is, not as it was.
2. No tracked markdown tells a reader to run ``unittest`` against ``tests/gates``.
3. The hardware suite, by contrast, does contain TestCase classes — so the
   opposite command is correct there and this rule is not accidentally applied
   to it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATES_DIR = REPO_ROOT / "tests" / "gates"
HW_TESTS_DIR = REPO_ROOT / "hardware" / "powerboard-reva" / "tests"

# Markdown that documents commands. Archive is excluded: it records an older
# project whose suite genuinely was unittest-based.
DOC_GLOBS = ("README.md", "docs/**/*.md")


def _gate_test_files() -> list[Path]:
    return sorted(p for p in GATES_DIR.glob("test_*.py"))


def _markdown_files() -> list[Path]:
    files = [REPO_ROOT / "README.md"]
    files += sorted((REPO_ROOT / "docs").rglob("*.md"))
    return [p for p in files if p.is_file()]


def test_gate_suite_is_bare_functions_not_testcases():
    files = _gate_test_files()
    assert files, "no tests/gates/test_*.py found — did the directory move?"

    classes = 0
    funcs = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        classes += len(re.findall(r"^class\s+\w+\((?:unittest\.)?TestCase\)",
                                  text, re.M))
        funcs += len(re.findall(r"^def test_", text, re.M))

    # If this ever flips, the documented rule must be revisited rather than
    # silently becoming wrong.
    assert classes == 0, (
        f"tests/gates now has {classes} TestCase class(es); the README's "
        "warning that unittest grades nothing may no longer hold")
    assert funcs > 100, f"only {funcs} gate test functions found"


def test_no_doc_tells_reader_to_run_unittest_against_tests_gates():
    """A unittest command for tests/gates is only allowed when labelled vacuous.

    The warning itself must be able to name the command — it is the thing being
    warned about. So a matching line is acceptable only if the same line, or the
    one before it, marks it as grading nothing.
    """
    vacuous_markers = ("Ran 0 tests", "grades nothing", "graded nothing",
                       "vacuous", "not the cause", "no unittest route",
                       "vacuous_run", "0 tests")
    offenders = []
    pattern = re.compile(r"discover[^\n]*tests/gates")

    for path in _markdown_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if not pattern.search(line):
                continue
            window = " ".join(lines[max(0, i - 1):i + 1]).lower()
            if any(m.lower() in window for m in vacuous_markers):
                continue
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{i + 1}")

    assert not offenders, (
        "documentation presents the unittest route for tests/gates as valid: "
        f"{offenders}. Use 'python3 -m pytest tests/gates -q', or mark the "
        "unittest command explicitly as grading nothing.")


def test_hardware_suite_does_have_testcases():
    """The hardware suite is unittest-based, so the opposite command is right."""
    files = sorted(HW_TESTS_DIR.glob("test_*.py"))
    assert files, "hardware test directory missing"

    classes = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        classes += len(re.findall(r"^class\s+\w+\((?:unittest\.)?TestCase\)",
                                  text, re.M))
    assert classes > 0, (
        "hardware suite has no TestCase classes either; the documented "
        "unittest command there would be vacuous too")


def test_readme_states_the_gate_count_from_pytest():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "pytest tests/gates" in readme, (
        "README no longer documents the pytest gate command")
    # The note must name the mechanism, not merely warn vaguely.
    assert "TestCase" in readme, (
        "README warning should explain that unittest collects TestCase "
        "classes, which is why the route is vacuous")
