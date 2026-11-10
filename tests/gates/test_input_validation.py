"""Direct tests of the netlist_parity loaders and the manifest validators.

These cover the input-validation layer, where being lenient would mean
comparing something other than what the caller asked for.
"""

import json

import pytest

from gate_support import netlist_xml, write

from tools.gates import netlist_parity as np
from tools.gates import release_manifest as rm


# ------------------------------------------------------------ expected map

def test_load_expected_maps_form(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"nets": {"A": [["R1", "1"]]}}))
    endpoints, nets, nc = np.load_expected(path)
    assert endpoints == [("R1", "1", "A")]
    assert nets == ["A"]
    assert nc == []


def test_load_expected_endpoints_form(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"endpoints": [["R1", "1", "A"]]}))
    endpoints, nets, _nc = np.load_expected(path)
    assert endpoints == [("R1", "1", "A")]


def test_load_expected_rejects_broken_json(tmp_path):
    path = write(tmp_path / "e.json", "{")
    with pytest.raises(np.ExpectationError, match="not valid JSON"):
        np.load_expected(path)


def test_load_expected_rejects_non_object(tmp_path):
    path = write(tmp_path / "e.json", "[]")
    with pytest.raises(np.ExpectationError, match="must be a JSON object"):
        np.load_expected(path)


def test_load_expected_rejects_empty_nets(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"nets": {}}))
    with pytest.raises(np.ExpectationError, match="non-empty object"):
        np.load_expected(path)


def test_load_expected_rejects_nets_that_are_not_a_dict(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"nets": []}))
    with pytest.raises(np.ExpectationError, match="non-empty object"):
        np.load_expected(path)


def test_load_expected_rejects_net_without_a_row_list(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"nets": {"A": "R1.1"}}))
    with pytest.raises(np.ExpectationError, match="list of"):
        np.load_expected(path)


def test_load_expected_rejects_row_of_wrong_arity(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"nets": {"A": [["R1"]]}}))
    with pytest.raises(np.ExpectationError, match="pair"):
        np.load_expected(path)


def test_load_expected_rejects_endpoint_triple_of_wrong_arity(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"endpoints": [["R1", "1"]]}))
    with pytest.raises(np.ExpectationError, match="triple"):
        np.load_expected(path)


def test_load_expected_rejects_empty_endpoints(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"endpoints": []}))
    with pytest.raises(np.ExpectationError, match="non-empty list"):
        np.load_expected(path)


def test_load_expected_rejects_neither_key(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"other": 1}))
    with pytest.raises(np.ExpectationError, match="'nets' or 'endpoints'"):
        np.load_expected(path)


def test_load_expected_rejects_nc_not_a_list(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"nets": {"A": [["R1", "1"]]},
                                                 "nc": "R9.9"}))
    with pytest.raises(np.ExpectationError, match="'nc' must be a list"):
        np.load_expected(path)


def test_load_expected_rejects_malformed_nc_row(tmp_path):
    path = write(tmp_path / "e.json", json.dumps({"nets": {"A": [["R1", "1"]]},
                                                 "nc": [["R9"]]}))
    with pytest.raises(np.ExpectationError, match="nc row"):
        np.load_expected(path)


# ---------------------------------------------------------- netlist loader

def test_load_netlist_rejects_wrong_root(tmp_path):
    path = write(tmp_path / "n.xml", "<kicad/>")
    with pytest.raises(np.NetlistStructureError, match="root element"):
        np.load_netlist(path)


def test_load_netlist_rejects_missing_nets_element(tmp_path):
    path = write(tmp_path / "n.xml", "<export><design/></export>")
    with pytest.raises(np.NetlistStructureError, match="no <nets>"):
        np.load_netlist(path)


def test_load_netlist_rejects_unnamed_net(tmp_path):
    path = write(tmp_path / "n.xml", '<export><nets><net code="1"/></nets></export>')
    with pytest.raises(np.NetlistStructureError, match="without a name"):
        np.load_netlist(path)


def test_load_netlist_rejects_node_without_pin(tmp_path):
    path = write(tmp_path / "n.xml",
                 '<export><nets><net name="A"><node ref="R1"/></net></nets></export>')
    with pytest.raises(np.NetlistStructureError, match="without ref/pin"):
        np.load_netlist(path)


def test_load_netlist_rejects_empty_nets_document(tmp_path):
    path = write(tmp_path / "n.xml", "<export><nets/></export>")
    with pytest.raises(np.NetlistStructureError, match="declares no nets"):
        np.load_netlist(path)


def test_load_netlist_reports_shorts(tmp_path):
    path = write(tmp_path / "n.xml", netlist_xml({"A": [("R1", "1")], "B": [("R1", "1")]}))
    parsed = np.load_netlist(path)
    # Both rows are kept (so the caller can see where the pin went) and the
    # pair is also recorded as a short, which is what fails the gate.
    assert sorted(parsed["endpoints"]) == [("R1", "1", "A"), ("R1", "1", "B")]
    assert len(parsed["shorts"]) == 1
    assert parsed["shorts"][0]["nets"] == ["A", "B"]
    assert any(d["reason"].startswith("pin appears on more than one net")
               for d in parsed["duplicates"])


# ------------------------------------------------------ manifest validation

GOOD_MANIFEST = {
    "copper_layers": 2,
    "artifacts": [
        {"name": "F.Cu", "kind": "copper", "match": "*.gtl"},
        {"name": "B.Cu", "kind": "copper", "match": "*.gbl"},
        {"name": "Edge.Cuts", "kind": "outline", "match": "*.gm1"},
        {"name": "drill", "kind": "drill", "match": "*.drl"},
    ],
}


def _manifest(tmp_path, **overrides):
    data = json.loads(json.dumps(GOOD_MANIFEST))
    data.update(overrides)
    return write(tmp_path / "m.json", json.dumps(data))


def test_load_manifest_accepts_a_complete_one(tmp_path):
    data = rm.load_manifest(_manifest(tmp_path))
    assert len(data["artifacts"]) == 4


def test_load_manifest_rejects_broken_json(tmp_path):
    with pytest.raises(rm.ManifestError, match="not valid JSON"):
        rm.load_manifest(write(tmp_path / "m.json", "{"))


def test_load_manifest_rejects_non_object(tmp_path):
    with pytest.raises(rm.ManifestError, match="must be a JSON object"):
        rm.load_manifest(write(tmp_path / "m.json", "[]"))


def test_load_manifest_rejects_empty_artifacts(tmp_path):
    with pytest.raises(rm.ManifestError, match="non-empty list"):
        rm.load_manifest(_manifest(tmp_path, artifacts=[]))


def test_load_manifest_rejects_non_object_entry(tmp_path):
    with pytest.raises(rm.ManifestError, match="is not an object"):
        rm.load_manifest(_manifest(tmp_path, artifacts=["F.Cu"]))


@pytest.mark.parametrize("key", ["name", "kind", "match"])
def test_load_manifest_requires_each_key(tmp_path, key):
    artifacts = json.loads(json.dumps(GOOD_MANIFEST["artifacts"]))
    del artifacts[0][key]
    with pytest.raises(rm.ManifestError, match="lacks a non-empty"):
        rm.load_manifest(_manifest(tmp_path, artifacts=artifacts))


def test_load_manifest_rejects_unknown_kind(tmp_path):
    artifacts = json.loads(json.dumps(GOOD_MANIFEST["artifacts"]))
    artifacts[0]["kind"] = "cooper"
    with pytest.raises(rm.ManifestError, match="unknown kind"):
        rm.load_manifest(_manifest(tmp_path, artifacts=artifacts))


def test_load_manifest_rejects_duplicate_names(tmp_path):
    artifacts = json.loads(json.dumps(GOOD_MANIFEST["artifacts"]))
    artifacts.append(dict(artifacts[0]))
    with pytest.raises(rm.ManifestError, match="twice"):
        rm.load_manifest(_manifest(tmp_path, artifacts=artifacts))


def test_load_manifest_rejects_bad_min_bytes(tmp_path):
    artifacts = json.loads(json.dumps(GOOD_MANIFEST["artifacts"]))
    artifacts[0]["min_bytes"] = "big"
    with pytest.raises(rm.ManifestError, match="bad min_bytes"):
        rm.load_manifest(_manifest(tmp_path, artifacts=artifacts))


@pytest.mark.parametrize("dropped,dropped_kind", [
    ("Edge.Cuts", "outline"),
    ("drill", "drill"),
    ("F.Cu", "copper"),
])
def test_load_manifest_requires_each_required_kind(tmp_path, dropped, dropped_kind):
    """Dropping the last outline/drill entry is not run; dropping an outer
    copper layer contradicts copper_layers and is also not run."""
    artifacts = [a for a in GOOD_MANIFEST["artifacts"] if a["name"] != dropped]
    data = {"artifacts": artifacts, "copper_layers": 2}
    with pytest.raises(rm.ManifestError, match="required kind|copper_layers="):
        rm.load_manifest(write(tmp_path / "m.json", json.dumps(data)))


@pytest.mark.parametrize("bad", [0, -1, "2", 2.5])
def test_load_manifest_rejects_bad_copper_layers(tmp_path, bad):
    with pytest.raises(rm.ManifestError, match="positive integer"):
        rm.load_manifest(_manifest(tmp_path, copper_layers=bad))


def test_load_manifest_rejects_copper_count_mismatch(tmp_path):
    with pytest.raises(rm.ManifestError, match="copper_layers="):
        rm.load_manifest(_manifest(tmp_path, copper_layers=4))


# ------------------------------------------------------- artifact checkers

def test_check_gerber_accepts_kicad_output(tmp_path):
    from test_release_manifest import _gerber

    path = write(tmp_path / "a.gtl", _gerber())
    data = path.read_bytes()
    assert rm.check_gerber(path, data[:4096], data[-64:]) == (True, "")


def test_check_gerber_rejects_placeholder_marker(tmp_path):
    path = write(tmp_path / "a.gtl", "TODO: fix this later\n")
    data = path.read_bytes()
    ok, reason = rm.check_gerber(path, data, data)
    assert not ok and "placeholder" in reason


def test_check_gerber_rejects_wrong_preamble(tmp_path):
    path = write(tmp_path / "a.gtl", "hello world\n%FSLAX46Y46*%\n%MOMM*%\nD10*\nM02*\n")
    data = path.read_bytes()
    ok, reason = rm.check_gerber(path, data, data)
    assert not ok and "Gerber command" in reason


def test_check_gerber_rejects_missing_units(tmp_path):
    path = write(tmp_path / "a.gtl", "%FSLAX46Y46*%\nD10*\nM02*\n")
    data = path.read_bytes()
    ok, reason = rm.check_gerber(path, data, data)
    assert not ok and "%MO" in reason


def test_check_gerber_rejects_missing_apertures(tmp_path):
    path = write(tmp_path / "a.gtl", "%FSLAX46Y46*%\n%MOMM*%\nM02*\n")
    data = path.read_bytes()
    ok, reason = rm.check_gerber(path, data, data)
    assert not ok and "aperture" in reason


def test_check_gerber_accepts_g04_preamble(tmp_path):
    path = write(tmp_path / "a.gtl", "G04 comment*\n%FSLAX46Y46*%\n%MOMM*%\nD10*\nM02*\n")
    data = path.read_bytes()
    assert rm.check_gerber(path, data, data) == (True, "")


def test_check_drill_accepts_kicad_output(tmp_path):
    from test_release_manifest import _drill

    path = write(tmp_path / "a.drl", _drill())
    data = path.read_bytes()
    assert rm.check_drill(path, data[:4096], data[-64:]) == (True, "")


def test_check_drill_rejects_placeholder(tmp_path):
    path = write(tmp_path / "a.drl", "TODO drill\n")
    data = path.read_bytes()
    ok, reason = rm.check_drill(path, data, data)
    assert not ok and "placeholder" in reason


def test_check_drill_rejects_missing_units(tmp_path):
    path = write(tmp_path / "a.drl", "M48\nT1C0.3\nX1.0Y1.0\nM30\n")
    data = path.read_bytes()
    ok, reason = rm.check_drill(path, data, data)
    assert not ok and "METRIC/INCH" in reason


def test_check_drill_rejects_missing_tools(tmp_path):
    path = write(tmp_path / "a.drl", "M48\nMETRIC\nX1.0Y1.0\nM30\n")
    data = path.read_bytes()
    ok, reason = rm.check_drill(path, data, data)
    assert not ok and "tool definition" in reason


def test_check_drill_rejects_no_coordinates(tmp_path):
    path = write(tmp_path / "a.drl", "M48\nMETRIC\nT1C0.3\nM30\n")
    data = path.read_bytes()
    ok, reason = rm.check_drill(path, data, data)
    assert not ok and "coordinates" in reason


def test_check_drill_rejects_missing_end_marker(tmp_path):
    path = write(tmp_path / "a.drl", "M48\nMETRIC\nT1C0.3\nX1.0Y1.0\n")
    data = path.read_bytes()
    ok, reason = rm.check_drill(path, data, data)
    assert not ok and "M30" in reason


def test_check_pdf_accepts_real_pdf(tmp_path):
    from test_release_manifest import PDF_OK

    path = tmp_path / "a.pdf"
    path.write_bytes(PDF_OK)
    assert rm.check_pdf(path, PDF_OK[:4096], PDF_OK[-64:]) == (True, "")


def test_check_pdf_rejects_non_pdf(tmp_path):
    path = write(tmp_path / "a.pdf", "just text")
    data = path.read_bytes()
    ok, reason = rm.check_pdf(path, data, data)
    assert not ok and "not a PDF" in reason


def test_check_pdf_rejects_truncated_pdf(tmp_path):
    path = tmp_path / "a.pdf"
    path.write_bytes(b"%PDF-1.7\n1 0 obj\n")
    data = path.read_bytes()
    ok, reason = rm.check_pdf(path, data, data)
    assert not ok and "%%EOF" in reason


def test_check_job_accepts_json(tmp_path):
    path = write(tmp_path / "a.gbrjob", json.dumps({"Header": {}}))
    data = path.read_bytes()
    assert rm.check_job(path, data, data) == (True, "")


def test_check_job_rejects_broken_json(tmp_path):
    path = write(tmp_path / "a.gbrjob", "{")
    data = path.read_bytes()
    ok, reason = rm.check_job(path, data, data)
    assert not ok and "not valid JSON" in reason
