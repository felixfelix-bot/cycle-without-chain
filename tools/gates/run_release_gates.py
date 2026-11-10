#!/usr/bin/env python3
"""Run the release gates the way a human actually would: one command.

This is the wiring TOOL-01 was missing. It does not reimplement any gate; it
decides *what this tree can grade*, invokes ``run_all_gates.py`` for the gates
that have real inputs, and reports the rest as ``NOT RUN`` with the reason.

Two modes, one code path:

* local (default) — any ``NOT RUN`` is a failure, exactly as the gate contract
  says. Use this before asking for a review.
* ``--ci`` — the workflow's mode. A gate that cannot run on the runner (no
  ``kicad-cli``, no board file, no release packet) is surfaced as ``NOT RUN``
  in the job summary and *does not* fail the job; every gate that did run must
  still pass. ``FAIL`` is never relaxed in either mode.

Why ``--ci`` exists at all: a workflow that installs KiCad to satisfy a gate it
never really exercises is worse than one that says "this gate did not run
here". The relaxation is one-directional and tested
(``test_ci_mode_never_turns_a_failure_green``).

Usage::

    python3 tools/gates/run_release_gates.py
    python3 tools/gates/run_release_gates.py --ci --summary-file "$GITHUB_STEP_SUMMARY"
    python3 tools/gates/run_release_gates.py --list

Exit: 0 PASS, 1 FAIL, 2 NOT RUN.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

PASS, FAIL, NOT_RUN = 0, 1, 2

RUNNER = HERE / "run_all_gates.py"

# Where the board artifacts live; the gate suite was written against these names.
BOARD_DIR = Path("hardware") / "powerboard-reva"
BOARD_FILE = BOARD_DIR / "powerboard-reva.kicad_pcb"
XML_NETLIST = BOARD_DIR / "exports" / "ctrl-supply.xml"
SEXPR_NETLIST = BOARD_DIR / "exports" / "powerboard-reva.net"
PIN_NET_MAP = BOARD_DIR / "pin-net-map.csv"
RELEASE_MANIFEST = Path("docs") / "release-manifest.json"
RELEASE_ARTIFACTS = Path("out") / "gerbers"

GATES = ("native_reports", "netlist_parity", "release_manifest")


class Planned:
    """One gate's invocation plan: either an argv or a reason it cannot run."""

    def __init__(self, gate, argv=None, reason="", evidence=None):
        self.gate = gate
        self.argv = argv
        self.reason = reason
        self.evidence = evidence or {}

    @property
    def runnable(self):
        return self.argv is not None


def _missing(repo_root, relative):
    return not (Path(repo_root) / relative).is_file()


def plan(repo_root, kicad_cli="kicad-cli", selected=()):
    """Decide, with reasons, which gates this tree can actually run.

    A gate is planned as NOT RUN when an input it cannot invent is absent, so
    the reason names the exact missing thing (board file, tool, manifest,
    packet) rather than a shrug.
    """
    repo_root = Path(repo_root)
    plans = []

    if not selected or "native_reports" in selected:
        if _missing(repo_root, BOARD_FILE):
            plans.append(Planned(
                "native_reports",
                reason="no board file: %s does not exist, so DRC has nothing to "
                       "grade (this design is schematic-only)" % BOARD_FILE))
        elif not _tool_available(kicad_cli):
            plans.append(Planned(
                "native_reports",
                reason="kicad-cli not available (%s); DRC needs the native tool "
                       "and will not be faked" % kicad_cli))
        else:
            outdir = Path(tempfile.mkdtemp(prefix="gate-native-"))
            plans.append(Planned(
                "native_reports",
                argv=["--native-kind", "drc",
                      "--native-input", str(repo_root / BOARD_FILE),
                      "--native-outdir", str(outdir),
                      "--kicad-cli", kicad_cli],
                evidence={"outdir": str(outdir)}))

    if not selected or "netlist_parity" in selected:
        missing_parts = [str(p) for p in (XML_NETLIST, SEXPR_NETLIST, PIN_NET_MAP)
                         if _missing(repo_root, p)]
        if missing_parts:
            plans.append(Planned(
                "netlist_parity",
                reason="missing connectivity input(s): %s" % ", ".join(missing_parts)))
        else:
            plans.append(Planned(
                "netlist_parity",
                argv=["--expected-from-pin-net-map", str(repo_root / PIN_NET_MAP),
                      "--netlist", str(repo_root / XML_NETLIST),
                      "--netlist-sexpr", str(repo_root / SEXPR_NETLIST)],
                evidence={"artifacts": ["xml", "sexpr"]}))

    if not selected or "release_manifest" in selected:
        if _missing(repo_root, RELEASE_MANIFEST):
            plans.append(Planned(
                "release_manifest",
                reason="no release manifest: %s does not exist, so there is no "
                       "artifact inventory to grade" % RELEASE_MANIFEST))
        elif not (repo_root / RELEASE_ARTIFACTS).is_dir():
            plans.append(Planned(
                "release_manifest",
                reason="no artifact packet: %s/ does not exist, so the manifest "
                       "cannot be checked against files" % RELEASE_ARTIFACTS))
        else:
            plans.append(Planned(
                "release_manifest",
                argv=["--manifest", str(repo_root / RELEASE_MANIFEST),
                      "--artifacts", str(repo_root / RELEASE_ARTIFACTS)]))

    return plans


def _tool_available(kicad_cli):
    if os.sep in str(kicad_cli):
        path = Path(kicad_cli)
        return path.is_file() and os.access(str(path), os.X_OK)
    return shutil.which(str(kicad_cli)) is not None


def _run_runner(argv, repo_root, timeout):
    command = [sys.executable, str(RUNNER), *[str(a) for a in argv]]
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(repo_root))
    proc = subprocess.run(command, cwd=str(repo_root), capture_output=True,
                          text=True, timeout=timeout, env=env)
    payload = None
    for line in reversed((proc.stdout or "").strip().splitlines()):
        try:
            payload = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    return proc, payload


def _verdict_of(gate, payload, returncode):
    if payload is None:
        return "NOT RUN", "runner produced no machine-readable result (exit %s)" % returncode
    result = (payload.get("results") or {}).get(gate) or {}
    verdict = result.get("verdict", payload.get("verdict", "NOT RUN"))
    if verdict == "PASS" and returncode != 0:
        return "FAIL", "runner reported PASS but exited %s" % returncode
    return verdict, result.get("reason", "")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="run_release_gates.py",
        description="Run the fail-closed release gates for this tree in one command.",
        allow_abbrev=False,
    )
    parser.add_argument("--gate", action="append", dest="gates", default=None,
                        choices=GATES, metavar="GATE",
                        help="run only this gate (repeatable; default: all)")
    parser.add_argument("--repo-root", dest="repo_root", default=str(REPO_ROOT),
                        help="tree to grade (default: this checkout)")
    parser.add_argument("--kicad-cli", dest="kicad_cli", default="kicad-cli",
                        help="kicad-cli executable used by native_reports")
    parser.add_argument("--ci", action="store_true",
                        help="workflow mode: NOT RUN is reported and does not "
                             "fail the job; FAIL still does")
    parser.add_argument("--summary-file", dest="summary_file", default=None,
                        help="write a markdown summary here (use "
                             "$GITHUB_STEP_SUMMARY in CI)")
    parser.add_argument("--json-out", dest="json_out", default=None,
                        help="write the aggregate payload to this file")
    parser.add_argument("--list", action="store_true", help="print the gate list")
    parser.add_argument("--timeout", type=float, default=1800.0,
                        help="per-runner timeout in seconds (default %(default)s)")
    args = parser.parse_args(argv)

    if args.list:
        print(json.dumps({"gates": list(GATES)}, sort_keys=True))
        return PASS

    repo_root = Path(args.repo_root).resolve()
    selected = tuple(args.gates or ())
    plans = plan(repo_root, kicad_cli=args.kicad_cli, selected=selected)

    results = {}
    runnable = [p for p in plans if p.runnable]
    for item in plans:
        if not item.runnable:
            results[item.gate] = {"gate": item.gate, "verdict": "NOT RUN",
                                  "reason": item.reason, "checks_passed": 0}
            print("%s: NOT RUN (%s)" % (item.gate, item.reason), file=sys.stderr)

    if runnable:
        # One runner invocation for every runnable gate: the runner already
        # aggregates and enforces the exit-code contract gate by gate.
        argv_list = []
        for item in runnable:
            argv_list.extend(["--gate", item.gate])
            argv_list.extend(item.argv)
        proc, payload = _run_runner(argv_list, repo_root, args.timeout)
        for item in runnable:
            verdict, reason = _verdict_of(item.gate, payload, proc.returncode)
            detail = ((payload or {}).get("results", {}).get(item.gate) or {})
            ok_checks = [c for c in detail.get("checks", []) if c.get("ok")]
            results[item.gate] = {
                "gate": item.gate,
                "verdict": verdict,
                "reason": reason,
                "checks_passed": len(ok_checks),
                "checks_failed": [c.get("name") for c in detail.get("checks", [])
                                  if not c.get("ok")],
            }
            print("%s: %s" % (item.gate, verdict), file=sys.stderr)

    failed = [gate for gate in GATES
              if results.get(gate, {}).get("verdict") == "FAIL"]
    not_run = [gate for gate in GATES
               if results.get(gate, {}).get("verdict") == "NOT RUN"]
    passed = [gate for gate in GATES
              if results.get(gate, {}).get("verdict") == "PASS"]

    if failed:
        verdict, exit_code = "FAIL", FAIL
    elif not_run and (not args.ci or not passed):
        # In CI, NOT RUN is tolerated only when *something* actually graded.
        # A run where every selected gate was skipped is not a green run.
        verdict, exit_code = "NOT RUN", NOT_RUN
    else:
        verdict, exit_code = "PASS", PASS

    payload = {
        "gate": "run_release_gates",
        "verdict": verdict,
        "exit_code": exit_code,
        "mode": "ci" if args.ci else "local",
        "selected": list(selected) or list(GATES),
        "repo_root": str(repo_root),
        "results": results,
        "failed": failed,
        "not_run": not_run,
    }
    print(json.dumps(payload, sort_keys=True))

    markdown = _summary_markdown(payload)
    if args.summary_file:
        with open(args.summary_file, "a", encoding="utf-8") as handle:
            handle.write(markdown)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return exit_code


def _summary_markdown(payload):
    """The job summary. NOT RUN rows always appear; there is no quiet mode."""
    lines = ["## Release gates — %s mode" % payload["mode"], "",
             "| gate | verdict | detail |", "|---|---|---|"]
    for gate in GATES:
        entry = payload["results"].get(gate)
        if entry is None:
            continue
        detail = entry.get("reason") or ""
        if not detail and entry["verdict"] == "PASS":
            detail = "%d checks passed" % entry.get("checks_passed", 0)
        if not detail and entry["verdict"] == "FAIL":
            detail = "failed checks: %s" % ", ".join(entry.get("checks_failed") or [])[:400]
        lines.append("| %s | %s | %s |"
                     % (gate, entry["verdict"], str(detail).replace("|", "\\|")))
    lines.append("")
    lines.append("**Aggregate: %s**" % payload["verdict"])
    if payload["not_run"]:
        lines.append("")
        lines.append("NOT RUN is not a pass: %s did not grade anything on this "
                     "run. The reason is in the table." % ", ".join(payload["not_run"]))
    lines.append("")
    lines.append("These gates check artifacts, not electrical safety, road "
                 "legality or manufacturability.")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
