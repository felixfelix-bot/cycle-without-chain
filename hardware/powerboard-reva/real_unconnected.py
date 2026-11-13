#!/usr/bin/python3
"""List the REAL unconnected pairs from a kicad-cli DRC report.

WHY
---
The DRC report's [unconnected_items] category mixes two different things:
  * genuine same-net disconnections  -- a net's copper does not reach its own pads
  * cross-net pairings                -- two pads on DIFFERENT nets listed together

Measured on this board: 308 pairs reported, 121 (39%) same-net. So 61% of the
category is not a connectivity statement at all, and the headline total (385) is not
a count of unconnected pins. This script separates them so the real work list is
visible.

Cross-net pairs are still worth keeping: they usually indicate a net whose copper
reaches NEITHER pad, so DRC pairs each orphaned pad with whatever else is nearby.

Usage: real_unconnected.py <drc.rpt> [netlist]
"""
import re
import sys
import collections


def parse(path):
    """Yield (netA, refA, padA, netB, refB, padB) for each unconnected item."""
    out = []
    pending = []
    for line in open(path):
        if line.startswith('[unconnected_items]'):
            pending = []
            continue
        m = re.search(r'Pad \S+ \[([^\]]+)\] of (\S+)', line)
        if not m:
            continue
        pending.append((m.group(1), m.group(2)))
        if len(pending) == 2:
            out.append((pending[0][0], pending[0][1],
                        pending[1][0], pending[1][1]))
            pending = []
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pairs = parse(sys.argv[1])
    same = [p for p in pairs if p[0] == p[2]]
    cross = [p for p in pairs if p[0] != p[2]]

    print("pairs reported:        %d" % len(pairs))
    print("same-net (REAL):       %d" % len(same))
    print("cross-net (not a connectivity statement): %d" % len(cross))

    print("\n--- real disconnected NETS (a net appears once per unjoined island) ---")
    nets = collections.Counter(p[0] for p in same)
    for n, c in nets.most_common():
        print("   %-20s %d pair(s)" % (n, c))
    print("\n   distinct real nets: %d" % len(nets))

    print("\n--- cross-net pairs, by the first net named ---")
    cn = collections.Counter(p[0] for p in cross)
    for n, c in cn.most_common(12):
        print("   %-20s %d" % (n, c))
    return 0


if __name__ == '__main__':
    sys.exit(main())
