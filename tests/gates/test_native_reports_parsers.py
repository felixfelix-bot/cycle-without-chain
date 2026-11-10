"""Direct tests of the native_reports parsers and helper probes.

The CLI-level tests prove the gate's verdicts. These cover the structural
validation inside each parser, where a lenient reading would turn a malformed
report into "zero violations".
"""

import json

import pytest

from gate_support import drc_report, erc_report, netlist_xml

from tools.gates import native_reports as nr


# ---------------------------------------------------------------- DRC parsing

def test_parse_drc_accepts_a_minimal_report():
    data = nr._parse_drc(drc_report())
    assert data["violations"] == []


@pytest.mark.parametrize("payload", ["[]", '"text"', "3", "null"])
def test_parse_drc_rejects_non_object(payload):
    with pytest.raises(ValueError, match="not a JSON object"):
        nr._parse_drc(payload)


@pytest.mark.parametrize("key", ["source", "violations", "unconnected_items"])
def test_parse_drc_rejects_each_missing_key(key):
    data = json.loads(drc_report())
    del data[key]
    with pytest.raises(ValueError, match="missing required key"):
        nr._parse_drc(json.dumps(data))


def test_parse_drc_rejects_non_list_violations():
    data = json.loads(drc_report())
    data["violations"] = {"count": 0}
    with pytest.raises(ValueError, match="violations is not a list"):
        nr._parse_drc(json.dumps(data))


def test_parse_drc_rejects_non_list_unconnected():
    data = json.loads(drc_report())
    data["unconnected_items"] = None
    with pytest.raises(ValueError, match="unconnected_items is not a list"):
        nr._parse_drc(json.dumps(data))


# ---------------------------------------------------------------- ERC parsing

def test_parse_erc_accepts_a_minimal_report():
    data = nr._parse_erc(erc_report())
    assert len(data["sheets"]) == 1


def test_parse_erc_rejects_non_object():
    with pytest.raises(ValueError, match="not a JSON object"):
        nr._parse_erc("[]")


def test_parse_erc_rejects_missing_sheets():
    data = json.loads(erc_report())
    del data["sheets"]
    with pytest.raises(ValueError, match="missing required key"):
        nr._parse_erc(json.dumps(data))


def test_parse_erc_rejects_non_list_sheets():
    data = json.loads(erc_report())
    data["sheets"] = "nope"
    with pytest.raises(ValueError, match="sheets is not a list"):
        nr._parse_erc(json.dumps(data))


def test_parse_erc_rejects_sheet_without_violations_key():
    data = json.loads(erc_report())
    data["sheets"] = [{"path": "/"}]
    with pytest.raises(ValueError, match="no violations list"):
        nr._parse_erc(json.dumps(data))


def test_parse_erc_rejects_sheet_with_non_list_violations():
    data = json.loads(erc_report())
    data["sheets"] = [{"path": "/", "violations": 0}]
    with pytest.raises(ValueError, match="violations is not a list"):
        nr._parse_erc(json.dumps(data))


def test_parse_erc_rejects_sheet_that_is_not_an_object():
    data = json.loads(erc_report())
    data["sheets"] = ["/"]
    with pytest.raises(ValueError, match="no violations list"):
        nr._parse_erc(json.dumps(data))


# ------------------------------------------------------------- netlist probe

def test_parse_netlist_counts_nodes():
    assert nr._parse_netlist(netlist_xml({"VIN": [("R1", "1"), ("R2", "1")]})) == 2


def test_parse_netlist_rejects_wrong_root():
    with pytest.raises(ValueError, match="root element"):
        nr._parse_netlist("<html></html>")


def test_parse_netlist_rejects_missing_nets():
    with pytest.raises(ValueError, match="no <nets>"):
        nr._parse_netlist('<export version="E"><design/></export>')


def test_parse_netlist_rejects_unnamed_net():
    with pytest.raises(ValueError, match="without a name"):
        nr._parse_netlist('<export version="E"><nets><net code="1"/></nets></export>')


def test_parse_netlist_rejects_node_without_ref_or_pin():
    with pytest.raises(ValueError, match="without ref/pin"):
        nr._parse_netlist(
            '<export version="E"><nets><net name="A"><node ref="R1"/></net></nets></export>'
        )


# --------------------------------------------------------------- object probes

def test_count_pads_counts_pads_and_footprints(tmp_path):
    board = tmp_path / "b.kicad_pcb"
    board.write_text('(kicad_pcb (footprint "a" (pad "1")) (footprint "b" (pad "2")))')
    assert nr._count_pads(board) == (2, 2)


def test_count_pads_returns_zero_when_unreadable(tmp_path):
    assert nr._count_pads(tmp_path / "absent.kicad_pcb") == (0, 0)


def test_count_symbols_handles_both_spellings(tmp_path):
    sch = tmp_path / "s.kicad_sch"
    sch.write_text('(symbol (lib_id "Device:R"))\n(symbol (lib_id "Device:C"))')
    assert nr._count_symbols(sch) == 2


def test_count_symbols_returns_zero_when_unreadable(tmp_path):
    assert nr._count_symbols(tmp_path / "absent.kicad_sch") == 0


def test_count_symbols_in_hierarchy_includes_sub_sheets(tmp_path):
    """A hierarchical root holds no symbols of its own: count siblings too."""
    (tmp_path / "root.kicad_sch").write_text("(kicad_sch (sheet (uuid \"x\")))")
    (tmp_path / "child-a.kicad_sch").write_text('(symbol (lib_id "Device:R"))')
    (tmp_path / "child-b.kicad_sch").write_text(
        '(symbol (lib_id "Device:C"))\n(symbol (lib_id "Device:L"))')
    assert nr._count_symbols_in_hierarchy(tmp_path / "root.kicad_sch") == 3


def test_count_symbols_in_hierarchy_falls_back_to_the_named_file(tmp_path):
    lone = tmp_path / "only.kicad_sch"
    lone.write_text('(symbol (lib_id "Device:R"))')
    assert nr._count_symbols_in_hierarchy(lone) == 1


# ------------------------------------------------------------------ argv shape

def test_severity_all_flag_is_forwarded():
    argv = nr._command("drc", "/usr/bin/kicad-cli", "b.kicad_pcb", "out.json", True)
    assert "--severity-all" in argv
    argv = nr._command("drc", "/usr/bin/kicad-cli", "b.kicad_pcb", "out.json", False)
    assert "--severity-error" in argv
    assert "--severity-all" not in argv


def test_erc_and_netlist_commands_are_shaped_correctly():
    erc = nr._command("erc", "kc", "s.kicad_sch", "e.json", True)
    assert erc[:3] == ["kc", "sch", "erc"]
    netlist = nr._command("netlist", "kc", "s.kicad_sch", "n.xml", False)
    assert netlist[:4] == ["kc", "sch", "export", "netlist"]
    assert "--format" in netlist and "kicadxml" in netlist
