#!/usr/bin/env python3
"""Run the quality gates and return a single nonzero status if any gate fails.

Each gate is invoked as a subprocess so a crash, a hang or a ``sys.exit`` inside
one gate cannot affect the others, and so the aggregate status reflects the
gates' own exit codes rather than any in-process state.

Statuses are collapsed deliberately:

    0  every selected gate returned PASS
    1  at least one gate returned FAIL or NOT RUN (both are nonzero)

A gate that could not run at all is *not* silently dropped: it is recorded as
``NOT RUN`` and counted as a failure, because "we did not check" and "we
checked and it was fine" must not look the same to a caller.

Usage::

    python3 tools/gates/run_all_gates.py --list
    python3 tools/gates/run_all_gates.py \\
        --gate native_reports --native-kind drc \\
        --native-input hardware/powerboard-reva/board.kicad_pcb \\
        --native-outdir /tmp/gates --kicad-cli kicad-cli \\
        --gate netlist_parity --netlist out.xml --expected expected.json \\
        --gate release_manifest --manifest manifest.json --artifacts out/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

GATES = ("native_reports", "netlist_parity", "release_manifest")

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

PASS = 0
FAIL = 1
NOT_RUN = 2


def _build_argparser():
    parser = argparse.ArgumentParser(
        prog="run_all_gates.py",
        description="Run the fail-closed quality gates and aggregate the verdict.",
        allow_abbrev=False,
    )
    parser.add_argument("--gate", action="append", dest="gates", metavar="GATE",
                        help="gate to run (repeatable; default: all). One of: %s"
                             % ", ".join(GATES))
    parser.add_argument("--skip", action="append", dest="skips", metavar="GATE",
                        default=None,
                        help="gate to leave out even if selected (repeatable)")
    parser.add_argument("--list", action="store_true",
                        help="print the gate list and exit")
    parser.add_argument("--timeout", type=float, default=1800.0,
                        help="per-gate timeout in seconds (default %(default)s)")
    parser.add_argument("--json-out", dest="json_out", default=None,
                        help="also write the aggregate payload to this file")

    native = parser.add_argument_group("native_reports")
    native.add_argument("--native-kind", dest="native_kind", choices=("drc", "erc", "netlist"))
    native.add_argument("--native-input", dest="native_input")
    native.add_argument("--native-outdir", dest="native_outdir")
    native.add_argument("--kicad-cli", dest="kicad_cli")

    parity = parser.add_argument_group("netlist_parity")
    parity.add_argument("--netlist")
    parity.add_argument("--netlist-sexpr", dest="netlist_sexpr", default=None,
                        help="also grade this S-expression netlist against the "
                             "same expected map and require both to agree")
    parity.add_argument("--expected")
    parity.add_argument("--expected-from-pin-net-map", dest="pin_net_map", default=None,
                        metavar="CSV",
                        help="derive the expected map from pin-net-map.csv")
    parity.add_argument("--require-net", action="append", dest="require_nets")

    manifest = parser.add_argument_group("release_manifest")
    manifest.add_argument("--manifest")
    manifest.add_argument("--artifacts")
    return parser


class RunnerUsageError(Exception):
    """The runner itself was invoked with an unusable command line."""


def _emit(payload):
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stdout.flush()


def _gate_argv(gate, args):
    if gate == "native_reports":
        required = (args.native_kind, args.native_input, args.native_outdir, args.kicad_cli)
        if any(value is None for value in required):
            return None, "needs --native-kind, --native-input, --native-outdir and --kicad-cli"
        return [
            "-m", "tools.gates.native_reports",
            "--kind", args.native_kind,
            "--input", args.native_input,
            "--outdir", args.native_outdir,
            "--kicad-cli", args.kicad_cli,
        ], ""
    if gate == "netlist_parity":
        if args.netlist is None:
            return None, "needs --netlist"
        if args.expected is None and args.pin_net_map is None:
            return None, "needs --expected or --expected-from-pin-net-map"
        argv = ["-m", "tools.gates.netlist_parity", "--netlist", args.netlist]
        if args.expected is not None:
            argv.extend(["--expected", args.expected])
        if args.pin_net_map is not None:
            argv.extend(["--expected-from-pin-net-map", args.pin_net_map])
        if args.netlist_sexpr is not None:
            argv.extend(["--netlist-sexpr", args.netlist_sexpr])
        for name in args.require_nets or ():
            argv.extend(["--require-net", name])
        return argv, ""
    if gate == "release_manifest":
        if args.manifest is None or args.artifacts is None:
            return None, "needs --manifest and --artifacts"
        return ["-m", "tools.gates.release_manifest",
                "--manifest", args.manifest, "--artifacts", args.artifacts], ""
    raise AssertionError("unknown gate %r" % gate)  # unreachable via argparse


def _run_gate(gate, args):
    module_argv, problem = _gate_argv(gate, args)
    if module_argv is None:
        return {
            "gate": gate,
            "verdict": "NOT RUN",
            "exit_code": None,
            "reason": problem,
        }
    command = [sys.executable, *module_argv]
    started = time.time()
    try:
        proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True,
                              text=True, timeout=args.timeout)
        elapsed = round(time.time() - started, 3)
        payload = None
        text = (proc.stdout or "").strip()
        if text:
            try:
                payload = json.loads(text.splitlines()[-1])
            except json.JSONDecodeError:
                payload = None
        if payload is None:
            return {
                "gate": gate,
                "verdict": "NOT RUN",
                "exit_code": proc.returncode,
                "reason": "gate produced no machine-readable result",
                "stderr_tail": (proc.stderr or "")[-800:],
                "elapsed_s": elapsed,
            }
        payload["elapsed_s"] = elapsed
        payload["stderr_tail"] = (proc.stderr or "")[-800:]
        # Trust the exit code, not the self-reported verdict, if they disagree:
        # a gate that printed PASS and exited 1 is a failure.
        if proc.returncode != 0 and payload.get("verdict") == "PASS":
            payload["verdict"] = "FAIL"
            payload["reason"] = "self-reported PASS with nonzero exit code %d" % proc.returncode
        return payload
    except subprocess.TimeoutExpired:
        return {
            "gate": gate,
            "verdict": "NOT RUN",
            "exit_code": None,
            "reason": "gate exceeded the %ss timeout" % args.timeout,
        }


def main(argv=None):
    parser = _build_argparser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse rejects an unknown gate/flag this way
        code = int(exc.code or 0)
        if code != 0:
            _emit({"gate": "run_all_gates", "verdict": "NOT RUN",
                   "reason": "unusable command line (see stderr)",
                   "gates": list(GATES), "failed": [], "results": {}})
        return code

    if args.list:
        _emit({"gates": list(GATES), "verdict": "PASS", "selected": list(GATES)})
        return 0

    if not args.gates:
        # Running "all gates" is only meaningful once the caller has said where
        # the artifacts live; guessing would produce three NOT RUNs and hide a
        # configuration mistake behind a FAIL.
        _emit({"gate": "run_all_gates", "verdict": "NOT RUN",
               "reason": "no --gate selected; pass --gate at least once",
               "gates": list(GATES), "failed": [], "results": {}})
        print("run_all_gates: NOT RUN: no --gate selected", file=sys.stderr)
        return NOT_RUN

    explicit = args.gates
    unknown = [gate for gate in explicit if gate not in GATES]
    skips = args.skips or []
    unknown += [gate for gate in skips if gate not in GATES]
    if unknown:
        _emit({"gate": "run_all_gates", "verdict": "NOT RUN",
               "reason": "unknown gate(s): %s (known: %s)"
                         % (", ".join(unknown), ", ".join(GATES)),
               "gates": list(GATES), "failed": [], "results": {}})
        print("run_all_gates: NOT RUN: unknown gate(s): %s" % ", ".join(unknown),
              file=sys.stderr)
        return NOT_RUN

    selected = [gate for gate in GATES if gate in explicit and gate not in skips]
    if not selected:
        _emit({"gate": "run_all_gates", "verdict": "NOT RUN",
               "reason": "no gates selected", "gates": [], "failed": [], "results": {}})
        print("run_all_gates: NOT RUN: no gates selected", file=sys.stderr)
        return NOT_RUN

    results = {}
    wiring = {}
    for gate in selected:
        module_argv, problem = _gate_argv(gate, args)
        wiring[gate] = problem
        if module_argv is None:
            results[gate] = {"gate": gate, "verdict": "NOT RUN", "exit_code": None,
                             "reason": problem}
            print("%s: NOT RUN (%s)" % (gate, problem), file=sys.stderr)
            continue
        result = _run_gate(gate, args)
        results[gate] = result
        print("%s: %s" % (gate, result.get("verdict", "NOT RUN")), file=sys.stderr)

    unwired = sorted(gate for gate, problem in wiring.items() if problem)
    if unwired:
        # Nothing was graded for these gates: report a NOT RUN aggregate rather
        # than a FAIL, so "you did not configure it" stays distinguishable from
        # "it ran and the artifact failed".
        payload = {
            "gate": "run_all_gates",
            "verdict": "NOT RUN",
            "exit_code": NOT_RUN,
            "reason": "incomplete runner wiring: %s"
                      % "; ".join("%s %s" % (gate, wiring[gate]) for gate in unwired),
            "selected": selected,
            "unwired": unwired,
            "failed": [],
            "results": results,
        }
        _emit(payload)
        if args.json_out:
            Path(args.json_out).write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return NOT_RUN

    failed = [gate for gate in selected
              if results[gate].get("verdict") != "PASS"
              or results[gate].get("exit_code") != 0]
    verdict = "PASS" if not failed else "FAIL"
    payload = {
        "gate": "run_all_gates",
        "verdict": verdict,
        "exit_code": PASS if verdict == "PASS" else FAIL,
        "selected": selected,
        "failed": failed,
        "results": results,
    }
    _emit(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
