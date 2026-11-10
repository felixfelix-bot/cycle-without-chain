"""Read the S-expression netlist KiCad writes (`sch export netlist`).

The XML export (`--format kicadxml`) and this file are two serialisations of
the same netlist, and until RAIL-12 nothing compared them. This module is a
deliberately small, dependency-free reader for exactly the subset of the format
that matters here:

    (export ... (nets (net (code "1") (name "VIN") (class "Default")
                           (node (ref "R1") (pin "1") (pintype "passive"))) ...))

It returns the same shape as ``netlist_parity.load_netlist`` so both artifacts
are graded by one comparison: ``endpoints``, ``nets``, ``unconnected_nets``,
``nc_pins``, ``duplicates`` and ``shorts``.

It is duplicated from ``hardware/powerboard-reva/verify_exports.py`` on purpose.
That checker is the artifact under test for parity purposes; a gate that
imported it would inherit its bugs and would also stop being a second opinion.
"""

from __future__ import annotations

import json
import re

UNCONNECTED_PREFIX = "unconnected-"

TOKEN_RE = re.compile(r'"(?:\\.|[^"\\])*"|[^\s()"]+|[()]|"')


class SexprParseError(ValueError):
    """The text is not one complete S-expression (truncated or unbalanced)."""


class SexprStructureError(ValueError):
    """The text parsed but is not a netlist in the shape KiCad emits."""


def parse(text):
    """Parse exactly one complete S-expression; reject trailing/unbalanced input."""
    tokens = TOKEN_RE.findall(text)
    stack, roots = [], []
    for token in tokens:
        if token == "(":
            stack.append([])
        elif token == ")":
            if not stack:
                raise SexprParseError("unexpected closing parenthesis")
            item = stack.pop()
            if not item:
                raise SexprParseError("empty expression")
            (stack[-1] if stack else roots).append(item)
        else:
            if not stack:
                raise SexprParseError("atom outside any expression")
            if token == '"':
                raise SexprParseError("unterminated string")
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    if stack:
        raise SexprParseError("%d unclosed expression(s) — truncated file?" % len(stack))
    if len(roots) != 1:
        raise SexprParseError("expected exactly one top-level expression, got %d"
                              % len(roots))
    return roots[0]


def children(node, key):
    return [item for item in node[1:] if isinstance(item, list) and item and item[0] == key]


def child(node, key):
    matches = children(node, key)
    if not matches:
        raise SexprStructureError("no %r field" % key)
    return matches[0]


def value(node, key):
    field = child(node, key)
    if len(field) != 2 or not isinstance(field[1], str) or not field[1]:
        raise SexprStructureError("invalid %r field: %r" % (key, field))
    return field[1]


def load(path, include_unconnected=False):
    """Return the same comparison structure as the XML reader."""
    with open(path, "r", encoding="utf-8", errors="strict") as handle:
        text = handle.read()
    root = parse(text)
    if not root or root[0] != "export":
        raise SexprStructureError(
            "netlist root element is %r, expected 'export'" % (root[0] if root else None))
    nets_elements = children(root, "nets")
    if not nets_elements:
        raise SexprStructureError("netlist has no (nets ...) element")

    endpoints, nets, unconnected_nets = [], [], []
    nc_pins = set()
    duplicates = []
    seen_ref_pin = {}

    for net_element in children(nets_elements[0], "net"):
        name = value(net_element, "name")
        is_unconnected = name.startswith(UNCONNECTED_PREFIX)
        if is_unconnected:
            unconnected_nets.append(name)
        compared = include_unconnected or not is_unconnected
        if compared:
            nets.append(name)

        local = set()
        for node in children(net_element, "node"):
            ref, pin = value(node, "ref"), value(node, "pin")
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
        raise SexprStructureError("netlist declares no nets")

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
