"""Tests for the aggregate runner: one nonzero status if any gate fails."""

import json
import subprocess
import sys

import pytest

from gate_support import (
    BOARD_NO_PADS,
    BOARD_MIN,
    drc_report,
    make_fake_kicad,
    netlist_xml,
    run_gate,
    write,
)
from gate_support import REPO_ROOT

RUNNER = REPO_ROOT / "tools" / "gates" / "run_all_gates.py"

PASSING_NETS = {
    "VIN": [("R1", "1")],
    "GND": [("R1", "2")],
}


def _run_runner(args, cwd=None):
    command = [sys.executable, str(RUNNER), *[str(a) for a in args]]
    proc = subprocess.run(command, cwd=str(cwd or REPO_ROOT), capture_output=True, text=True)
    payload = None
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            payload = None
    return proc, payload


def test_runner_with_no_gates_selected_is_not_run():
    proc, payload = _run_runner([])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_runner_rejects_unknown_gate():
    proc, payload = _run_runner(["--gate", "bom"])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_runner_is_executable_invocation_from_elsewhere(tmp_path):
    """The runner must work when invoked by path from another cwd."""
    proc, payload = _run_runner(["--gate", "netlist_parity"], cwd=tmp_path)
    assert proc.returncode == 2  # no inputs given -> NOT RUN, not a crash


def test_runner_single_nonzero_if_any_gate_fails(tmp_path):
    cli = make_fake_kicad(tmp_path, {"drc": {"exit": 1, "content": drc_report()}})
    board = write(tmp_path / "board.kicad_pcb", BOARD_MIN)
    netlist = write(tmp_path / "board.xml", netlist_xml(PASSING_NETS))
    expected = write(
        tmp_path / "expected.json",
        json.dumps({"nets": {"VIN": [["R1", "1"]], "GND": [["R1", "2"]]}}),
    )
    out = tmp_path / "out"
    out.mkdir()

    proc, payload = _run_runner([
        "--gate", "native_reports",
        "--gate", "netlist_parity",
        "--native-kind", "drc",
        "--native-input", board,
        "--native-outdir", out,
        "--kicad-cli", cli,
        "--netlist", netlist,
        "--expected", expected,
        "--skip", "release_manifest",
    ])
    assert proc.returncode == 1, proc.stderr
    assert payload["verdict"] == "FAIL"
    assert payload["results"]["native_reports"]["verdict"] == "FAIL"
    assert payload["results"]["netlist_parity"]["verdict"] == "PASS"
    assert payload["failed"] == ["native_reports"]


def test_runner_passes_when_every_selected_gate_passes(tmp_path):
    cli = make_fake_kicad(
        tmp_path, {"drc": {"exit": 0, "content": drc_report(source="board.kicad_pcb")}}
    )
    board = write(tmp_path / "board.kicad_pcb", BOARD_MIN)
    netlist = write(tmp_path / "board.xml", netlist_xml(PASSING_NETS))
    expected = write(
        tmp_path / "expected.json",
        json.dumps({"nets": {"VIN": [["R1", "1"]], "GND": [["R1", "2"]]}}),
    )
    out = tmp_path / "out"
    out.mkdir()

    proc, payload = _run_runner([
        "--gate", "native_reports",
        "--gate", "netlist_parity",
        "--native-kind", "drc",
        "--native-input", board,
        "--native-outdir", out,
        "--kicad-cli", cli,
        "--netlist", netlist,
        "--expected", expected,
    ])
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["failed"] == []


def test_runner_treats_not_run_as_failure(tmp_path):
    """A gate that cannot run must not be silently green."""
    board = write(tmp_path / "board.kicad_pcb", BOARD_MIN)
    out = tmp_path / "out"
    out.mkdir()
    proc, payload = _run_runner([
        "--gate", "native_reports",
        "--native-kind", "drc",
        "--native-input", board,
        "--native-outdir", out,
        "--kicad-cli", tmp_path / "absent-tool",
        "--netlist", tmp_path / "absent.xml",
        "--expected", tmp_path / "absent.json",
    ])
    assert proc.returncode != 0
    assert payload["verdict"] == "FAIL"
    assert "native_reports" in payload["failed"]
    assert payload["results"]["native_reports"]["verdict"] == "NOT RUN"


def test_runner_lists_the_three_gates():
    proc, payload = _run_runner(["--list"])
    assert proc.returncode == 0
    assert payload["gates"] == ["native_reports", "netlist_parity", "release_manifest"]


def test_runner_skip_removes_a_gate_from_the_selection(tmp_path):
    netlist = write(tmp_path / "board.xml", netlist_xml(PASSING_NETS))
    expected = write(
        tmp_path / "expected.json",
        json.dumps({"nets": {"VIN": [["R1", "1"]], "GND": [["R1", "2"]]}}),
    )
    proc, payload = _run_runner([
        "--gate", "native_reports",
        "--gate", "netlist_parity",
        "--skip", "native_reports",
        "--netlist", netlist,
        "--expected", expected,
    ])
    assert proc.returncode == 0, proc.stderr
    assert payload["selected"] == ["netlist_parity"]


def test_runner_writes_json_out(tmp_path):
    netlist = write(tmp_path / "board.xml", netlist_xml(PASSING_NETS))
    expected = write(
        tmp_path / "expected.json",
        json.dumps({"nets": {"VIN": [["R1", "1"]], "GND": [["R1", "2"]]}}),
    )
    out = tmp_path / "aggregate.json"
    proc, payload = _run_runner([
        "--gate", "netlist_parity",
        "--netlist", netlist,
        "--expected", expected,
        "--json-out", out,
    ])
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out.read_text())["verdict"] == "PASS"


# ------------------------------- in-process tests of the runner's own paths

def _runner_module():
    import tools.gates.run_all_gates as runner

    return runner


def _args(module, argv):
    return module._build_argparser().parse_args(argv)


def test_gate_that_prints_nothing_is_not_run(tmp_path, monkeypatch):
    module = _runner_module()
    args = _args(module, ["--gate", "netlist_parity"])
    monkeypatch.setattr(module, "_gate_argv",
                        lambda gate, a: (["-c", "import sys; sys.exit(0)"], ""))
    result = module._run_gate("netlist_parity", args)
    assert result["verdict"] == "NOT RUN"
    assert "no machine-readable result" in result["reason"]


def test_gate_claiming_pass_with_nonzero_exit_is_a_failure(tmp_path, monkeypatch):
    module = _runner_module()
    liar = (
        "import json,sys;"
        "print(json.dumps({'verdict':'PASS','exit_code':0}));"
        "sys.exit(1)"
    )
    args = _args(module, ["--gate", "netlist_parity"])
    monkeypatch.setattr(module, "_gate_argv", lambda gate, a: (["-c", liar], ""))
    result = module._run_gate("netlist_parity", args)
    assert result["verdict"] == "FAIL"
    assert "self-reported PASS" in result["reason"]


def test_gate_that_hangs_times_out_as_not_run(monkeypatch):
    module = _runner_module()
    sleeper = "import json,time; print(json.dumps({'verdict':'PASS'})); time.sleep(30)"
    args = _args(module, ["--gate", "netlist_parity", "--timeout", "0.4"])
    monkeypatch.setattr(module, "_gate_argv", lambda gate, a: (["-c", sleeper], ""))
    result = module._run_gate("netlist_parity", args)
    assert result["verdict"] == "NOT RUN"
    assert "timeout" in result["reason"]


def test_gate_with_unparsable_stdout_is_not_run(monkeypatch):
    module = _runner_module()
    args = _args(module, ["--gate", "netlist_parity"])
    monkeypatch.setattr(module, "_gate_argv",
                        lambda gate, a: (["-c", "print('not json')"], ""))
    result = module._run_gate("netlist_parity", args)
    assert result["verdict"] == "NOT RUN"


def test_gate_argv_rejects_missing_wiring():
    module = _runner_module()
    args = _args(module, ["--gate", "native_reports"])
    argv, problem = module._gate_argv("native_reports", args)
    assert argv is None
    assert "--kicad-cli" in problem

    args = _args(module, ["--gate", "release_manifest"])
    argv, problem = module._gate_argv("release_manifest", args)
    assert argv is None
    assert "--manifest" in problem


def test_runner_help_exits_zero():
    proc, _payload = _run_runner(["--help"])
    assert proc.returncode == 0
    assert "run_all_gates" in proc.stdout


def test_runner_require_net_flags_are_forwarded(tmp_path):
    netlist = write(tmp_path / "board.xml", netlist_xml(PASSING_NETS))
    expected = write(
        tmp_path / "expected.json",
        json.dumps({"nets": {"VIN": [["R1", "1"]], "GND": [["R1", "2"]]}}),
    )
    proc, payload = _run_runner([
        "--gate", "netlist_parity",
        "--netlist", netlist,
        "--expected", expected,
        "--require-net", "GND",
        "--require-net", "VBUS",
    ])
    assert proc.returncode == 1
    assert "net_present:VBUS" in {
        check["name"] for check in payload["results"]["netlist_parity"]["checks"]
        if not check["ok"]
    }


def test_runner_reports_unwired_gate_as_not_run(tmp_path):
    """A selected gate with no inputs is a configuration error, not a verdict."""
    proc, payload = _run_runner(["--gate", "release_manifest"])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"
    assert payload["unwired"] == ["release_manifest"]
    assert "needs --manifest and --artifacts" in payload["reason"]


def test_runner_reports_partial_wiring_as_not_run(tmp_path):
    proc, payload = _run_runner(["--gate", "native_reports", "--native-kind", "drc"])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_runner_unparsable_flag_is_not_run():
    proc, payload = _run_runner(["--nonsense"])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_runner_unknown_skip_is_not_run():
    proc, payload = _run_runner(["--gate", "netlist_parity", "--skip", "bom"])
    assert proc.returncode == 2
    assert "unknown gate" in payload["reason"]
