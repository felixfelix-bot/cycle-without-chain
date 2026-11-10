"""Tests for the fail-closed native KiCad report/export runner.

The gate is exercised through its real CLI surface (subprocess + exit code)
against a fake ``kicad-cli`` that can return any exit code, write nothing,
write a truncated report, or write a report to the wrong path.
"""

import hashlib
import json
import os
import stat

import pytest

from gate_support import (
    BOARD_EMPTY,
    BOARD_MIN,
    BOARD_NO_PADS,
    SCH_MIN,
    SCH_NO_SYMBOLS,
    drc_report,
    erc_report,
    make_fake_kicad,
    run_gate,
    violation,
    write,
)


def _setup(tmp_path, spec, board=BOARD_MIN, name="board.kicad_pcb"):
    cli = make_fake_kicad(tmp_path, spec)
    target = write(tmp_path / name, board)
    return cli, target


def _args(cli, target, outdir, kind="drc", extra=()):
    return [
        "--kind", kind,
        "--input", target,
        "--outdir", outdir,
        "--kicad-cli", cli,
        *extra,
    ]


# ---------------------------------------------------------------- PASS paths

def test_clean_report_is_the_only_pass(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(source="board.kicad_pcb")},
    })
    outdir = tmp_path / "out"
    proc, payload = run_gate("native_reports", _args(cli, target, outdir))

    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["gate"] == "native_reports"
    assert payload["exit_code"] == 0
    assert all(check["ok"] for check in payload["checks"])
    assert payload["evidence"]["violations"] == 0
    assert payload["evidence"]["objects_scanned"] >= 2


def test_stdout_is_a_single_machine_readable_json_object(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(source="board.kicad_pcb")},
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert json.loads(proc.stdout) == payload


def test_erc_clean_pass(tmp_path):
    cli, target = _setup(tmp_path, {
        "erc": {"exit": 0, "content": erc_report()},
    }, board=SCH_MIN, name="board.kicad_sch")
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", kind="erc")
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["evidence"]["sheets"] >= 1


def test_netlist_export_kind_pass(tmp_path):
    from gate_support import netlist_xml

    xml = netlist_xml({"VIN": [("R1", "1")], "GND": [("R1", "2")]})
    cli, target = _setup(tmp_path, {
        "netlist": {"exit": 0, "content": xml},
    }, board=SCH_MIN, name="board.kicad_sch")
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", kind="netlist")
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["evidence"]["objects_scanned"] >= 2


def test_report_path_is_unique_per_run_and_never_the_legacy_fixed_path(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(source="board.kicad_pcb")},
    })
    outdir = tmp_path / "out"
    first, payload_a = run_gate("native_reports", _args(cli, target, outdir))
    second, payload_b = run_gate("native_reports", _args(cli, target, outdir))

    assert first.returncode == 0 and second.returncode == 0
    path_a = payload_a["evidence"]["report_path"]
    path_b = payload_b["evidence"]["report_path"]
    assert path_a != path_b
    assert os.path.exists(path_a) and os.path.exists(path_b)
    assert path_a != str(outdir / "drc.json")


# ------------------------------------------------- negative controls (FAIL)

def test_negative_control_nonzero_exit_with_empty_violations_fails(tmp_path):
    """The balloon-fresh defect: subprocess failed, arrays stayed empty."""
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 1, "content": drc_report(violations=[]), },
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))

    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    assert payload["evidence"]["violations"] == 0
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "subprocess_exit" in failed


def test_negative_control_nonzero_exit_without_report_fails(tmp_path):
    cli, target = _setup(tmp_path, {"drc": {"exit": 3, "write": False}})
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert {"subprocess_exit", "report_present"} <= failed
    assert payload["evidence"]["report_path"] is not None


def test_negative_control_missing_report_with_zero_exit_fails(tmp_path):
    cli, target = _setup(tmp_path, {"drc": {"exit": 0, "write": False}})
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not c_ok(payload, "report_present")}
    assert "report_present" in {c["name"] for c in payload["checks"] if not c["ok"]}


def c_ok(payload, name):
    for check in payload["checks"]:
        if check["name"] == name:
            return check["ok"]
    return False


def test_negative_control_truncated_report_fails(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": '{"violations": [], "unconnected_ite'},
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "report_parseable" in failed
    assert "report_structure" in failed


def test_negative_control_truncated_mid_document_report_fails(tmp_path):
    """A report cut exactly at a byte boundary can still be valid JSON."""
    text = drc_report(violations=[violation()])
    cli, target = _setup(tmp_path, {"drc": {"exit": 0, "content": text[: len(text) // 3]}})
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"


def test_negative_control_report_missing_required_keys_fails(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": json.dumps({"date": "2026-11-10", "violations": []})},
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "report_structure" in failed


def test_negative_control_json_scalar_report_fails(tmp_path):
    cli, target = _setup(tmp_path, {"drc": {"exit": 0, "content": "[]"}})
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"


def test_negative_control_zero_objects_scanned_fails(tmp_path):
    """Zero pads + zero violations is not a pass: nothing was graded."""
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(source="board.kicad_pcb")},
    }, board=BOARD_NO_PADS)
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "objects_scanned" in failed
    assert payload["evidence"]["objects_scanned"] == 0


def test_negative_control_empty_board_file_fails_objects(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(source="board.kicad_pcb")},
    }, board=BOARD_EMPTY)
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    assert payload["evidence"]["objects_scanned"] == 0


def test_negative_control_planted_violations_fail(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {
            "exit": 3,
            "content": drc_report(violations=[violation("short"), violation("clearance")],
                                  source="board.kicad_pcb"),
        },
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    assert payload["evidence"]["violations"] == 2
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "no_violations" in failed


def test_negative_control_planted_unconnected_items_fail(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(unconnected=[violation()], source="board.kicad_pcb")},
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "no_unconnected" in failed


def test_negative_control_stale_report_at_legacy_path_is_not_reused(tmp_path):
    """A pre-existing clean report at the fixed balloon-fresh path must be ignored."""
    outdir = tmp_path / "out"
    outdir.mkdir()
    stale = write(outdir / "drc.json", drc_report(source="board.kicad_pcb"))
    before = hashlib.sha256(stale.read_bytes()).hexdigest()

    cli, target = _setup(tmp_path, {"drc": {"exit": 5, "write": False}})
    proc, payload = run_gate("native_reports", _args(cli, target, outdir))

    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    assert payload["evidence"]["report_path"] != str(stale)
    assert hashlib.sha256(stale.read_bytes()).hexdigest() == before


def test_negative_control_second_run_does_not_reuse_first_run_report(tmp_path):
    outdir = tmp_path / "out"
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(source="board.kicad_pcb")},
    })
    first, payload_1 = run_gate("native_reports", _args(cli, target, outdir))
    assert first.returncode == 0

    broken_dir = tmp_path / "second"
    broken_dir.mkdir(exist_ok=True)
    broken = make_fake_kicad(broken_dir, {"drc": {"exit": 1, "content": ""}})
    second, payload_2 = run_gate("native_reports", _args(broken, target, outdir))
    assert second.returncode == 1
    assert payload_2["verdict"] == "FAIL"
    assert payload_2["evidence"]["report_path"] != payload_1["evidence"]["report_path"]


def test_negative_control_report_written_to_wrong_path_fails(tmp_path):
    elsewhere = tmp_path / "elsewhere.json"
    cli, target = _setup(tmp_path, {
        "drc": {
            "exit": 0,
            "content": drc_report(source="board.kicad_pcb"),
            "write": False,
            "write_to": str(elsewhere),
        },
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    assert elsewhere.exists()
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "report_present" in failed


def test_negative_control_report_for_a_different_input_fails(tmp_path):
    cli, target = _setup(tmp_path, {
        "drc": {"exit": 0, "content": drc_report(source="some_other_board.kicad_pcb")},
    })
    proc, payload = run_gate("native_reports", _args(cli, target, tmp_path / "out"))
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "report_source_matches_input" in failed


def test_negative_control_tool_timeout_fails(tmp_path):
    cli, target = _setup(tmp_path, {"drc": {"exit": 0, "sleep": 5, "write": False}})
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", extra=["--timeout", "0.5"])
    )
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "subprocess_completed" in failed


def test_negative_control_erc_without_sheets_fails(tmp_path):
    payload_json = json.loads(erc_report())
    payload_json["sheets"] = []
    cli, target = _setup(tmp_path, {"erc": {"exit": 0, "content": json.dumps(payload_json)}},
                         board=SCH_MIN, name="board.kicad_sch")
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", kind="erc")
    )
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "report_covers_sheets" in failed


def test_negative_control_schematic_with_no_symbols_fails(tmp_path):
    cli, target = _setup(tmp_path, {"erc": {"exit": 0, "content": erc_report()}},
                         board=SCH_NO_SYMBOLS, name="board.kicad_sch")
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", kind="erc")
    )
    assert proc.returncode == 1
    assert payload["evidence"]["objects_scanned"] == 0


def test_negative_control_netlist_export_with_zero_nodes_fails(tmp_path):
    from gate_support import netlist_xml
    cli, target = _setup(tmp_path, {"netlist": {"exit": 0, "content": netlist_xml({})}},
                         board=SCH_MIN, name="board.kicad_sch")
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", kind="netlist")
    )
    assert proc.returncode == 1
    assert payload["evidence"]["objects_scanned"] == 0


# ------------------------------------------------------- NOT RUN (exit 2)

def test_no_arguments_is_not_run():
    proc, payload = run_gate("native_reports", [])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_missing_required_flag_is_not_run(tmp_path):
    cli, target = _setup(tmp_path, {})
    proc, payload = run_gate("native_reports", ["--kind", "drc", "--input", target,
                                                "--kicad-cli", cli])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_unknown_kind_is_not_run(tmp_path):
    cli, target = _setup(tmp_path, {})
    proc, payload = run_gate(
        "native_reports", ["--kind", "bom", "--input", target,
                           "--outdir", tmp_path / "o", "--kicad-cli", cli]
    )
    assert proc.returncode == 2


def test_missing_input_is_not_run(tmp_path):
    cli = make_fake_kicad(tmp_path, {})
    proc, payload = run_gate(
        "native_reports",
        ["--kind", "drc", "--input", tmp_path / "nope.kicad_pcb",
         "--outdir", tmp_path / "out", "--kicad-cli", cli],
    )
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"
    assert "nope.kicad_pcb" in json.dumps(payload)


def test_input_directory_instead_of_file_is_not_run(tmp_path):
    cli = make_fake_kicad(tmp_path, {})
    directory = tmp_path / "dir.kicad_pcb"
    directory.mkdir()
    proc, payload = run_gate(
        "native_reports",
        ["--kind", "drc", "--input", directory, "--outdir", tmp_path / "out",
         "--kicad-cli", cli],
    )
    assert proc.returncode == 2


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read anything")
def test_unreadable_input_is_not_run(tmp_path):
    cli = make_fake_kicad(tmp_path, {})
    target = write(tmp_path / "board.kicad_pcb", BOARD_MIN, mode=0o000)
    target.chmod(0)
    try:
        proc, payload = run_gate(
            "native_reports",
            ["--kind", "drc", "--input", target, "--outdir", tmp_path / "out",
             "--kicad-cli", cli],
        )
    finally:
        target.chmod(stat.S_IRUSR | stat.S_IWUSR)
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_missing_kicad_cli_is_not_run(tmp_path):
    target = write(tmp_path / "board.kicad_pcb", BOARD_MIN)
    proc, payload = run_gate(
        "native_reports",
        ["--kind", "drc", "--input", target, "--outdir", tmp_path / "out",
         "--kicad-cli", tmp_path / "no-such-tool"],
    )
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_min_objects_zero_is_rejected(tmp_path):
    cli, target = _setup(tmp_path, {})
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", extra=["--min-objects", "0"])
    )
    assert proc.returncode == 2


def test_extra_positional_argument_is_rejected(tmp_path):
    cli, target = _setup(tmp_path, {})
    proc, _ = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", extra=["surplus"])
    )
    assert proc.returncode == 2


def test_non_positive_timeout_is_not_run(tmp_path):
    cli, target = _setup(tmp_path, {})
    proc, payload = run_gate(
        "native_reports", _args(cli, target, tmp_path / "out", extra=["--timeout", "0"])
    )
    assert proc.returncode == 2
    assert "timeout" in payload["reason"]


def test_outdir_that_is_a_file_is_not_run(tmp_path):
    cli, target = _setup(tmp_path, {})
    blocker = write(tmp_path / "not-a-dir", "x")
    proc, payload = run_gate("native_reports", _args(cli, target, blocker))
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_non_executable_kicad_cli_is_not_run(tmp_path):
    target = write(tmp_path / "board.kicad_pcb", BOARD_MIN)
    tool = write(tmp_path / "kicad-cli", "#!/bin/sh\nexit 0\n", mode=0o644)
    proc, payload = run_gate(
        "native_reports",
        ["--kind", "drc", "--input", target, "--outdir", tmp_path / "out",
         "--kicad-cli", tool],
    )
    assert proc.returncode == 2
    assert "not executable" in payload["reason"]
