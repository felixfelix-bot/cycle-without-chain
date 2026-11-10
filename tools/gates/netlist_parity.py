"""Exact schematic-to-netlist parity: KiCad XML netlist vs an expected map.

Set semantics, not counts
-------------------------
A connectivity swap can keep the endpoint count identical, so this gate never
compares totals. It builds the normalized set of ``(reference, pin, net)``
triples on both sides and reports the exact missing and extra rows, any pin
that appears on two nets (a short) and any duplicate row inside one net.

Expected-map formats accepted (same data, two spellings)::

    {"nets": {"VIN": [["J1", "1"], ["C1", "1"]], "GND": [["J1", "2"]]},
     "nc":   [["U1", "3"]]}

    {"endpoints": [["J1", "1", "VIN"], ["C1", "1", "VIN"], ["J1", "2", "GND"]],
     "nc":        [["U1", "3"]]}

A net declared with an empty row list must still exist in the netlist; that
catches a net that silently vanished while all its endpoints moved elsewhere.

``nc`` is optional and lists pins that must *not* appear on any real net.
KiCad emits ``unconnected-(REF-PadN)`` nets for such pins; those nets are
ignored by default (``--include-unconnected`` opts back in) because no
expected map can enumerate auto-generated names.

Exit codes: 0 PASS, 1 FAIL (diffs found), 2 NOT RUN (bad invocation, missing
or unparsable input, malformed or self-contradictory expected map).
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from ._common import (
    Checks,
    StrictParser,
    UsageError,
    finish,
    guard,
    require_inputs,
    sha256_file,
)

GATE = "netlist_parity"

UNCONNECTED_PREFIX = "unconnected-"


class ExpectationError(UsageError):
    """The expected map itself is malformed: the gate cannot grade."""


class NetlistStructureError(ValueError):
    """The XML parsed but is not a netlist in the shape KiCad emits."""


def build_parser():
    parser = StrictParser(
        prog="python3 -m tools.gates.netlist_parity",
        description="Compare a KiCad XML netlist against an expected "
                    "reference/pin/net map with exact set semantics.",
    )
    parser.add_argument("--netlist", required=True, help="KiCad XML netlist")
    parser.add_argument("--expected", required=True, help="expected endpoint map (JSON)")
    parser.add_argument("--require-net", action="append", default=None,
                        dest="require_nets", metavar="NAME",
                        help="fail unless this net exists (repeatable)")
    parser.add_argument("--include-unconnected", action="store_true",
                        dest="include_unconnected",
                        help="also compare KiCad's auto-generated "
                             "'unconnected-*' nets (off by default)")
    parser.add_argument("--allow-empty", action="store_true", dest="allow_empty",
                        help="permit a zero-endpoint comparison (default: never)")
    return parser


def load_netlist(path, include_unconnected=False):
    """Parse a KiCad XML netlist into comparable structures.

    Returns a dict with ``endpoints`` (list of (ref, pin, net)), ``nets``
    (compared net names), ``unconnected_nets``, ``nc_pins`` (pins seen only on
    auto-generated unconnected nets), ``duplicates`` and ``shorts``.
    """
    root = ET.parse(str(path)).getroot()
    if root.tag != "export":
        raise NetlistStructureError(
            "netlist root element is %r, expected 'export'" % root.tag)
    nets_element = root.find("nets")
    if nets_element is None:
        raise NetlistStructureError("netlist has no <nets> element")

    endpoints = []
    nets = []
    unconnected_nets = []
    nc_pins = set()
    duplicates = []
    seen_ref_pin = {}

    for net in nets_element.findall("net"):
        name = net.get("name")
        if not name:
            raise NetlistStructureError("netlist <net> element without a name attribute")
        is_unconnected = name.startswith(UNCONNECTED_PREFIX)
        if is_unconnected:
            unconnected_nets.append(name)
        compared = include_unconnected or not is_unconnected
        if compared:
            nets.append(name)

        local = set()
        for node in net.findall("node"):
            ref, pin = node.get("ref"), node.get("pin")
            if not ref or not pin:
                raise NetlistStructureError(
                    "netlist <node> without ref/pin in net %r" % name)
            key = (ref, pin)
            if is_unconnected:
                nc_pins.add(key)
            if not compared:
                continue
            if key in local:
                duplicates.append({"ref": ref, "pin": pin, "net": name,
                                   "reason": "duplicate row inside one net"})
                continue
            local.add(key)
            endpoints.append((ref, pin, name))
            seen_ref_pin.setdefault(key, []).append(name)

    if not nets and not unconnected_nets:
        raise NetlistStructureError("netlist declares no nets")

    shorts = []
    for (ref, pin), where in sorted(seen_ref_pin.items()):
        if len(where) > 1:
            finding = {"ref": ref, "pin": pin, "nets": sorted(where),
                       "reason": "pin appears on more than one net"}
            duplicates.append(finding)
            shorts.append(finding)

    return {
        "endpoints": endpoints,
        "nets": nets,
        "unconnected_nets": unconnected_nets,
        "nc_pins": nc_pins,
        "duplicates": duplicates,
        "shorts": shorts,
    }


def load_expected(path):
    """Return (endpoints, declared_nets, nc_pins) from an expected map."""
    try:
        data = json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise ExpectationError("expected map is not valid JSON: %s" % exc)
    if not isinstance(data, dict):
        raise ExpectationError("expected map must be a JSON object")

    endpoints = []
    net_names = []
    if "nets" in data:
        nets = data["nets"]
        if not isinstance(nets, dict) or not nets:
            raise ExpectationError("expected map 'nets' must be a non-empty object")
        for name, rows in nets.items():
            if not isinstance(rows, list):
                raise ExpectationError("net %r must map to a list of [ref, pin]" % name)
            net_names.append(str(name))
            for row in rows:
                if not isinstance(row, (list, tuple)) or len(row) != 2:
                    raise ExpectationError(
                        "net %r row %r is not a [ref, pin] pair" % (name, row))
                endpoints.append((str(row[0]), str(row[1]), str(name)))
    elif "endpoints" in data:
        rows = data["endpoints"]
        if not isinstance(rows, list) or not rows:
            raise ExpectationError("expected map 'endpoints' must be a non-empty list")
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                raise ExpectationError(
                    "endpoint row %r is not a [ref, pin, net] triple" % (row,))
            endpoints.append((str(row[0]), str(row[1]), str(row[2])))
            net_names.append(str(row[2]))
    else:
        raise ExpectationError("expected map needs a 'nets' or 'endpoints' key")

    seen = set()
    for row in endpoints:
        if row in seen:
            raise ExpectationError(
                "duplicate endpoint in expected map: %s pin %s on net %s" % row)
        seen.add(row)

    nc_rows = data.get("nc", [])
    if not isinstance(nc_rows, list):
        raise ExpectationError("expected map 'nc' must be a list of [ref, pin]")
    nc_pins = []
    for row in nc_rows:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            raise ExpectationError("nc row %r is not a [ref, pin] pair" % (row,))
        nc_pins.append((str(row[0]), str(row[1])))

    connected = {(ref, pin) for ref, pin, _ in endpoints}
    overlap = sorted(pin for pin in nc_pins if pin in connected)
    if overlap:
        raise ExpectationError(
            "expected map lists %s as both connected and NC" % (overlap,))

    return endpoints, sorted(set(net_names)), nc_pins


def grade(argv):
    args = build_parser().parse_args(argv)
    require_inputs(GATE, netlist=args.netlist, expected=args.expected)

    expected, expected_nets, expected_nc = load_expected(args.expected)

    checks = Checks()
    parsed = None
    parse_error = ""
    structure_error = ""
    try:
        parsed = load_netlist(args.netlist, args.include_unconnected)
    except ET.ParseError as exc:
        parse_error = "netlist is not well-formed XML: %s" % exc
    except NetlistStructureError as exc:
        structure_error = str(exc)
    except (OSError, ValueError) as exc:
        parse_error = str(exc)

    checks.require("netlist_parseable", not parse_error, parse_error or "ok")
    checks.require("netlist_structure", not structure_error and parsed is not None,
                   structure_error or "ok")

    if parsed is None:
        endpoints = []
        duplicates = []
        actual_nets = []
        missing = sorted(expected)
        extra = []
    else:
        endpoints = parsed["endpoints"]
        duplicates = parsed["duplicates"]
        actual = set(endpoints)
        wanted = set(expected)
        actual_nets = sorted(set(parsed["nets"]))
        wanted_nets = sorted(set(expected_nets))

        missing = sorted(wanted - actual)
        extra = sorted(actual - wanted)

        checks.require("duplicate_free", not duplicates,
                       "%d duplicate/short endpoint(s)" % len(duplicates))
        checks.require("non_empty", bool(endpoints) or args.allow_empty,
                       "%d endpoint(s) in netlist" % len(endpoints))
        checks.require("endpoints_match", not missing and not extra,
                       "%d missing, %d extra" % (len(missing), len(extra)))
        checks.require("nets_match", actual_nets == wanted_nets,
                       "missing nets %s, unexpected nets %s"
                       % (sorted(set(wanted_nets) - set(actual_nets)),
                          sorted(set(actual_nets) - set(wanted_nets))))
        for name in args.require_nets or ():
            checks.require("net_present:%s" % name, name in actual_nets,
                           "required net %r absent" % name)

    nc_violations = []
    if parsed is not None and expected_nc:
        connected_pairs = {(ref, pin) for ref, pin, _net in endpoints}
        nc_violations = sorted(pin for pin in expected_nc if pin in connected_pairs)
        checks.require("nc_respected", not nc_violations,
                       "NC pin(s) found on a real net: %s" % (nc_violations,))

    wanted_nets = sorted(set(expected_nets))
    evidence = {
        "netlist": str(Path(args.netlist).resolve()),
        "netlist_sha256": sha256_file(args.netlist),
        "expected": str(Path(args.expected).resolve()),
        "expected_sha256": sha256_file(args.expected),
        "endpoints": len(endpoints),
        "expected_endpoints": len(expected),
        "nets": len(actual_nets),
        "expected_nets": len(wanted_nets),
        "duplicate_endpoints": len(duplicates),
        "duplicates": duplicates[:20],
        "nc_expected": len(expected_nc),
        "nc_violations": nc_violations,
        "unconnected_nets_ignored": len(parsed["unconnected_nets"]) if parsed else 0,
    }
    diffs = {
        "missing": [{"ref": r, "pin": p, "net": n} for r, p, n in missing[:100]],
        "extra": [{"ref": r, "pin": p, "net": n} for r, p, n in extra[:100]],
        "nets_missing": sorted(set(wanted_nets) - set(actual_nets)),
        "nets_extra": sorted(set(actual_nets) - set(wanted_nets)),
        "missing_truncated": len(missing) > 100,
        "extra_truncated": len(extra) > 100,
    }

    human = []
    if parse_error:
        human.append("netlist unusable: %s" % parse_error)
    if structure_error:
        human.append("netlist structure: %s" % structure_error)
    for dup in duplicates[:10]:
        if "nets" in dup:
            human.append("SHORT: %s pin %s appears on %s"
                         % (dup["ref"], dup["pin"], ", ".join(dup["nets"])))
        else:
            human.append("DUPLICATE: %s pin %s twice in net %s"
                         % (dup["ref"], dup["pin"], dup["net"]))
    for row in diffs["missing"][:10]:
        human.append("missing: %s pin %s should be on net %s"
                     % (row["ref"], row["pin"], row["net"]))
    for row in diffs["extra"][:10]:
        human.append("extra:   %s pin %s is on net %s"
                     % (row["ref"], row["pin"], row["net"]))
    if diffs["nets_missing"]:
        human.append("declared in the expectation but absent from the netlist: %s"
                     % ", ".join(diffs["nets_missing"][:20]))
    if diffs["nets_extra"]:
        human.append("present in the netlist but not declared: %s"
                     % ", ".join(diffs["nets_extra"][:20]))
    for ref, pin in nc_violations[:10]:
        human.append("NC VIOLATION: %s pin %s is connected" % (ref, pin))

    return finish(GATE, checks, evidence=evidence,
                  extras={"diffs": diffs}, human_lines=human)


def main(argv=None):
    return guard(GATE, grade, argv)


if __name__ == "__main__":
    sys.exit(main())
