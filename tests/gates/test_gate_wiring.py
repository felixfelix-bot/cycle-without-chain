"""TOOL-01: the release gates must run without a human remembering to type it.

Two wirings are graded here:

* a local one-command runner (``tools/gates/run_release_gates.py``) that plans
  which gates the tree can actually support, runs the ones it can, and reports
  the rest as ``NOT RUN`` with an explicit reason;
* the GitHub Actions workflow that calls that same script, so CI and a human run
  one code path.

What is *not* graded here: GitHub. Nothing in this file observes a workflow
run. These tests prove the workflow file declares the right triggers, calls the
tested script, and has no masking switch that could turn a failed gate green.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gate_support import REPO_ROOT, netlist_sexpr, netlist_xml, write

SCRIPT = REPO_ROOT / "tools" / "gates" / "run_release_gates.py"
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
BOARD = REPO_ROOT / "hardware" / "powerboard-reva"

NETS = {
    "VIN": [("R1", "1"), ("C1", "1")],
    "GND": [("R1", "2"), ("C1", "2")],
}


def _fake_repo(tmp_path, *, xml_nets=None, net_nets=None, board=False):
    """A repo-shaped tree holding only what the gates read from the board dir."""
    root = tmp_path / "repo"
    exports = root / "hardware" / "powerboard-reva" / "exports"
    exports.mkdir(parents=True)
    write(exports / "ctrl-supply.xml", netlist_xml(NETS if xml_nets is None else xml_nets))
    write(exports / "powerboard-reva.net",
          netlist_sexpr(NETS if net_nets is None else net_nets))
    write(root / "hardware" / "powerboard-reva" / "pin-net-map.csv",
          "ref,pin,pin_name,net,sheet\n"
          + "".join("R1,1,,VIN,s\nR1,2,,GND,s\nC1,1,,VIN,s\nC1,2,,GND,s\n"))
    if board:
        write(root / "hardware" / "powerboard-reva" / "powerboard-reva.kicad_pcb",
              "(kicad_pcb (version 20240108) (generator pcbnew))\n")
    return root


def _run_script(args, cwd=None, extra_env=None):
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONPATH"] = str(REPO_ROOT)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run([sys.executable, str(SCRIPT), *[str(a) for a in args]],
                          cwd=str(cwd or REPO_ROOT), capture_output=True, text=True,
                          env=env, timeout=300)
    payload = None
    for line in reversed(proc.stdout.strip().splitlines()):
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    return proc, payload


# ------------------------------------------------------------- local runner

def test_one_command_runs_the_gates_and_reports_what_it_cannot_run(tmp_path):
    repo = _fake_repo(tmp_path)
    summary = tmp_path / "summary.md"
    proc, payload = _run_script(["--repo-root", repo, "--summary-file", summary])
    assert proc.returncode == 2, proc.stdout + proc.stderr  # NOT RUN blocks
    assert payload["gate"] == "run_release_gates"
    assert payload["verdict"] == "NOT RUN"
    verdicts = {gate: entry["verdict"] for gate, entry in payload["results"].items()}
    assert verdicts["netlist_parity"] == "PASS"
    assert verdicts["native_reports"] == "NOT RUN"
    assert "board" in payload["results"]["native_reports"]["reason"].lower()

    text = summary.read_text()
    assert "netlist_parity" in text and "PASS" in text
    assert "NOT RUN" in text
    assert "kicad" in text.lower() or "board" in text.lower()


def test_the_one_command_is_the_documented_one():
    """The README must name the exact command the tests exercise."""
    readme = (REPO_ROOT / "tools" / "gates" / "README.md").read_text()
    assert "tools/gates/run_release_gates.py" in readme
    assert "--ci" in readme


def test_failing_gate_fails_the_runner(tmp_path):
    """A split injected into the XML alone is a FAIL, not a green run."""
    split = {name: list(nodes) for name, nodes in NETS.items()}
    split["VIN_SENSE"] = [("C1", "1")]
    split["VIN"] = [("R1", "1")]
    repo = _fake_repo(tmp_path, xml_nets=split)
    # the CSV expectation must still describe the split-free netlist
    write(repo / "hardware" / "powerboard-reva" / "pin-net-map.csv",
          "ref,pin,pin_name,net,sheet\n"
          "R1,1,,VIN,s\nR1,2,,GND,s\nC1,1,,VIN,s\nC1,2,,GND,s\n")
    summary = tmp_path / "summary.md"
    proc, payload = _run_script(["--repo-root", repo, "--summary-file", summary])
    assert proc.returncode == 1, proc.stdout
    assert payload["verdict"] == "FAIL"
    assert payload["failed"] == ["netlist_parity"]
    assert "FAIL" in summary.read_text()


def test_ci_mode_is_green_only_for_the_gates_that_ran(tmp_path):
    repo = _fake_repo(tmp_path)
    summary = tmp_path / "summary.md"
    proc, payload = _run_script(["--repo-root", repo, "--ci", "--summary-file", summary])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["not_run"] == ["native_reports", "release_manifest"]
    text = summary.read_text()
    assert "NOT RUN" in text
    # The reason must be the real one, not a shrug.
    assert "no board" in text.lower() or "board file" in text.lower()


def test_ci_mode_never_turns_a_failure_green(tmp_path):
    """The anti-greenwash control: --ci relaxes NOT RUN only, never FAIL."""
    split = {name: list(nodes) for name, nodes in NETS.items()}
    split["GND_SENSE"] = [("C1", "2")]
    split["GND"] = [("R1", "2")]
    repo = _fake_repo(tmp_path, net_nets=split)
    write(repo / "hardware" / "powerboard-reva" / "pin-net-map.csv",
          "ref,pin,pin_name,net,sheet\n"
          "R1,1,,VIN,s\nR1,2,,GND,s\nC1,1,,VIN,s\nC1,2,,GND,s\n")
    proc, payload = _run_script(["--repo-root", repo, "--ci"])
    assert proc.returncode == 1, proc.stdout
    assert payload["verdict"] == "FAIL"


def test_missing_board_is_not_run_with_a_reason_naming_the_board(tmp_path):
    repo = _fake_repo(tmp_path)
    proc, payload = _run_script(["--repo-root", repo])
    reason = payload["results"]["native_reports"]["reason"]
    assert "kicad_pcb" in reason or "board" in reason.lower()


def test_board_present_but_tool_absent_is_not_run_naming_the_tool(tmp_path):
    repo = _fake_repo(tmp_path, board=True)
    proc, payload = _run_script(["--repo-root", repo,
                                 "--kicad-cli", str(tmp_path / "no-such-kicad-cli")])
    result = payload["results"]["native_reports"]
    assert result["verdict"] == "NOT RUN"
    assert "kicad-cli" in result["reason"]


def test_release_manifest_without_a_packet_is_not_run(tmp_path):
    repo = _fake_repo(tmp_path)
    proc, payload = _run_script(["--repo-root", repo])
    result = payload["results"]["release_manifest"]
    assert result["verdict"] == "NOT RUN"
    assert "manifest" in result["reason"].lower()


def test_runner_works_from_another_cwd(tmp_path):
    repo = _fake_repo(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    proc, payload = _run_script(["--repo-root", repo, "--ci"], cwd=elsewhere)
    assert proc.returncode == 0, proc.stderr
    assert payload["results"]["netlist_parity"]["verdict"] == "PASS"


def test_summary_lists_every_selected_gate(tmp_path):
    repo = _fake_repo(tmp_path)
    summary = tmp_path / "summary.md"
    _proc, payload = _run_script(["--repo-root", repo, "--ci", "--summary-file", summary])
    text = summary.read_text()
    for gate in ("native_reports", "netlist_parity", "release_manifest"):
        assert gate in text
    assert "| gate |" in text.lower()


def test_gate_selection_limits_what_runs(tmp_path):
    repo = _fake_repo(tmp_path)
    proc, payload = _run_script(["--repo-root", repo, "--ci", "--gate", "netlist_parity"])
    assert proc.returncode == 0, proc.stderr
    assert list(payload["results"]) == ["netlist_parity"]
    assert payload["not_run"] == []


def test_unrunnable_selection_is_not_run_not_a_crash(tmp_path):
    repo = _fake_repo(tmp_path)
    proc, payload = _run_script(["--repo-root", repo, "--ci", "--gate", "native_reports"])
    assert payload["verdict"] == "NOT RUN"
    assert payload["results"]["native_reports"]["verdict"] == "NOT RUN"


def test_real_tree_parity_gate_passes_on_the_committed_artifacts(tmp_path):
    """The wiring must be green on the artifacts actually committed here."""
    summary = tmp_path / "summary.md"
    proc, payload = _run_script(["--ci", "--summary-file", summary,
                                 "--gate", "netlist_parity"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert payload["results"]["netlist_parity"]["verdict"] == "PASS"
    assert payload["results"]["netlist_parity"]["checks_passed"] > 0


# ---------------------------------------------------------------- the workflow

def _workflow():
    files = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    assert files, "no workflow file under .github/workflows"
    matching = [path for path in files if "run_release_gates" in path.read_text()]
    assert matching, "no workflow invokes tools/gates/run_release_gates.py"
    return matching[0], yaml.safe_load(matching[0].read_text())


def test_workflow_runs_on_push_and_pull_request():
    _path, doc = _workflow()
    # `on` is parsed as the boolean True by YAML 1.1 loaders; accept both keys.
    triggers = doc.get("on", doc.get(True))
    assert triggers is not None
    if isinstance(triggers, str):
        triggers = {triggers: {}}
    assert "push" in triggers
    assert "pull_request" in triggers


def test_workflow_invokes_the_tested_script_with_the_ci_summary_flag():
    _path, doc = _workflow()
    runs = []
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if step.get("run"):
                runs.append(step)
    commands = "\n".join(step["run"] for step in runs)
    assert "tools/gates/run_release_gates.py" in commands
    assert "--ci" in commands
    assert "GITHUB_STEP_SUMMARY" in commands


def test_workflow_has_no_continue_on_error_on_the_gate_step():
    """A gate step that is allowed to fail makes the job green for nothing."""
    _path, doc = _workflow()
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if "run_release_gates" in step.get("run", ""):
                assert step.get("continue-on-error") in (None, False)
                assert "|| true" not in step["run"]
                assert "||true" not in step["run"]


def test_workflow_does_not_swallow_the_exit_code_with_a_trailing_command():
    _path, doc = _workflow()
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            text = step.get("run", "")
            if "run_release_gates" not in text:
                continue
            assert "| tee" not in text
            assert "set -e" in text or "&&" in text or "\n" not in text.strip()


def test_workflow_installs_only_what_it_needs_and_says_so():
    """The gate that can run in CI must not depend on an installed KiCad."""
    _path, doc = _workflow()
    text = json.dumps(doc)
    assert "kicad" not in text.lower() or "not run" in text.lower()


def test_workflow_is_valid_yaml_and_has_a_job():
    path, doc = _workflow()
    assert isinstance(doc, dict)
    assert doc.get("jobs")
    assert path.name.endswith((".yml", ".yaml"))


def _gate_step_command(doc):
    for job in doc["jobs"].values():
        for step in job.get("steps", []):
            if "run_release_gates.py" in step.get("run", ""):
                return step["run"]
    raise AssertionError("no step runs the gate script")


def _execute_workflow_command(repo, summary, command):
    """Run the workflow's own shell text, with the repo swapped for a scratch one."""
    script = command.replace(
        "python3 tools/gates/run_release_gates.py",
        "%s %s --repo-root %s" % (sys.executable, SCRIPT, repo))
    script = script.replace('"$GITHUB_STEP_SUMMARY"', str(summary))
    return subprocess.run(["bash", "-c", script], cwd=str(REPO_ROOT),
                          capture_output=True, text=True, timeout=300,
                          env={**os.environ, "PYTHONPATH": str(REPO_ROOT)})


def test_the_workflow_command_actually_fails_on_a_failing_gate(tmp_path):
    """The real test of "does a failing gate fail the workflow": run the YAML.

    The command is lifted verbatim from the workflow file and executed with the
    repo root pointed at a tree whose two exports disagree. GitHub is not
    simulated — but the shell text that decides the job's exit status is the
    exact text committed in the workflow.
    """
    _path, doc = _workflow()
    command = _gate_step_command(doc)

    split = {name: list(nodes) for name, nodes in NETS.items()}
    split["VIN_SENSE"] = [("C1", "1")]
    split["VIN"] = [("R1", "1")]
    repo = _fake_repo(tmp_path, xml_nets=split)
    write(repo / "hardware" / "powerboard-reva" / "pin-net-map.csv",
          "ref,pin,pin_name,net,sheet\n"
          "R1,1,,VIN,s\nR1,2,,GND,s\nC1,1,,VIN,s\nC1,2,,GND,s\n")
    summary = tmp_path / "summary.md"

    proc = _execute_workflow_command(repo, summary, command)
    assert proc.returncode != 0, (
        "the workflow command went green on a failing gate.\n"
        "stdout:\n%s\nstderr:\n%s" % (proc.stdout, proc.stderr))
    assert "FAIL" in summary.read_text()


def test_the_workflow_command_is_green_when_the_runnable_gates_pass(tmp_path):
    _path, doc = _workflow()
    command = _gate_step_command(doc)
    repo = _fake_repo(tmp_path)
    summary = tmp_path / "summary.md"
    proc = _execute_workflow_command(repo, summary, command)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "NOT RUN" in summary.read_text()
