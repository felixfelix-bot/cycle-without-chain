#!/usr/bin/python3
"""Audit whether each escape net's copper actually touches both of its pads.

Written because kicad-cli DRC reported HUB_CPH as unconnected IN PAIR WITH PRE_VDDM
-- a pad on a different net. A pad cannot be "unconnected to" a pad it shares no net
with, so the DRC pairing is not evidence about connectivity. This checks the actual
question: does copper reach each pad?

A pad counts as reached when a segment of its own net enters the pad rectangle, or a
via of its own net sits on the pad centre. Nothing cleverer is needed.
"""
import sys
import math

import pcbnew

NETS = ['HUB_CPH', 'HUB_CPL', 'HUB_VCP', 'HUB_VGLS', 'HUB_DVDD']


def audit(path):
    board = pcbnew.LoadBoard(path)
    print("== %s  (%d items)" % (path, len(list(board.GetTracks()))))
    for net in NETS:
        pads = []
        for fp in board.GetFootprints():
            for p in fp.Pads():
                if p.GetNetname() == net:
                    pads.append((p.GetPosition(), p.GetSize()))
        if not pads:
            print("   %-9s (no pads on this board)" % net)
            continue
        segs = []
        for t in board.GetTracks():
            if t.GetNetname() != net:
                continue
            if t.Type() == pcbnew.PCB_VIA_T:
                pp = t.GetPosition()
                segs.append(('via', pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y),
                             None, None))
            else:
                s, e = t.GetStart(), t.GetEnd()
                segs.append(('seg', pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                             pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)))
        reached = []
        for (pos, sz) in pads:
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            hw = pcbnew.ToMM(sz.x) / 2.0
            hh = pcbnew.ToMM(sz.y) / 2.0
            hit = False
            for s in segs:
                if s[0] == 'via':
                    if math.hypot(s[1] - px, s[2] - py) < 0.01:
                        hit = True
                        break
                else:
                    x0, y0, x1, y1 = s[1], s[2], s[3], s[4]
                    # segment enters the pad rectangle?
                    for tt in [i / 20.0 for i in range(21)]:
                        xx = x0 + (x1 - x0) * tt
                        yy = y0 + (y1 - y0) * tt
                        if abs(xx - px) <= hw and abs(yy - py) <= hh:
                            hit = True
                            break
                    if hit:
                        break
            reached.append(hit)
        print("   %-9s %d pads, copper reaches: %s"
              % (net, len(pads), reached))
    return 0


if __name__ == '__main__':
    for p in sys.argv[1:]:
        audit(p)
