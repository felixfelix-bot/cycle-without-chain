#!/usr/bin/env python3
"""Read-only, fail-closed consistency check, NOT independent circuit qualification.

Expectations are the existing pin-net-map.csv and review-bom.csv. Never import
(or execute) the generator here: doing so would overwrite the evidence checked.
Exit zero means only that this deliberately incomplete milestone is consistent.
"""
import csv
import json
from pathlib import Path
import re
import sys

P = Path(__file__).resolve().parent
# Independent physical-pin contract, matching tests/test_mcu_connectivity.py.
UNUSED_MCU_PINS = {
    5, 7, 8, 9, 10, 11, 12, 13, 19, 30, 31,
    38, 47, 51, 52, 53, 54, 68, 69, 70, 71, 72, 73, 78, 79,
    80, 81, 82, 83, 85, 86, 87, 88, 89, 90, 91, 96, 97, 98,
}
EXPECTED_NC = {('U17', str(pin)) for pin in UNUSED_MCU_PINS}
EXPECTED_NC |= {(ref, str(pin)) for ref in ['U27', 'U29'] for pin in [5,6,8,9,11,12]}
# U500 PGOOD now wired to rail interlock


class VerificationError(ValueError):
    """An artifact is missing, malformed, or inconsistent."""


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def parse(text):
    """Parse one complete KiCad S-expression; reject unbalanced/trailing input."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[^\s()"]+|[()]|"', text)
    stack, roots = [], []
    for token in tokens:
        if token == '(':
            stack.append([])
        elif token == ')':
            require(bool(stack), 'unexpected closing parenthesis')
            item = stack.pop()
            require(bool(item), 'empty expression')
            (stack[-1] if stack else roots).append(item)
        else:
            require(bool(stack), 'atom outside expression')
            require(token != '"', 'unterminated string')
            stack[-1].append(json.loads(token) if token.startswith('"') else token)
    require(not stack and len(roots) == 1, 'expected one complete expression')
    return roots[0]


def children(node, key):
    return [x for x in node[1:] if isinstance(x, list) and x[0] == key]


def child(node, key):
    matches = children(node, key)
    require(len(matches) == 1, f'expected one {key}')
    return matches[0]


def value(node, key):
    field = child(node, key)
    require(len(field) == 2 and isinstance(field[1], str) and bool(field[1]), f'invalid {key}')
    return field[1]


def rows(path, fields, count):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream, strict=True)
        require(reader.fieldnames == fields, f'{path.name}: invalid columns')
        result = list(reader)
    require(len(result) == count, f'{path.name}: expected {count} rows')
    require(all(set(r) == set(fields) and all(r[f] is not None for f in fields) for r in result), 'invalid CSV row')
    return result


def verify(root=P):
    expected = {}
    for row in rows(root / 'pin-net-map.csv', ['ref', 'pin', 'pin_name', 'net', 'sheet'], 1171):
        key = (row['ref'], row['pin'])
        require(all(row.values()) and key not in expected, 'empty or duplicate expected endpoint')
        expected[key] = row['net']
    bom = {}
    for row in rows(root / 'review-bom.csv', ['reference', 'value', 'footprint', 'sheet'], 397):
        ref = row['reference']
        require(ref and row['value'] and row['sheet'] and ref not in bom, 'empty or duplicate expected part')
        bom[ref] = (row['value'], row['footprint'])
    require({ref for ref, pin in expected} == set(bom), 'manifest reference sets differ')
    net = parse((root / 'exports/powerboard-reva.net').read_text())
    require(net[0] == 'export', 'not a KiCad export')
    components = children(child(net, 'components'), 'comp')
    actual_bom = {}
    for comp in components:
        ref = value(comp, 'ref')
        require(ref not in actual_bom, f'duplicate component {ref}')
        footprints = children(comp, 'footprint')
        require(len(footprints) <= 1, 'duplicate footprint')
        footprint = value(comp, 'footprint') if footprints else ''
        actual_bom[ref] = (value(comp, 'value'), footprint)
    require(actual_bom == bom, 'component reference/value/footprint mismatch')
    require(sum(ref.startswith('Q') for ref in bom) == 29 and sum(ref.startswith('U') for ref in bom) == 38, 'expected 29 Q references and 35 U references')
    actual, names, codes, nc = {}, set(), set(), {}
    seen_endpoints = set()
    for entry in children(child(net, 'nets'), 'net'):
        name, code = value(entry, 'name'), value(entry, 'code')
        require(name not in names and code not in codes, 'duplicate net name/code')
        names.add(name)
        codes.add(code)
        nodes = children(entry, 'node')
        require(bool(nodes), f'empty net {name}')
        is_nc = name.startswith('unconnected-')
        if is_nc:
            require(len(nodes) == 1, 'NC net must be singleton')
        for node in nodes:
            key = (value(node, 'ref'), value(node, 'pin'))
            require(key not in seen_endpoints, f'duplicate endpoint {key}')
            seen_endpoints.add(key)
            if is_nc:
                require(key in EXPECTED_NC, f'unapproved NC endpoint {key}')
                require(name == f'unconnected-({key[0]}-{value(node, "pinfunction")}-Pad{key[1]})', 'invalid NC net name')
                require(value(node, 'pintype') == ('bidirectional+no_connect' if key[0]=='U17' else 'open_collector+no_connect' if key[0]=='U500' else 'passive+no_connect'), 'missing explicit NC type')
                nc[key] = name
            else:
                actual[key] = name
    require(set(nc) == EXPECTED_NC, 'explicit NC endpoint set mismatch')
    names -= set(nc.values())
    require(names == set(expected.values()) and len(names) == 226, 'net identity/count mismatch')
    schematic = parse((root / 'mcu-core.kicad_sch').read_text())
    require(schematic[0] == 'kicad_sch', 'invalid MCU schematic')
    markers = children(schematic, 'no_connect')
    require(len(markers) == len(UNUSED_MCU_PINS), 'explicit NC marker count mismatch')
    positions = [tuple(child(marker, 'at')[1:]) for marker in markers]
    require(len(set(positions)) == len(markers), 'duplicate NC marker position')
    require(actual == expected, 'endpoint set or net assignment mismatch')

    report = (root / 'exports/erc.rpt').read_text()
    require(report.startswith('ERC report (') and 'Report includes: Errors, Warnings' in report, 'invalid ERC report header')
    require(re.findall(r'\*\* ERC messages:.*', report) == ['** ERC messages: 0  Errors 0  Warnings 0'], 'invalid ERC totals')

    # ERC is required to be EMPTY. This is stricter than the previous form, which
    # pinned the exact set of ten known undriven-supply errors as an accepted
    # state. Those ten were resolved by attaching PWR_FLAGs to the nets whose
    # power genuinely originates off-symbol (connector, passive link, buck SW
    # pin, FET source node); each flag was justified individually in
    # docs/design/erc-power-flags.md.
    #
    # The guard's original purpose — that an expected issue class cannot silently
    # disappear — is preserved and strengthened: now NO issue class may appear at
    # all. Any new ERC finding, of any kind, fails this check.
    # Count severity markers rather than parsing issue-block structure. A chunk
    # split on "^\[" depends on the report's exact formatting: an injected issue
    # whose "[" is not the first character of a line slips straight through
    # (found by mutation test). Every issue KiCad emits carries a "; error" or
    # "; warning" line, so counting those is formatting-independent and catches
    # a well-formed issue body even when the totals line still reads 0/0.
    severities = re.findall(r'(?m)^\s*;\s*(error|warning)\b', report)
    require(severities == [],
            'ERC report contains %d issue(s): %r' % (len(severities), severities[:8]))

    # The PWR_FLAGs are real schematic symbols, so confirm they exist and are
    # non-physical (#FLG refs must not enter the BOM). A flag that vanished would
    # bring the undriven errors back, so its presence is asserted.
    # Ten nets, ten flags: DC_LINK, CTRL_RAW, CTRL3V3, DRIVE12, MCU_VDDA,
    # MCU_VREF, MAIN_SOURCE, PRE_SOURCE, LOGIC3V3_EXT, PGND.
    flags = sorted(set(re.findall(r'#FLG\d{3}', ''.join(
        p.read_text() for p in root.glob('*.kicad_sch')))))
    require(len(flags) == 10,
            'expected exactly 10 PWR_FLAG symbols (one per undriven net), found %d'
            % len(flags))
    # `bom` here is a sequence of reference strings, not rows.
    require(all(not str(r).startswith('#') for r in bom),
            'non-physical # reference leaked into the BOM')

    return {'components': len(bom), 'nets': len(names), 'verified_pin_assignments': len(actual),
            'explicit_nc_endpoints': len(nc),
            'mosfets': 29, 'drivers': 4, 'erc_errors': 0, 'erc_warnings': 0,
            'pwr_flags': len(flags),
            'erc_reason': 'ERC clean: 0 errors, 0 warnings. Ten former undriven-supply '
                          'issues resolved by justified PWR_FLAGs, not waived.',
            'status': 'PARTIAL_NOT_SAFE_TO_ENERGIZE',
            'svg_pages': len(list((root / 'exports/svg').glob('*.svg')))}


def main():
    try:
        summary = verify()
    except (OSError, ValueError, csv.Error) as exc:
        print(f'Export verification FAILED: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
