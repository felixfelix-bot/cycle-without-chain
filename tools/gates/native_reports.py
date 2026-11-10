"""Fail-closed wrapper around native KiCad exports and reports.

Why this exists
---------------
The audited upstream pipeline ran native DRC, and when the subprocess failed
or the report was absent it still returned ``{'violations': [], ...}`` and the
caller announced "DRC CLEAN". Two independent defects produce that:

1. **fail-open report handling** — a missing/unparsable report becomes an
   empty violation list, i.e. zero defects;
2. **a fixed report path** — a report left over from an earlier run is graded
   as if it belonged to this one.

This gate closes both. Every run gets its own directory
(``<outdir>/<utc>-<pid>-<random>/``), so a previous run's report can neither be
found nor reused, and every failure mode above is a recorded FAIL.

Usage
-----
    python3 -m tools.gates.native_reports \
        --kind drc --input board.kicad_pcb --outdir /tmp/gates \
        --kicad-cli kicad-cli

    python3 -m tools.gates.native_reports \
        --kind erc --input board.kicad_sch --outdir /tmp/gates --kicad-cli kicad-cli

    python3 -m tools.gates.native_reports \
        --kind netlist --input board.kicad_sch --outdir /tmp/gates --kicad-cli kicad-cli
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from ._common import (
    Checks,
    StrictParser,
    UsageError,
    finish,
    guard,
    is_readable_file,
    new_run_dir,
    not_run,
    require_inputs,
    sha256_file,
)

GATE = "native_reports"

KINDS = ("drc", "erc", "netlist")

REPORT_NAMES = {"drc": "drc.json", "erc": "erc.json", "netlist": "netlist.xml"}

REQUIRED_KEYS = {
    "drc": ("source", "violations", "unconnected_items"),
    "erc": ("sheets",),
}

DEFAULT_TIMEOUT = 900.0
DEFAULT_MIN_OBJECTS = 1


def build_parser():
    parser = StrictParser(
        prog="python3 -m tools.gates.native_reports",
        description="Fail-closed native KiCad export/DRC/ERC runner.",
    )
    parser.add_argument("--kind", required=True, choices=KINDS,
                        help="which native artifact to produce and grade")
    parser.add_argument("--input", required=True, help="schematic or board to grade")
    parser.add_argument("--outdir", required=True,
                        help="parent directory for the per-run output directory")
    parser.add_argument("--kicad-cli", required=True, dest="kicad_cli",
                        help="kicad-cli executable to invoke")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help="subprocess timeout in seconds (default %(default)s)")
    parser.add_argument("--min-objects", type=int, default=DEFAULT_MIN_OBJECTS,
                        dest="min_objects",
                        help="minimum graded objects for a PASS (default %(default)s)")
    parser.add_argument("--severity-all", action="store_true", dest="severity_all",
                        help="include warning and exclusion severities")
    return parser


def _command(kind, tool, input_path, report_path, severity_all):
    if kind == "drc":
        argv = [tool, "pcb", "drc", "--format", "json", "--exit-code-violations"]
        argv += ["--severity-all"] if severity_all else ["--severity-error"]
        argv += ["-o", str(report_path), str(input_path)]
    elif kind == "erc":
        argv = [tool, "sch", "erc", "--format", "json", "--exit-code-violations"]
        argv += ["--severity-all"] if severity_all else ["--severity-error"]
        argv += ["-o", str(report_path), str(input_path)]
    else:
        argv = [tool, "sch", "export", "netlist", "--format", "kicadxml",
                "-o", str(report_path), str(input_path)]
    return argv


SYMBOL_RE = re.compile(r'\(symbol\s+\(lib_id\s+"')


def _count_symbols(path):
    """Count symbol instances in one schematic file, without trusting a report.

    A single regex, not two substrings: ``(symbol (lib_id "`` contains
    ``(symbol (lib_id`` and adding the two counts would double every symbol.
    """
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return 0
    return len(SYMBOL_RE.findall(text))


def _count_symbols_in_hierarchy(path):
    """Count symbols across the project's sheets, not just the root file.

    A hierarchical root sheet holds ``sheet`` instances and no symbols of its
    own, so counting only the file named on the command line reports zero for
    a perfectly populated design. Every ``*.kicad_sch`` beside the root is part
    of the same project; sheets they reference that live elsewhere are still
    covered by the ERC report's own sheet list, which is checked separately.
    """
    root = Path(path)
    total = 0
    try:
        siblings = sorted(root.parent.glob("*.kicad_sch"))
    except OSError:
        siblings = []
    for sheet in siblings:
        total += _count_symbols(sheet)
    if total == 0:
        total = _count_symbols(root)
    return total


def _count_pads(path):
    """Count board pads and footprints without trusting the report."""
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return 0, 0
    return text.count("(pad "), text.count("(footprint ")


def _parse_drc(text):
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("DRC report is not a JSON object")
    for key in REQUIRED_KEYS["drc"]:
        if key not in data:
            raise ValueError("DRC report is missing required key %r" % key)
    if not isinstance(data["violations"], list):
        raise ValueError("DRC violations is not a list")
    if not isinstance(data["unconnected_items"], list):
        raise ValueError("DRC unconnected_items is not a list")
    return data


def _parse_erc(text):
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("ERC report is not a JSON object")
    for key in REQUIRED_KEYS["erc"]:
        if key not in data:
            raise ValueError("ERC report is missing required key %r" % key)
    if not isinstance(data["sheets"], list):
        raise ValueError("ERC sheets is not a list")
    for sheet in data["sheets"]:
        if not isinstance(sheet, dict) or "violations" not in sheet:
            raise ValueError("ERC sheet entry has no violations list")
        if not isinstance(sheet["violations"], list):
            raise ValueError("ERC sheet violations is not a list")
    return data


def _parse_netlist(text):
    root = ET.fromstring(text)
    if root.tag != "export":
        raise ValueError("netlist root element is %r, expected 'export'" % root.tag)
    nets = root.find("nets")
    if nets is None:
        raise ValueError("netlist has no <nets> element")
    nodes = 0
    for net in nets.findall("net"):
        if net.get("name") is None:
            raise ValueError("netlist <net> without a name")
        for node in net.findall("node"):
            if not node.get("ref") or not node.get("pin"):
                raise ValueError("netlist node without ref/pin")
            nodes += 1
    return nodes


def grade(argv):
    args = build_parser().parse_args(argv)

    if args.min_objects < 1:
        raise UsageError("--min-objects must be at least 1 (zero objects is never a pass)")
    if args.timeout <= 0:
        raise UsageError("--timeout must be positive")

    input_path = Path(args.input)
    require_inputs(GATE, input=input_path)

    tool = shutil.which(args.kicad_cli) or (
        args.kicad_cli if os.path.isfile(args.kicad_cli) else None
    )
    if not tool:
        raise UsageError("kicad-cli not found: %s" % args.kicad_cli)
    if not os.access(tool, os.X_OK):
        raise UsageError("kicad-cli is not executable: %s" % tool)

    checks = Checks()
    try:
        run_dir = new_run_dir(args.outdir)
    except OSError as exc:
        raise UsageError("cannot create output directory under %s: %s" % (args.outdir, exc))

    report_path = run_dir / REPORT_NAMES[args.kind]
    argv_used = _command(args.kind, tool, input_path, report_path, args.severity_all)

    started = time.time()
    completed = True
    timed_out = False
    exit_code = None
    stdout_text = ""
    stderr_text = ""
    try:
        proc = subprocess.run(argv_used, capture_output=True, text=True,
                              timeout=args.timeout)
        exit_code = proc.returncode
        stdout_text = proc.stdout or ""
        stderr_text = proc.stderr or ""
    except subprocess.TimeoutExpired:
        completed = False
        timed_out = True
        exit_code = None
    except OSError as exc:
        completed = False
        exit_code = None
        stderr_text = str(exc)
    elapsed = round(time.time() - started, 3)

    checks.require("subprocess_completed", completed,
                   "timed out after %ss" % args.timeout if timed_out
                   else "" if completed else stderr_text)
    checks.require("subprocess_exit", completed and exit_code == 0,
                   "exit code %r (nonzero is a failure even with an empty "
                   "violation list)" % (exit_code,))

    report_exists = report_path.is_file()
    report_size = report_path.stat().st_size if report_exists else 0
    checks.require("report_present", report_exists and report_size > 0,
                   "expected fresh report at %s" % report_path)

    report_text = ""
    parse_error = ""
    if report_exists and report_size > 0:
        try:
            report_text = report_path.read_text()
        except OSError as exc:
            parse_error = "cannot read report: %s" % exc

    parsed = None
    if report_text:
        try:
            if args.kind == "drc":
                parsed = _parse_drc(report_text)
            elif args.kind == "erc":
                parsed = _parse_erc(report_text)
            else:
                parsed = _parse_netlist(report_text)
        except (json.JSONDecodeError, ET.ParseError, ValueError) as exc:
            parse_error = str(exc)

    checks.require("report_parseable", parsed is not None and not parse_error,
                   parse_error or "ok")

    violations = 0
    unconnected = 0
    sheets = 0
    structure_ok = False
    source_ok = True
    source_detail = ""

    if parsed is not None:
        structure_ok = True
        if args.kind == "drc":
            violations = len(parsed["violations"])
            unconnected = len(parsed["unconnected_items"])
            reported_source = os.path.basename(str(parsed.get("source", "")))
            source_ok = reported_source == input_path.name
            source_detail = ("report source %r vs input %r"
                             % (reported_source, input_path.name))
            checks.require("report_source_matches_input", source_ok, source_detail)
        elif args.kind == "erc":
            sheets = len(parsed["sheets"])
            violations = sum(len(sheet["violations"]) for sheet in parsed["sheets"])
    checks.require("report_structure", structure_ok, parse_error or "ok")

    # Objects actually graded. The report is never the source of truth here:
    # a zero-violation report over zero objects is a pass over nothing.
    if args.kind == "drc":
        pads, footprints = _count_pads(input_path)
        objects = pads
        object_detail = "%d pads in %d footprints" % (pads, footprints)
    elif args.kind == "erc":
        objects = _count_symbols_in_hierarchy(input_path)
        object_detail = "%d symbols across the project's sheets" % objects
    else:
        objects = parsed if parsed is not None else 0
        object_detail = "%d netlist nodes" % objects

    checks.require("objects_scanned", objects >= args.min_objects,
                   "%d graded objects, need >= %d (%s)"
                   % (objects, args.min_objects, object_detail))
    checks.require("no_violations", violations == 0,
                   "%d violation(s) reported" % violations)
    if args.kind == "erc":
        # A report that enumerates no sheet graded nothing, whatever the
        # schematic contains.
        checks.require("report_covers_sheets", sheets >= 1,
                       "%d sheet(s) covered by the ERC report" % sheets)
    if args.kind == "drc":
        checks.require("no_unconnected", unconnected == 0,
                       "%d unconnected item(s) reported" % unconnected)

    evidence = {
        "kind": args.kind,
        "command": argv_used,
        "input": str(input_path.resolve()),
        "input_sha256": sha256_file(input_path),
        "report_path": str(report_path),
        "report_sha256": sha256_file(report_path) if report_exists else None,
        "run_dir": str(run_dir),
        "exit_code": exit_code,
        "elapsed_s": elapsed,
        "violations": violations,
        "unconnected": unconnected,
        "sheets": sheets,
        "objects_scanned": objects,
        "stdout_tail": stdout_text[-400:],
    }
    if args.kind != "drc":
        evidence.pop("unconnected")

    human = []
    if parsed is None and parse_error:
        human.append("report could not be used: %s" % parse_error)
    if exit_code not in (None, 0):
        tail = (stderr_text or stdout_text).strip().splitlines()
        if tail:
            human.append("kicad-cli said: %s" % tail[-1][:300])
    if checks.failed():
        human.append("failed checks: %s" % ", ".join(checks.failed()))
    return finish(GATE, checks, evidence=evidence, human_lines=human)


def main(argv=None):
    return guard(GATE, grade, argv)


if __name__ == "__main__":
    sys.exit(main())
