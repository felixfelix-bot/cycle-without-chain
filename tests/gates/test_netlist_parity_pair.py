"""RAIL-12: cross-artifact parity — XML netlist and S-expression `.net`.

The topology tests read ``exports/ctrl-supply.xml``; ``verify_exports.py`` reads
``exports/powerboard-reva.net``. They are two exports of the same design, and
until this pair was wired nothing compared them to each other or to one
expected map, so an intra-rail split injected into one artifact alone stayed
green. Every test below is a negative control for that class of defect.
"""

import json
import shutil
import xml.etree.ElementTree as ET

import pytest

from gate_support import REPO_ROOT, netlist_sexpr, netlist_xml, run_gate, write

BOARD = REPO_ROOT / "hardware" / "powerboard-reva"
XML_REAL = BOARD / "exports" / "ctrl-supply.xml"
NET_REAL = BOARD / "exports" / "powerboard-reva.net"
CSV_REAL = BOARD / "pin-net-map.csv"

NETS = {
    "VIN": [("R1", "1"), ("C1", "1")],
    "GND": [("R1", "2"), ("C1", "2"), ("R2", "2")],
    "GATE": [("R2", "1")],
}

EXPECTED = {
    "nets": {
        "VIN": [["R1", "1"], ["C1", "1"]],
        "GND": [["R1", "2"], ["C1", "2"], ["R2", "2"]],
        "GATE": [["R2", "1"]],
    }
}


def _inputs(tmp_path, xml_nets=None, net_nets=None, expected=None):
    xml = write(tmp_path / "board.xml",
                netlist_xml(NETS if xml_nets is None else xml_nets))
    sexpr = write(tmp_path / "board.net",
                  netlist_sexpr(NETS if net_nets is None else net_nets))
    mapping = write(tmp_path / "expected.json",
                    json.dumps(EXPECTED if expected is None else expected, indent=1))
    return xml, sexpr, mapping


def _run(xml, sexpr, mapping, *extra):
    return run_gate("netlist_parity",
                    ["--netlist", xml, "--netlist-sexpr", sexpr,
                     "--expected", mapping, *extra])


# ------------------------------------------------------------------ PASS paths

def test_both_artifacts_matching_one_expected_map_pass(tmp_path):
    xml, sexpr, mapping = _inputs(tmp_path)
    proc, payload = _run(xml, sexpr, mapping)
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["evidence"]["artifacts_checked"] == ["xml", "sexpr"]
    assert payload["evidence"]["endpoints_sexpr"] == 6
    assert payload["evidence"]["sexpr_sha256"]


def test_single_artifact_mode_is_unchanged(tmp_path):
    """Omitting --netlist-sexpr keeps the old, single-artifact contract."""
    xml, _sexpr, mapping = _inputs(tmp_path)
    proc, payload = run_gate("netlist_parity", ["--netlist", xml, "--expected", mapping])
    assert proc.returncode == 0, proc.stderr
    assert payload["evidence"]["artifacts_checked"] == ["xml"]


# ------------------------------------------------- negative controls (FAIL)

def test_negative_control_intra_rail_split_injected_into_xml_only_fails(tmp_path):
    """The RAIL-12 defect: a split in the XML alone must not stay green.

    VIN's two endpoints move apart: C1.1 is rewired onto a new net
    ``VIN_SENSE`` so the rail is split in the artifact the topology tests read,
    while the S-expression export still shows one net.
    """
    split = {name: list(nodes) for name, nodes in NETS.items()}
    split["VIN_SENSE"] = [("C1", "1")]
    split["VIN"] = [("R1", "1")]
    xml, sexpr, mapping = _inputs(tmp_path, xml_nets=split)
    proc, payload = _run(xml, sexpr, mapping)
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "endpoints_match" in failed and "nets_match" in failed
    assert {"ref": "C1", "pin": "1", "net": "VIN"} in payload["diffs"]["missing"]
    assert "VIN_SENSE" in payload["diffs"]["nets_extra"]


def test_negative_control_injection_into_sexpr_only_fails(tmp_path):
    """The mirror case: mutation in the `.net` alone must also fail."""
    split = {name: list(nodes) for name, nodes in NETS.items()}
    split["GND_SENSE"] = [("R2", "2")]
    split["GND"] = [("R1", "2"), ("C1", "2")]
    xml, sexpr, mapping = _inputs(tmp_path, net_nets=split)
    proc, payload = _run(xml, sexpr, mapping)
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    assert any(name.startswith("sexpr_") for name in
               {check["name"] for check in payload["checks"] if not check["ok"]})


def test_negative_control_artifacts_disagree_with_each_other(tmp_path):
    """XML matches the expectation, `.net` does not: still a failure, and the
    disagreement is reported as its own check rather than as a diff."""
    nets = {name: list(nodes) for name, nodes in NETS.items()}
    nets["GATE"] = [("R1", "1")]
    xml, sexpr, mapping = _inputs(tmp_path, net_nets=nets)
    proc, payload = _run(xml, sexpr, mapping)
    assert proc.returncode == 1
    failed = {check["name"] for check in payload["checks"] if not check["ok"]}
    assert "artifacts_agree" in failed
    assert payload["evidence"]["cross_artifact_diffs"]["count"] > 0


def test_negative_control_split_in_both_artifacts_against_stale_map_fails(tmp_path):
    """Both exports mutated identically still fails the expected map."""
    split = {name: list(nodes) for name, nodes in NETS.items()}
    split["VIN_SENSE"] = [("C1", "1")]
    split["VIN"] = [("R1", "1")]
    xml, sexpr, mapping = _inputs(tmp_path, xml_nets=split, net_nets=split)
    proc, payload = _run(xml, sexpr, mapping)
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"


def test_negative_control_sexpr_pin_on_two_nets_fails(tmp_path):
    nets = {name: list(nodes) for name, nodes in NETS.items()}
    nets["GATE"].append(("R1", "1"))
    xml, sexpr, mapping = _inputs(tmp_path, net_nets=nets)
    proc, payload = _run(xml, sexpr, mapping)
    assert proc.returncode == 1
    assert "sexpr_duplicate_free" in {c["name"] for c in payload["checks"] if not c["ok"]}
    assert "SHORT" in proc.stderr


# --------------------------------------------------------- NOT RUN / malformed

def test_missing_sexpr_artifact_is_not_run(tmp_path):
    xml, _sexpr, mapping = _inputs(tmp_path)
    proc, payload = run_gate("netlist_parity",
                             ["--netlist", xml,
                              "--netlist-sexpr", tmp_path / "absent.net",
                              "--expected", mapping])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_malformed_sexpr_artifact_fails(tmp_path):
    xml, _sexpr, mapping = _inputs(tmp_path)
    broken = write(tmp_path / "broken.net", '(export (version "E") (nets (net (code "1")')
    proc, payload = _run(xml, broken, mapping)
    assert proc.returncode == 1
    assert "sexpr_parseable" in {c["name"] for c in payload["checks"] if not c["ok"]}


def test_sexpr_without_nets_element_fails(tmp_path):
    xml, _sexpr, mapping = _inputs(tmp_path)
    stub = write(tmp_path / "stub.net", '(export (version "E") (design (source "x")))')
    proc, payload = _run(xml, stub, mapping)
    assert proc.returncode == 1
    assert "sexpr_structure" in {c["name"] for c in payload["checks"] if not c["ok"]}


# ------------------------------------------------------------- real artifacts

def test_real_sexpr_export_parses_to_the_committed_contract():
    """The parser must work on the 445 KB artifact, not only on fixtures."""
    import tools.gates.netlist_parity as parity

    parsed = parity.load_sexpr_netlist(NET_REAL)
    assert len(parsed["endpoints"]) == 1142
    assert len(parsed["nets"]) == 220
    assert len(parsed["unconnected_nets"]) == 51
    assert parsed["shorts"] == []


def test_real_xml_export_parses_to_the_same_contract():
    import tools.gates.netlist_parity as parity

    parsed = parity.load_netlist(XML_REAL)
    assert len(parsed["endpoints"]) == 1142
    assert len(parsed["nets"]) == 220


def test_real_both_artifacts_agree_with_the_committed_pin_map(tmp_path):
    """The three committed sources of connectivity agree at this commit."""
    import tools.gates.expected_map as expected_map

    mapping = expected_map.from_pin_net_map(CSV_REAL, tmp_path / "expected.json")
    data = json.loads(mapping.read_text())
    assert len(data["nets"]) == 220
    assert sum(len(rows) for rows in data["nets"].values()) == 1142

    proc, payload = _run(XML_REAL, NET_REAL, mapping)
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"


def test_real_xml_injection_is_caught_against_the_real_sexpr(tmp_path):
    """Inject a rail split into a copy of the real XML: the pair must fail."""
    board = tmp_path / "board"
    board.mkdir()
    xml_copy = shutil.copy(XML_REAL, board / "ctrl-supply.xml")
    net_copy = shutil.copy(NET_REAL, board / "powerboard-reva.net")

    tree = ET.parse(xml_copy)
    nets = tree.getroot().find("nets")
    drive = next(net for net in nets.findall("net") if net.get("name") == "DRIVE12")
    moved = drive.findall("node")[0]
    moved.set("ref", "C15")
    nets.remove(drive)
    nets.append(drive)
    # Re-home one DRIVE12 node onto a new net: a split visible in XML only.
    split = ET.SubElement(nets, "net", {"code": "999", "name": "DRIVE12_SPLIT"})
    split.append(moved)
    drive.remove(moved)
    tree.write(xml_copy)

    import tools.gates.expected_map as expected_map

    mapping = expected_map.from_pin_net_map(CSV_REAL, tmp_path / "expected.json")
    proc, payload = _run(xml_copy, net_copy, mapping)
    assert proc.returncode == 1, proc.stdout
    assert payload["verdict"] == "FAIL"
    assert "DRIVE12_SPLIT" in payload["diffs"]["nets_extra"]
    assert {"ref": "C15", "pin": "1", "net": "DRIVE12"} in payload["diffs"]["missing"]
    assert "FAIL" in proc.stderr
