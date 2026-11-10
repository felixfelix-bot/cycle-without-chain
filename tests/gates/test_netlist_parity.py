"""Tests for the schematic-to-netlist parity gate (exact set semantics)."""

import json
import stat

import pytest

from gate_support import netlist_xml, run_gate, write

PASSING_NETS = {
    "VIN": [("R1", "1"), ("C1", "1")],
    "GND": [("R1", "2"), ("C1", "2"), ("R2", "2")],
    "GATE": [("R2", "1")],
}

PASSING_EXPECTED = {
    "nets": {
        "VIN": [["R1", "1"], ["C1", "1"]],
        "GND": [["R1", "2"], ["C1", "2"], ["R2", "2"]],
        "GATE": [["R2", "1"]],
    }
}


def _write_inputs(tmp_path, nets=None, expected=None, name="board.xml"):
    netlist = write(tmp_path / name, netlist_xml(PASSING_NETS if nets is None else nets))
    mapping = write(tmp_path / "expected.json",
                    json.dumps(PASSING_EXPECTED if expected is None else expected, indent=1))
    return netlist, mapping


# ---------------------------------------------------------------- PASS paths

def test_exact_match_passes(tmp_path):
    netlist, mapping = _write_inputs(tmp_path)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["evidence"]["endpoints"] == 6
    assert payload["evidence"]["nets"] == 3
    assert payload["diffs"]["missing"] == [] and payload["diffs"]["extra"] == []


def test_machine_readable_stdout_only(tmp_path):
    netlist, mapping = _write_inputs(tmp_path)
    proc, _ = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert json.loads(proc.stdout)["gate"] == "netlist_parity"


def test_node_order_inside_a_net_does_not_matter(tmp_path):
    reordered = {
        "nets": {
            "VIN": [["C1", "1"], ["R1", "1"]],
            "GND": [["R2", "2"], ["C1", "2"], ["R1", "2"]],
            "GATE": [["R2", "1"]],
        }
    }
    netlist, mapping = _write_inputs(tmp_path, expected=reordered)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"


def test_expected_map_may_be_a_plain_sorted_list(tmp_path):
    rows = sorted((ref, pin, net) for net, nodes in PASSING_NETS.items() for ref, pin in nodes)
    netlist = write(tmp_path / "board.xml", netlist_xml(PASSING_NETS))
    mapping = write(tmp_path / "expected.json", json.dumps({"endpoints": rows}))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"


# ------------------------------------------------- negative controls (FAIL)

def test_negative_control_mutated_endpoint_net_fails(tmp_path):
    """The classic defect: a swap that keeps the endpoint count identical."""
    # netlist says R2.1 on GATE, R2.2 on GND; the expectation is swapped.
    mutated = json.loads(json.dumps(PASSING_EXPECTED))
    mutated["nets"]["GATE"] = [["R2", "2"]]
    mutated["nets"]["GND"] = [["R1", "2"], ["C1", "2"], ["R2", "1"]]
    netlist, mapping = _write_inputs(tmp_path, expected=mutated)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])

    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    missing = payload["diffs"]["missing"]
    extra = payload["diffs"]["extra"]
    assert {"ref": "R2", "pin": "1", "net": "GND"} in missing
    assert {"ref": "R2", "pin": "2", "net": "GATE"} in missing
    assert {"ref": "R2", "pin": "1", "net": "GATE"} in extra
    assert {"ref": "R2", "pin": "2", "net": "GND"} in extra
    assert payload["evidence"]["endpoints"] == payload["evidence"]["expected_endpoints"] == 6
    assert proc.stderr.strip() != ""


def test_negative_control_swapped_gate_source_fails(tmp_path):
    mutated = json.loads(json.dumps(PASSING_EXPECTED))
    mutated["nets"]["GATE"] = [["R2", "1"]]
    nets = dict(PASSING_NETS)
    nets["GATE"] = [("R1", "1")]
    netlist, mapping = _write_inputs(tmp_path, nets=nets, expected=mutated)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert {"ref": "R1", "pin": "1", "net": "GATE"} in payload["diffs"]["extra"]


def test_negative_control_missing_endpoint_fails(tmp_path):
    nets = json.loads(json.dumps(PASSING_NETS))
    nets["GND"] = [["R1", "2"], ["C1", "2"]]
    netlist, mapping = _write_inputs(tmp_path, nets=nets)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["diffs"]["missing"] == [{"ref": "R2", "pin": "2", "net": "GND"}]
    assert "R2" in proc.stderr


def test_negative_control_extra_endpoint_fails(tmp_path):
    nets = json.loads(json.dumps(PASSING_NETS))
    nets["GATE"].append(["C1", "1"])
    netlist, mapping = _write_inputs(tmp_path, nets=nets)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["diffs"]["extra"] == [{"ref": "C1", "pin": "1", "net": "GATE"}]


def test_negative_control_extra_net_fails_even_when_endpoints_match(tmp_path):
    mutated = json.loads(json.dumps(PASSING_EXPECTED))
    mutated["nets"]["UNUSED"] = []
    netlist, mapping = _write_inputs(tmp_path, expected=mutated)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert "UNUSED" in payload["diffs"]["nets_missing"]


def test_negative_control_renamed_net_fails(tmp_path):
    nets = json.loads(json.dumps(PASSING_NETS))
    nets["GATE_SW"] = nets.pop("GATE")
    netlist, mapping = _write_inputs(tmp_path, nets=nets)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["diffs"]["nets_missing"] == ["GATE"]
    assert payload["diffs"]["nets_extra"] == ["GATE_SW"]


def test_negative_control_duplicate_row_inside_one_net_fails(tmp_path):
    """The same (ref, pin) listed twice in one net is a malformed export."""
    duplicate = netlist_xml(PASSING_NETS).replace(
        '<node ref="C1" pin="1"/>',
        '<node ref="C1" pin="1"/><node ref="C1" pin="1"/>',
        1,
    )
    netlist = write(tmp_path / "board.xml", duplicate)
    mapping = write(tmp_path / "expected.json", json.dumps(PASSING_EXPECTED))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    assert payload["evidence"]["duplicate_endpoints"] == 1
    assert "DUPLICATE" in proc.stderr


def test_negative_control_pin_on_two_nets_fails(tmp_path):
    nets = json.loads(json.dumps(PASSING_NETS))
    nets["GATE"].append(["R1", "1"])  # R1.1 already on VIN
    netlist, mapping = _write_inputs(tmp_path, nets=nets)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["evidence"]["duplicate_endpoints"] == 1
    assert "R1" in proc.stderr and "pin 1" in proc.stderr


def test_negative_control_duplicate_expected_rows_fail(tmp_path):
    duplicated = json.loads(json.dumps(PASSING_EXPECTED))
    duplicated["nets"]["GND"].append(["R1", "2"])
    netlist, mapping = _write_inputs(tmp_path, expected=duplicated)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"
    assert "duplicate" in json.dumps(payload).lower()


def test_negative_control_empty_netlist_fails(tmp_path):
    netlist = write(tmp_path / "board.xml", netlist_xml({}))
    mapping = write(tmp_path / "expected.json", json.dumps(PASSING_EXPECTED))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["evidence"]["endpoints"] == 0


def test_negative_control_truncated_netlist_fails(tmp_path):
    text = netlist_xml(PASSING_NETS)
    netlist = write(tmp_path / "board.xml", text[: len(text) // 2])
    mapping = write(tmp_path / "expected.json", json.dumps(PASSING_EXPECTED))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    assert any("pars" in check["name"] for check in payload["checks"] if not check["ok"])


def test_negative_control_netlist_without_nets_element_fails(tmp_path):
    netlist = write(tmp_path / "board.xml", '(export (version "E") (design (source "x")))')
    mapping = write(tmp_path / "expected.json", json.dumps(PASSING_EXPECTED))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "netlist_structure" in failed


# --------------------------------------------- unconnected nets and NC pins

def test_unconnected_nets_are_ignored_by_default(tmp_path):
    nets = json.loads(json.dumps(PASSING_NETS))
    netlist_text = netlist_xml(nets).replace(
        "  </nets>",
        '    <net code="99" name="unconnected-(U1-Pad3)">\n'
        '      <node ref="U1" pin="3"/>\n    </net>\n  </nets>',
    )
    netlist = write(tmp_path / "board.xml", netlist_text)
    mapping = write(tmp_path / "expected.json", json.dumps(PASSING_EXPECTED))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 0, proc.stderr
    assert payload["evidence"]["unconnected_nets_ignored"] == 1


def test_include_unconnected_flag_makes_them_fail(tmp_path):
    nets = json.loads(json.dumps(PASSING_NETS))
    netlist_text = netlist_xml(nets).replace(
        "  </nets>",
        '    <net code="99" name="unconnected-(U1-Pad3)">\n'
        '      <node ref="U1" pin="3"/>\n    </net>\n  </nets>',
    )
    netlist = write(tmp_path / "board.xml", netlist_text)
    mapping = write(tmp_path / "expected.json", json.dumps(PASSING_EXPECTED))
    proc, payload = run_gate(
        "netlist_parity",
        ["--netlist", netlist, "--expected", mapping, "--include-unconnected"],
    )
    assert proc.returncode == 1


def test_negative_control_nc_pin_that_is_connected_fails(tmp_path):
    """The schematic says U2.1 is unused; the netlist ties it to GATE."""
    expected = json.loads(json.dumps(PASSING_EXPECTED))
    expected["nc"] = [["U2", "1"]]
    nets = json.loads(json.dumps(PASSING_NETS))
    nets["GATE"].append(["U2", "1"])
    netlist, mapping = _write_inputs(tmp_path, nets=nets, expected=expected)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1
    assert payload["evidence"]["nc_violations"] == [["U2", "1"]]
    assert "NC VIOLATION" in proc.stderr
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "nc_respected" in failed


def test_nc_pin_that_is_really_unconnected_passes(tmp_path):
    expected = json.loads(json.dumps(PASSING_EXPECTED))
    expected["nc"] = [["U1", "3"]]
    netlist_text = netlist_xml(PASSING_NETS).replace(
        "  </nets>",
        '    <net code="99" name="unconnected-(U1-Pad3)">\n'
        '      <node ref="U1" pin="3"/>\n    </net>\n  </nets>',
    )
    netlist = write(tmp_path / "board.xml", netlist_text)
    mapping = write(tmp_path / "expected.json", json.dumps(expected))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 0, proc.stderr
    assert payload["evidence"]["nc_violations"] == []


def test_negative_control_pin_declared_both_connected_and_nc_is_not_run(tmp_path):
    expected = json.loads(json.dumps(PASSING_EXPECTED))
    expected["nc"] = [["R1", "1"]]
    expected["nets"]["VIN"] = [["R1", "1"], ["C1", "1"]]
    netlist = write(tmp_path / "board.xml", netlist_xml(PASSING_NETS))
    mapping = write(tmp_path / "expected.json", json.dumps(expected))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_require_net_flag_fails_on_absent_net(tmp_path):
    netlist, mapping = _write_inputs(tmp_path)
    proc, payload = run_gate(
        "netlist_parity",
        ["--netlist", netlist, "--expected", mapping, "--require-net", "VBUS"],
    )
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "net_present:VBUS" in failed


def test_allow_empty_flag_permits_a_zero_endpoint_comparison(tmp_path):
    netlist = write(tmp_path / "board.xml", netlist_xml({"EMPTY": []}))
    mapping = write(tmp_path / "expected.json", json.dumps({"nets": {"EMPTY": []}}))
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 1  # non_empty check fires by default

    proc2, payload2 = run_gate(
        "netlist_parity",
        ["--netlist", netlist, "--expected", mapping, "--allow-empty"],
    )
    assert proc2.returncode == 0, proc2.stderr


# ------------------------------------------------------- NOT RUN (exit 2)

def test_no_arguments_is_not_run():
    proc, payload = run_gate("netlist_parity", [])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_wrong_argument_count_is_not_run(tmp_path):
    netlist, _ = _write_inputs(tmp_path)
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist])
    assert proc.returncode == 2


def test_missing_netlist_is_not_run(tmp_path):
    _, mapping = _write_inputs(tmp_path)
    proc, payload = run_gate(
        "netlist_parity", ["--netlist", tmp_path / "absent.xml", "--expected", mapping]
    )
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_missing_expected_map_is_not_run(tmp_path):
    netlist, _ = _write_inputs(tmp_path)
    proc, payload = run_gate(
        "netlist_parity", ["--netlist", netlist, "--expected", tmp_path / "absent.json"]
    )
    assert proc.returncode == 2


@pytest.mark.skipif(stat.S_ISUID and False, reason="placeholder")
def test_unparsable_expected_map_is_not_run(tmp_path):
    netlist, _ = _write_inputs(tmp_path)
    mapping = write(tmp_path / "bad.json", "{not json")
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_expected_map_without_nets_key_is_not_run(tmp_path):
    netlist, _ = _write_inputs(tmp_path)
    mapping = write(tmp_path / "empty.json", "{}")
    proc, payload = run_gate("netlist_parity", ["--netlist", netlist, "--expected", mapping])
    assert proc.returncode == 2


def test_unreadable_netlist_is_not_run(tmp_path):
    netlist, mapping = _write_inputs(tmp_path)
    netlist.chmod(0)
    try:
        proc, payload = run_gate(
            "netlist_parity", ["--netlist", netlist, "--expected", mapping]
        )
    finally:
        netlist.chmod(0o644)
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_extra_positional_argument_is_rejected(tmp_path):
    netlist, mapping = _write_inputs(tmp_path)
    proc, _ = run_gate(
        "netlist_parity", ["--netlist", netlist, "--expected", mapping, "surplus"]
    )
    assert proc.returncode == 2
