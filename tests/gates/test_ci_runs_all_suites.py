"""Guards that CI actually runs every test suite the repo declares.

WHY THIS EXISTS
---------------
``.github/workflows/release-gates.yml`` ran only ``pytest tests/gates``. The
hardware suite (66+ tests, including two ngspice decks that ``raise
RuntimeError`` rather than skip) and the whole ``analysis/**`` tree (200+
closed-form budget tests) were never executed by any workflow. Both passed
locally, so nothing was red -- but a regression in the schematic generator, a
calculator or a SPICE deck would have merged with a green tick.

That is the same class of defect as a vacuous test command: the lane looks
green because the lane graded less than the reader assumes. A comment saying
"we run everything" is not a control, so this test reads the workflow file and
asserts the suites are wired.

WHAT THESE TESTS ASSERT
-----------------------
1. Every suite directory with tests is named in the workflow.
2. ``ngspice`` is installed in CI. Without it the two SPICE suites fail rather
   than skip, so a runner missing it must fail loudly, not silently pass.
3. No suite step is neutralised by ``|| true``, ``continue-on-error`` or a
   piped ``tail``/``head`` that would swallow the exit code.
4. The negative control: a workflow with a suite removed IS rejected, so this
   checker is known to discriminate rather than always passing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-gates.yml"

# Suites that must be executed by CI, with the directory that must appear in the
# workflow. Adding a suite to the repo without wiring it here is the bug.
REQUIRED_SUITES = {
    "gate suite": "tests/gates",
    "hardware suite": "hardware/powerboard-reva/tests",
    "analysis suite": "analysis/",
}


def _workflow_text() -> str:
    if not WORKFLOW.exists():
        pytest.fail(f"release workflow missing: {WORKFLOW}")
    return WORKFLOW.read_text()


def _run_steps(text: str) -> list[str]:
    """Return the ``run:`` payloads, which is where a suite is actually invoked."""
    return re.findall(r"(?ms)^\s+run:\s*(?:\|-?\s*\n(.*?)(?=^\s{6}- name:|^\s{6}- uses:|\Z))", text)


def test_every_suite_is_named_in_the_workflow():
    text = _workflow_text()
    missing = [name for name, needle in REQUIRED_SUITES.items() if needle not in text]
    assert not missing, (
        f"CI does not run: {missing}. These suites pass locally, so dropping them "
        f"from the workflow makes a regression invisible while the lane stays green."
    )


def test_ngspice_is_installed_in_ci():
    text = _workflow_text()
    assert re.search(r"install[^\n]*ngspice", text), (
        "CI never installs ngspice. The two SPICE suites raise RuntimeError rather "
        "than skip when it is absent, so this must be installed or the hardware "
        "suite fails for the wrong reason."
    )
    # Installing it and then swallowing a failure is the same as not installing it.
    install_block = [s for s in _run_steps(text) if "ngspice" in s]
    assert install_block, "ngspice named but not in a run step"
    for block in install_block:
        assert "|| true" not in block, "ngspice install is neutralised by `|| true`"


def test_no_suite_step_swallows_its_exit_code():
    text = _workflow_text()
    for block in _run_steps(text):
        if "pytest" not in block:
            continue
        assert "|| true" not in block, f"pytest step neutralised:\n{block}"
        assert "continue-on-error" not in block, f"pytest step neutralised:\n{block}"
        for line in block.splitlines():
            if "pytest" in line:
                assert "| tail" not in line and "| head" not in line, (
                    f"pytest output piped, so the step reports the pipe's status not the "
                    f"test suite's:\n{line}"
                )


def test_checker_rejects_a_workflow_with_a_suite_removed():
    """Negative control: prove the assertions above can fail."""
    text = _workflow_text()
    crippled = text.replace(
        "run: python3 -m pytest hardware/powerboard-reva/tests -q",
        "run: echo 'skipped'",
    )
    assert crippled != text, "control could not cripple the workflow; the assertion is vacuous"
    missing = [name for name, needle in REQUIRED_SUITES.items() if needle not in crippled]
    assert "hardware suite" in missing, (
        "removing the hardware suite from the workflow did not register as missing, "
        "so test_every_suite_is_named_in_the_workflow could never fail"
    )
