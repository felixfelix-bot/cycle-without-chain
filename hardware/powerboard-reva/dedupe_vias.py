#!/usr/bin/python3
"""Drop vias that two routing passes placed at the same coordinates.

WHY THIS IS NEEDED
------------------
The route-first ordering fix means two passes now contribute copper to the same
board: the inter-block pass, then the block pass around it. Where both needed a
via at the same point they each placed one, 0.0001 mm apart. DRC reports 199
`holes_co_located` warnings, all same-net, all on the 27 inter-block nets.

Electrically this is harmless -- two vias on one net at one location conduct the
same as one -- but it is 199 fabricated holes that serve no purpose, and it
would be dishonest to report "2 unconnected" while shipping a board with 199
spurious drills.

WHAT THIS DOES AND DOES NOT DO
------------------------------
It removes a via ONLY when another via on the SAME net sits within `--tol` mm of
it. Different nets at the same coordinates would be a short, and this script
refuses to touch those -- it reports them and leaves them for a human.

Usage: /usr/bin/python3 dedupe_vias.py <in.kicad_pcb> <out.kicad_pcb> [--tol 0.02]
"""
from __future__ import annotations

import argparse
import sys

import pcbnew


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--tol", type=float, default=0.02,
                    help="mm; two vias closer than this on one net are duplicates")
    args = ap.parse_args()

    board = pcbnew.LoadBoard(args.src)
    if board is None:
        print("FATAL: could not load", args.src)
        return 1

    vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    print("vias before: %d" % len(vias))

    tol_nm = int(args.tol * 1e6)
    kept: list = []
    removed = 0
    conflicts = []
    for v in vias:
        pos = v.GetPosition()
        net = v.GetNetname()
        dup = None
        for k in kept:
            if k.GetNetname() != net:
                continue
            kp = k.GetPosition()
            if abs(kp.x - pos.x) <= tol_nm and abs(kp.y - pos.y) <= tol_nm:
                dup = k
                break
        if dup is not None:
            board.Remove(v)
            removed += 1
            continue
        # Flag (but do not touch) a via that collides with a DIFFERENT net: that
        # is a short, not a duplicate, and removing one side would hide it.
        for k in kept:
            if k.GetNetname() == net:
                continue
            kp = k.GetPosition()
            if abs(kp.x - pos.x) <= tol_nm and abs(kp.y - pos.y) <= tol_nm:
                conflicts.append((net, k.GetNetname(), pos.x / 1e6, pos.y / 1e6))
        kept.append(v)

    pcbnew.SaveBoard(args.dst, board)
    print("vias after:  %d  (removed %d same-net duplicates)" % (len(kept), removed))
    if conflicts:
        print()
        print("REFUSED: %d via pair(s) sit on DIFFERENT nets. These are shorts and"
              % len(conflicts))
        print("are left untouched deliberately:")
        for net, other, x, y in conflicts[:10]:
            print("  %s vs %s at %.3f,%.3f" % (net, other, x, y))
    else:
        print("no cross-net coincident vias")
    return 0


if __name__ == "__main__":
    sys.exit(main())
