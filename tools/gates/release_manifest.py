"""Manufacturing artifact inventory gate: reject placeholders and missing layers.

Why this exists
---------------
The audited upstream "Gerber generator" was a 21-line placeholder that emitted
no Gerbers at all, and the export wrapper ignored the CLI return code and never
compared the files on disk with the layer list it asked for. A four-layer board
whose export silently emitted only two copper layers looked exactly like a
good release.

This gate grades a *directory of exported artifacts* against a manifest that
names every expected layer. It fails on:

* a missing expected artifact, including an inner copper layer the manifest
  and the ``copper_layers`` count both require;
* a placeholder or structurally invalid file (text where Gerber belongs, no
  end-of-file marker, no format spec, a non-PDF ``.pdf``);
* a file smaller than the ``min_bytes`` floor for its kind;
* more than one file matching one manifest entry, or a layer file nobody
  declared.

It does **not** prove: copper is electrically correct, the drill is plated
correctly, the outline is closed, the stackup is the one you think, or that a
fab will accept the packet. See README.md.

Exit codes: 0 PASS, 1 FAIL (packet incomplete/placeholder), 2 NOT RUN
(invocation, manifest or artifact-directory problems).
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

from ._common import (
    Checks,
    StrictParser,
    UsageError,
    finish,
    guard,
    is_readable_file,
    sha256_file,
)

GATE = "release_manifest"

MIN_BYTES = {
    "copper": 2048,
    "mask": 512,
    "silk": 256,
    "paste": 128,
    "outline": 128,
    "drill": 256,
    "job": 64,
    "document": 1024,
    "other": 64,
}

GERBER_END = re.compile(r"M02\*?\s*$")
# KiCad emits %FSLAX46Y46*% : leading-zero/absolute, 4.6 in X and Y.
GERBER_FORMAT = re.compile(r"%FS[LT]AX\d+Y\d+\*%")

PLACEHOLDER_MARKERS = (
    "TODO",
    "FIXME",
    "placeholder",
    "PLACEHOLDER",
    "not implemented",
    "lorem ipsum",
    "generate gerbers here",
)

REQUIRED_KINDS = ("copper", "outline", "drill")

COPPER_KINDS = ("copper",)


class ManifestError(UsageError):
    """The manifest cannot be used to grade anything."""


def build_parser():
    parser = StrictParser(
        prog="python3 -m tools.gates.release_manifest",
        description="Verify a manufacturing artifact inventory against an "
                    "expected layer manifest.",
    )
    parser.add_argument("--manifest", required=True, help="expected manifest (JSON)")
    parser.add_argument("--artifacts", required=True,
                        help="directory holding the exported artifacts")
    parser.add_argument("--allow-unexpected", action="store_true", dest="allow_unexpected",
                        help="permit files that no manifest entry claims")
    return parser


def load_manifest(path):
    try:
        data = json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise ManifestError("manifest is not valid JSON: %s" % exc)
    if not isinstance(data, dict):
        raise ManifestError("manifest must be a JSON object")

    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ManifestError("manifest 'artifacts' must be a non-empty list")

    seen = set()
    for entry in artifacts:
        if not isinstance(entry, dict):
            raise ManifestError("manifest artifact %r is not an object" % (entry,))
        for key in ("name", "kind", "match"):
            if not key in entry or not isinstance(entry[key], str) or not entry[key]:
                raise ManifestError("manifest artifact %r lacks a non-empty %r"
                                    % (entry.get("name", entry), key))
        if entry["kind"] not in MIN_BYTES:
            raise ManifestError(
                "manifest artifact %r has unknown kind %r (known: %s)"
                % (entry["name"], entry["kind"], ", ".join(sorted(MIN_BYTES))))
        if entry["name"] in seen:
            raise ManifestError("manifest declares %r twice" % entry["name"])
        seen.add(entry["name"])
        if "min_bytes" in entry and (
                not isinstance(entry["min_bytes"], int) or entry["min_bytes"] < 0):
            raise ManifestError("manifest artifact %r has a bad min_bytes" % entry["name"])

    kinds = {entry["kind"] for entry in artifacts}
    missing_kinds = [kind for kind in REQUIRED_KINDS if kind not in kinds]
    if missing_kinds:
        raise ManifestError(
            "manifest must declare at least one of each required kind; missing %s"
            % ", ".join(missing_kinds))

    copper_layers = data.get("copper_layers")
    if copper_layers is not None:
        if not isinstance(copper_layers, int) or copper_layers < 1:
            raise ManifestError("manifest 'copper_layers' must be a positive integer")
        declared_copper = sum(1 for entry in artifacts if entry["kind"] in COPPER_KINDS)
        if declared_copper != copper_layers:
            raise ManifestError(
                "manifest copper_layers=%d but %d copper artifacts are declared"
                % (copper_layers, declared_copper))

    return data


def _read_head(path, size=4096):
    with open(path, "rb") as handle:
        return handle.read(size)


def _read_tail(path, size=64):
    with open(path, "rb") as handle:
        handle.seek(0, 2)
        end = handle.tell()
        handle.seek(max(0, end - size))
        return handle.read(size)


def check_gerber(path, data_head, data_tail):
    """Return (ok, reason) for a Gerber file. Structure, not correctness."""
    text_head = data_head.decode("latin-1")
    text_tail = data_tail.decode("latin-1")
    lowered = text_head.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in lowered:
            return False, "placeholder text %r found in file" % marker
    if not text_head.lstrip().startswith("%") and not text_head.lstrip().startswith("G04"):
        return False, "does not start with a Gerber command"
    if not GERBER_FORMAT.search(text_head):
        return False, "no %FSLAX..% format specification"
    if "%MO" not in text_head:
        return False, "no %MO..% unit specification"
    if "D" not in text_head:
        return False, "no aperture (Dnn) definitions"
    if not GERBER_END.search(text_tail.strip()):
        return False, "truncated: no M02 end-of-file marker"
    return True, ""


def check_drill(path, data_head, data_tail):
    text_head = data_head.decode("latin-1")
    text_tail = data_tail.decode("latin-1")
    lowered = text_head.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in lowered:
            return False, "placeholder text %r found in file" % marker
    if not text_head.lstrip().startswith("M48"):
        return False, "does not start with M48 (Excellon header)"
    if "METRIC" not in text_head.upper() and "INCH" not in text_head.upper():
        return False, "no METRIC/INCH unit declaration"
    if not re.search(r"^T\d+C?[\d.]+", text_head, re.MULTILINE) and "T1C" not in text_head:
        return False, "no tool definition (TnnC...)"
    if "M30" not in text_tail and "M30" not in text_head:
        return False, "truncated: no M30 end-of-file marker"
    coordinates = re.findall(r"X-?[\d.]+Y-?[\d.]+", text_head + text_tail)
    if not coordinates:
        return False, "no drill coordinates"
    return True, ""


def check_pdf(path, data_head, data_tail):
    if not data_head.lstrip()[:5] == b"%PDF-":
        return False, "not a PDF (missing %PDF- header)"
    if b"%%EOF" not in data_tail:
        return False, "truncated: no %%EOF trailer"
    return True, ""


def check_job(path, data_head, _data_tail):
    try:
        json.loads(Path(path).read_text())
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        return False, "gerber job file is not valid JSON: %s" % exc
    return True, ""


CHECKERS = {
    "copper": check_gerber,
    "mask": check_gerber,
    "silk": check_gerber,
    "paste": check_gerber,
    "outline": check_gerber,
    "drill": check_drill,
    "document": check_pdf,
    "job": check_job,
    "other": lambda *_args: (True, ""),
}


def grade(argv):
    args = build_parser().parse_args(argv)
    manifest = load_manifest(args.manifest)

    artifacts_dir = Path(args.artifacts)
    if not artifacts_dir.exists():
        raise UsageError("artifact directory does not exist: %s" % artifacts_dir)
    if not artifacts_dir.is_dir():
        raise UsageError("artifact path is not a directory: %s" % artifacts_dir)

    checks = Checks()
    findings = []
    matches_by_name = {}
    claimed = set()

    for entry in manifest["artifacts"]:
        name = entry["name"]
        pattern = entry["match"]
        candidates = sorted(
            child for child in artifacts_dir.iterdir()
            if child.is_file() and fnmatch.fnmatch(child.name, pattern)
        )
        matches_by_name[name] = [child.name for child in candidates]

        if not candidates:
            findings.append({
                "artifact": name,
                "code": "missing",
                "detail": "no file matching %r in %s" % (pattern, artifacts_dir),
                "kind": entry["kind"],
            })
            continue
        if len(candidates) > 1:
            findings.append({
                "artifact": name,
                "code": "ambiguous",
                "detail": "%d files match %r: %s"
                          % (len(candidates), pattern, ", ".join(c.name for c in candidates)),
                "kind": entry["kind"],
            })
            continue

        chosen = candidates[0]
        claimed.add(chosen.name)
        readable, why = is_readable_file(chosen)
        if not readable:
            findings.append({"artifact": name, "code": "unreadable",
                             "detail": why, "kind": entry["kind"]})
            continue

        size = chosen.stat().st_size
        floor = entry.get("min_bytes", MIN_BYTES[entry["kind"]])
        if size == 0:
            findings.append({"artifact": name, "code": "empty",
                             "detail": "%s is zero bytes" % chosen.name,
                             "kind": entry["kind"]})
            continue

        # Content first: a 28-byte file that says "TODO" is a placeholder, and
        # that diagnosis is more useful than "too small". Size is the fallback
        # for files that pass the structural checks but cannot be real.
        head = _read_head(chosen)
        tail = _read_tail(chosen)
        ok, reason = CHECKERS[entry["kind"]](chosen, head, tail)
        if not ok:
            findings.append({"artifact": name, "code": "placeholder_or_invalid",
                             "detail": "%s: %s" % (chosen.name, reason),
                             "kind": entry["kind"]})
            continue
        if size < floor:
            findings.append({
                "artifact": name,
                "code": "suspiciously_small",
                "detail": "%s is %d bytes, below the %d-byte floor for %s"
                          % (chosen.name, size, floor, entry["kind"]),
                "kind": entry["kind"],
            })
            continue

    all_files = sorted(child.name for child in artifacts_dir.iterdir() if child.is_file())
    unclaimed = [name for name in all_files if name not in claimed]
    if unclaimed and not args.allow_unexpected:
        for name in unclaimed:
            findings.append({
                "artifact": name,
                "code": "unexpected",
                "detail": "%s is in the release directory but no manifest entry claims it"
                          % name,
                "kind": None,
            })

    copper_entries = [e for e in manifest["artifacts"] if e["kind"] in COPPER_KINDS]
    copper_found = sum(
        1 for entry in copper_entries
        if any(matches_by_name.get(entry["name"], []))
        and not any(f["artifact"] == entry["name"] for f in findings)
    )
    declared_layers = manifest.get("copper_layers")

    missing_copper = sorted(
        entry["name"] for entry in copper_entries
        if not matches_by_name.get(entry["name"])
    )

    checks.require("manifest_readable", True, "%d artifacts declared" % len(manifest["artifacts"]))
    checks.require(
        "all_artifacts_present",
        not any(f["code"] == "missing" for f in findings),
        "missing: %s" % ", ".join(f["artifact"] for f in findings if f["code"] == "missing"),
    )
    checks.require(
        "artifacts_unambiguous",
        not any(f["code"] == "ambiguous" for f in findings),
        "ambiguous: %s" % ", ".join(f["artifact"] for f in findings if f["code"] == "ambiguous"),
    )
    checks.require(
        "artifacts_valid",
        not any(f["code"] in ("placeholder_or_invalid", "suspiciously_small", "empty",
                              "unreadable") for f in findings),
        "invalid: %s" % ", ".join(
            f["artifact"] for f in findings
            if f["code"] in ("placeholder_or_invalid", "suspiciously_small", "empty",
                             "unreadable")),
    )
    checks.require(
        "no_unexpected_files",
        args.allow_unexpected or not unclaimed,
        "unclaimed: %s" % ", ".join(unclaimed),
    )
    checks.require(
        "copper_layers_complete",
        not missing_copper,
        "inner/outer copper artifacts with no file: %s" % ", ".join(missing_copper),
    )
    if declared_layers is not None:
        checks.require(
            "copper_layer_manifest",
            copper_found == declared_layers,
            "%d of %d declared copper layers have a file" % (copper_found, declared_layers),
        )

    evidence = {
        "artifacts_dir": str(artifacts_dir.resolve()),
        "manifest": str(Path(args.manifest).resolve()),
        "manifest_sha256": sha256_file(args.manifest),
        "artifacts_checked": len(manifest["artifacts"]),
        "artifacts_present": len(manifest["artifacts"]) - sum(
            1 for f in findings if f["code"] == "missing"),
        "copper_layers_expected": declared_layers,
        "copper_layers_found": copper_found,
        "inner_layer_artifacts": [e["name"] for e in copper_entries
                                  if e["name"] not in ("F.Cu", "B.Cu")],
        "hashes": {},
        "files": all_files,
    }
    for entry in manifest["artifacts"]:
        names = matches_by_name.get(entry["name"], [])
        if len(names) == 1:
            path = artifacts_dir / names[0]
            readable, _why = is_readable_file(path)
            evidence["hashes"][entry["name"]] = sha256_file(path) if readable else None

    human = []
    for finding in findings[:20]:
        human.append("%s: %s (%s)" % (finding["code"], finding["artifact"], finding["detail"]))
    if missing_copper:
        inner = [name for name in missing_copper if name not in ("F.Cu", "B.Cu")]
        if inner:
            human.append(
                "inner copper layer(s) requested but not exported: %s "
                "(an export exit code of 0 does not prove layer coverage)" % ", ".join(inner))

    return finish(GATE, checks, evidence=evidence, findings=findings, human_lines=human)


def main(argv=None):
    return guard(GATE, grade, argv)


if __name__ == "__main__":
    sys.exit(main())
