"""Tests for the manufacturing artifact inventory gate."""

import json

from gate_support import run_gate, write

def _gerber(draws=400, file_function="Copper,L1,Top"):
    """A structurally valid Gerber of realistic size (~10 kB)."""
    lines = [
        "%TF.GenerationSoftware,KiCad,Pcbnew,9.0.9*%",
        "%%TF.FileFunction,%s*%%" % file_function,
        "%TF.FilePolarity,Positive*%",
        "%FSLAX46Y46*%",
        "%MOMM*%",
        "G04 layer*",
        "%ADD10C,0.250000*%",
        "%ADD11R,1.000000X0.600000*%",
        "D10*",
    ]
    for index in range(draws):
        x = 1_000_000 + index * 1000
        y = 2_000_000 + index * 500
        lines.append("X%dY%dD02*" % (x, y))
        lines.append("X%dY%dD01*" % (x + 500, y + 500))
        lines.append("D11*")
    lines.append("M02*")
    return "\n".join(lines) + "\n"


GERBER_OK = _gerber()

def _drill(holes=40):
    lines = [
        "M48",
        "; DRILL file",
        "; FORMAT={-:-/ absolute / metric / decimal}",
        "; #@! TF.GenerationSoftware,Kicad,Pcbnew,9.0.9",
        "; #@! TF.FileFunction,MixedPlating,1,2",
        "FMAT,2",
        "METRIC",
        "; #@! TA.AperFunction,Plated,PTH,ViaDrill",
        "T1C0.300",
        "T2C0.500",
        "%",
        "G90",
        "G05",
        "T1",
    ]
    for index in range(holes):
        lines.append("X%d.%dY-%d.%d" % (3 + index, index % 10, 20 + index, index % 10))
    lines.append("T2")
    for index in range(holes // 2):
        lines.append("X%d.%dY-%d.%d" % (7 + index, index % 10, 30 + index, index % 10))
    lines.append("M30")
    return "\n".join(lines) + "\n"


DRILL_OK = _drill()


def _pdf(pages=60):
    """A minimal but multi-object PDF above the 1 KiB document floor."""
    objects = [
        b"%PDF-1.7",
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R >>\nendobj",
    ]
    stream = b"\n".join(b"BT /F1 9 Tf 40 %d Td (net %d) Tj ET" % (700 - i * 9, i)
                         for i in range(pages))
    objects.append(b"4 0 obj\n<< /Length %d >>\nstream\n" % len(stream) + stream
                   + b"\nendstream\nendobj")
    objects.append(b"trailer\n<< /Root 1 0 R /Size 5 >>\nstartxref\n0\n%%EOF\n")
    return b"\n".join(objects)


PDF_OK = _pdf()


def _manifest(copper_layers=2, documents=True):
    artifacts = [
        {"name": "F.Cu", "kind": "copper", "match": "*-F_Cu.gtl"},
        {"name": "B.Cu", "kind": "copper", "match": "*-B_Cu.gbl"},
        {"name": "F.Mask", "kind": "mask", "match": "*-F_Mask.gts"},
        {"name": "F.SilkS", "kind": "silk", "match": "*-F_Silkscreen.gto"},
        {"name": "Edge.Cuts", "kind": "outline", "match": "*-Edge_Cuts.gm1"},
        {"name": "drill", "kind": "drill", "match": "*.drl"},
        {"name": "job", "kind": "job", "match": "*.gbrjob"},
    ]
    if copper_layers >= 4:
        artifacts.insert(1, {"name": "In1.Cu", "kind": "copper", "match": "*-In1_Cu.gbr"})
        artifacts.insert(2, {"name": "In2.Cu", "kind": "copper", "match": "*-In2_Cu.gbr"})
    if documents:
        artifacts.append({"name": "schematic", "kind": "document", "match": "*.pdf"})
    return {
        "board": "board.kicad_pcb",
        "copper_layers": copper_layers,
        "artifacts": artifacts,
    }


def _populate(directory, *, gerber=GERBER_OK, drill=DRILL_OK, pdf=PDF_OK,
              inner=False, skip=()):
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "board-F_Cu.gtl": gerber,
        "board-B_Cu.gbl": gerber,
        "board-F_Mask.gts": gerber,
        "board-F_Silkscreen.gto": gerber,
        "board-Edge_Cuts.gm1": gerber,
        "board.drl": drill,
        "board-job.gbrjob": json.dumps({
            "Header": {"GenerationSoftware": {"Vendor": "KiCad", "Application": "Pcbnew",
                                              "Version": "9.0.9"},
                       "CreationDate": "2026-11-10T00:00:00+01:00"},
            "GeneralSpecs": {"ProjectId": {"Name": "board", "GUID": "0" * 32,
                                           "Revision": "A"},
                             "Size": {"X": 50.0, "Y": 40.0},
                             "LayerNumber": 2, "BoardThickness": 1.6},
            "FilesAttributes": [
                {"Path": "board-F_Cu.gtl", "FileFunction": "Copper,L1,Top",
                 "FilePolarity": "Positive"},
                {"Path": "board-B_Cu.gbl", "FileFunction": "Copper,L2,Bot",
                 "FilePolarity": "Positive"},
            ],
        }, indent=2),
        "board.pdf": pdf,
    }
    if inner:
        files["board-In1_Cu.gbr"] = gerber
        files["board-In2_Cu.gbr"] = gerber
    for name, content in files.items():
        if name in skip:
            continue
        target = directory / name
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content)
    return directory


def _run(tmp_path, manifest, directory, extra=()):
    mapping = write(tmp_path / "manifest.json", json.dumps(manifest, indent=1))
    return run_gate(
        "release_manifest",
        ["--manifest", mapping, "--artifacts", directory, *extra],
    )


# ---------------------------------------------------------------- PASS paths

def test_complete_two_layer_packet_passes(tmp_path):
    proc, payload = _run(tmp_path, _manifest(), _populate(tmp_path / "out"))
    assert proc.returncode == 0, proc.stderr
    assert payload["verdict"] == "PASS"
    assert payload["evidence"]["artifacts_checked"] == 8
    assert payload["evidence"]["copper_layers_expected"] == 2
    assert payload["evidence"]["copper_layers_found"] == 2


def test_four_layer_packet_with_inner_files_passes(tmp_path):
    proc, payload = _run(
        tmp_path, _manifest(copper_layers=4), _populate(tmp_path / "out", inner=True)
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["evidence"]["copper_layers_found"] == 4


def test_hashes_are_recorded_for_every_artifact(tmp_path):
    proc, payload = _run(tmp_path, _manifest(), _populate(tmp_path / "out"))
    assert proc.returncode == 0
    hashes = payload["evidence"]["hashes"]
    assert len(hashes) == 8
    assert all(len(value) == 64 for value in hashes.values())


def test_relative_and_absolute_paths_work(tmp_path):
    proc, payload = _run(tmp_path, _manifest(), _populate(tmp_path / "out"))
    assert proc.returncode == 0
    manifest = write(tmp_path / "m.json", json.dumps(_manifest()))
    proc2, payload2 = run_gate(
        "release_manifest", ["--manifest", "m.json", "--artifacts", "out"], cwd=tmp_path
    )
    assert proc2.returncode == 0, proc2.stderr


# ------------------------------------ negative controls (the reported defect)

def test_negative_control_placeholder_gerber_fails(tmp_path):
    """The balloon `generate_gerbers.py` class of defect: text, not Gerber."""
    placeholder = "TODO: generate gerbers here\n"
    proc, payload = _run(
        tmp_path, _manifest(), _populate(tmp_path / "out", gerber=placeholder)
    )
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    bad = [f for f in payload["findings"] if f["code"] == "placeholder_or_invalid"]
    assert len(bad) == 5  # five copper/mask/silk/outline files
    assert "F.Cu" in {f["artifact"] for f in bad}


def test_negative_control_tiny_gerber_fails(tmp_path):
    """Structurally valid but 300 bytes: no real copper layer looks like that."""
    tiny = _gerber(draws=2)
    assert len(tiny) < 512
    proc, payload = _run(tmp_path, _manifest(), _populate(tmp_path / "out", gerber=tiny))
    assert proc.returncode == 1
    codes = {f["code"] for f in payload["findings"]}
    assert "suspiciously_small" in codes
    assert "placeholder_or_invalid" not in codes


def test_negative_control_truncated_gerber_without_end_of_file_fails(tmp_path):
    truncated = GERBER_OK.replace("M02*\n", "")
    proc, payload = _run(tmp_path, _manifest(), _populate(tmp_path / "out", gerber=truncated))
    assert proc.returncode == 1
    codes = {f["code"] for f in payload["findings"]}
    assert "placeholder_or_invalid" in codes


def test_negative_control_gerber_without_format_spec_fails(tmp_path):
    truncated = "\n".join(
        line for line in GERBER_OK.splitlines()
        if not line.startswith("%FS")
    ) + "\n"
    proc, payload = _run(tmp_path, _manifest(), _populate(tmp_path / "out", gerber=truncated))
    assert proc.returncode == 1
    assert "placeholder_or_invalid" in {f["code"] for f in payload["findings"]}


def test_negative_control_deleted_artifact_fails(tmp_path):
    out = _populate(tmp_path / "out", skip=("board-Edge_Cuts.gm1",))
    proc, payload = _run(tmp_path, _manifest(), out)
    assert proc.returncode == 1
    missing = [f for f in payload["findings"] if f["code"] == "missing"]
    assert [f["artifact"] for f in missing] == ["Edge.Cuts"]


def test_negative_control_inner_layer_without_file_fails(tmp_path):
    """Four-layer manifest, two-layer export: exactly the documented defect."""
    out = _populate(tmp_path / "out")  # no inner files
    proc, payload = _run(tmp_path, _manifest(copper_layers=4), out)
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"
    missing = {f["artifact"] for f in payload["findings"] if f["code"] == "missing"}
    assert {"In1.Cu", "In2.Cu"} <= missing
    assert payload["evidence"]["copper_layers_found"] == 2
    assert "inner" in proc.stderr.lower()


def test_negative_control_self_contradictory_manifest_is_not_run(tmp_path):
    """copper_layers=4 but only two copper entries: the manifest cannot grade.

    Exit 2, not exit 1, on purpose: the gate cannot tell whether the manifest
    or the artifact set is the wrong one, so it must refuse rather than pick a
    verdict. Either way the caller sees a nonzero status.
    """
    manifest = _manifest()
    manifest["copper_layers"] = 4  # claims four layers, lists only two
    out = _populate(tmp_path / "out", inner=True)
    proc, payload = _run(tmp_path, manifest, out)
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"
    assert "copper_layers=4" in payload["reason"]


def test_negative_control_drill_without_end_fails(tmp_path):
    proc, payload = _run(
        tmp_path, _manifest(), _populate(tmp_path / "out", drill=DRILL_OK.replace("M30\n", ""))
    )
    assert proc.returncode == 1
    assert "drill" in {f["artifact"] for f in payload["findings"] if f["code"] == "placeholder_or_invalid"}


def test_negative_control_empty_drill_fails(tmp_path):
    proc, payload = _run(tmp_path, _manifest(), _populate(tmp_path / "out", drill=""))
    assert proc.returncode == 1
    codes = {f["code"] for f in payload["findings"]}
    assert {"suspiciously_small", "empty"} & codes


def test_negative_control_placeholder_pdf_fails(tmp_path):
    proc, payload = _run(
        tmp_path, _manifest(), _populate(tmp_path / "out", pdf=b"not a pdf at all\n")
    )
    assert proc.returncode == 1
    assert "schematic" in {f["artifact"] for f in payload["findings"]}


def test_negative_control_truncated_pdf_fails(tmp_path):
    proc, payload = _run(
        tmp_path, _manifest(), _populate(tmp_path / "out", pdf=PDF_OK[:40])
    )
    assert proc.returncode == 1
    assert payload["verdict"] == "FAIL"


def test_negative_control_unmanifested_layer_file_fails(tmp_path):
    out = _populate(tmp_path / "out")
    (out / "board-In3_Cu.gbr").write_text(GERBER_OK)
    proc, payload = _run(tmp_path, _manifest(), out)
    assert proc.returncode == 1
    extra = [f for f in payload["findings"] if f["code"] == "unexpected"]
    assert "board-In3_Cu.gbr" in {f["artifact"] for f in extra}


def test_negative_control_two_files_matching_one_entry_fails(tmp_path):
    out = _populate(tmp_path / "out")
    (out / "board-copy-B_Cu.gbl").write_text(GERBER_OK)
    proc, payload = _run(tmp_path, _manifest(), out)
    assert proc.returncode == 1
    assert "ambiguous" in {f["code"] for f in payload["findings"]}


def test_negative_control_artifacts_directory_missing_fails(tmp_path):
    proc, payload = _run(tmp_path, _manifest(), tmp_path / "absent")
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


# ------------------------------------------------------- NOT RUN (exit 2)

def test_no_arguments_is_not_run():
    proc, payload = run_gate("release_manifest", [])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_missing_manifest_is_not_run(tmp_path):
    out = _populate(tmp_path / "out")
    proc, payload = run_gate(
        "release_manifest", ["--manifest", tmp_path / "absent.json", "--artifacts", out]
    )
    assert proc.returncode == 2


def test_unparsable_manifest_is_not_run(tmp_path):
    out = _populate(tmp_path / "out")
    bad = write(tmp_path / "bad.json", "{nope")
    proc, payload = run_gate("release_manifest", ["--manifest", bad, "--artifacts", out])
    assert proc.returncode == 2
    assert payload["verdict"] == "NOT RUN"


def test_manifest_without_artifacts_is_not_run(tmp_path):
    out = _populate(tmp_path / "out")
    bad = write(tmp_path / "bad.json", json.dumps({"board": "x", "artifacts": []}))
    proc, payload = run_gate("release_manifest", ["--manifest", bad, "--artifacts", out])
    assert proc.returncode == 2


def test_manifest_without_outline_is_not_run(tmp_path):
    manifest = _manifest()
    manifest["artifacts"] = [a for a in manifest["artifacts"] if a["kind"] != "outline"]
    proc, payload = _run(tmp_path, manifest, _populate(tmp_path / "out"))
    assert proc.returncode == 2
    assert "outline" in json.dumps(payload).lower()


def test_manifest_without_drill_is_not_run(tmp_path):
    manifest = _manifest()
    manifest["artifacts"] = [a for a in manifest["artifacts"] if a["kind"] != "drill"]
    proc, payload = _run(tmp_path, manifest, _populate(tmp_path / "out"))
    assert proc.returncode == 2


def test_unreadable_artifact_is_a_failure_not_a_skip(tmp_path):
    out = _populate(tmp_path / "out")
    target = out / "board-F_Cu.gtl"
    target.chmod(0)
    try:
        proc, payload = _run(tmp_path, _manifest(), out)
    finally:
        target.chmod(0o644)
    assert proc.returncode in (1, 2)
    assert payload["verdict"] in ("FAIL", "NOT RUN")


def test_extra_positional_argument_is_rejected(tmp_path):
    out = _populate(tmp_path / "out")
    manifest = write(tmp_path / "m.json", json.dumps(_manifest()))
    proc, _ = run_gate(
        "release_manifest", ["--manifest", manifest, "--artifacts", out, "surplus"]
    )
    assert proc.returncode == 2
