#!/usr/bin/python3
"""Diagnose why GEN_INHA's two pads are in separate free-space regions.

The router reports "no path" for GEN_INHA (U1 pin 32 -> U17 pin 40). BFS agrees,
so it is not an algorithm fault. Flood fill from each pad showed the start reaches
1.48M cells while the goal pad is unreachable, i.e. two disconnected regions.

This finds WHICH obstacle separates them, by flooding both sides and locating the
narrowest gap between the two regions, then reporting what copper occupies it.

Uses bytearray visited maps rather than Python sets: a set of 1.5M (x,y) tuples is
gigabytes and took minutes; a bytearray is 2 MB and takes seconds.
"""
import sys
sys.path.insert(0, '.')
import math
from collections import deque

import pcbnew

import hand_route_interblock as H


def main():
    b = pcbnew.LoadBoard('powerboard-reva-routed.kicad_pcb')
    bb = b.GetBoardEdgesBoundingBox()
    g = H.Grid(b, pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
    n = g.w * g.h
    print("grid %d x %d = %d cells" % (g.w, g.h, n))

    fine = H.fine_pitch_bodies(b)
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T:
            g.block_segment(pcbnew.ToMM(t.GetStart().x),
                            pcbnew.ToMM(t.GetStart().y),
                            pcbnew.ToMM(t.GetEnd().x),
                            pcbnew.ToMM(t.GetEnd().y),
                            pcbnew.ToMM(t.GetWidth()))
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            pos = pad.GetPosition()
            x, y = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            c = H.ESCAPE_CLEARANCE if H.in_any(fine, x, y) else H.CLEARANCE_PAD
            g.block_pad(pad, clearance=c)

    pads = [pd for fp in b.GetFootprints() for pd in fp.Pads()
            if pd.GetNetname() == 'GEN_INHA']
    assert len(pads) == 2, pads

    cells = []
    for p in pads:
        pos = p.GetPosition()
        cx, cy = g.mm_to_cell(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
        sz = p.GetSize()
        pw, ph = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)
        c = H.ESCAPE_CLEARANCE if H.in_any(fine, pcbnew.ToMM(pos.x),
                                           pcbnew.ToMM(pos.y)) else H.CLEARANCE_PAD
        rcx = int(math.ceil((pw / 2 + c) / H.GRID))
        rcy = int(math.ceil((ph / 2 + c) / H.GRID))
        for dy in range(-rcy, rcy + 1):
            for dx in range(-rcx, rcx + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < g.w and 0 <= ny < g.h:
                    g.blocked[g.idx(nx, ny)] = 0
        cells.append((cx, cy))

    def flood(seed):
        seen = bytearray(n)
        seen[g.idx(*seed)] = 1
        q = deque([seed])
        while q:
            cur = q.popleft()
            cx, cy = cur
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < g.w and 0 <= ny < g.h):
                    continue
                i = g.idx(nx, ny)
                if not seen[i] and not g.blocked[i]:
                    seen[i] = 1
                    q.append((nx, ny))
        return seen

    A = flood(cells[0])
    C = flood(cells[1])
    print("region A (U1 pin 32): %d cells" % sum(A))
    print("region C (U17 pin 40): %d cells" % sum(C))
    overlap = sum(1 for i in range(n) if A[i] and C[i])
    print("overlap: %d  (0 means genuinely disconnected)" % overlap)

    # Dilate region C outward layer by layer; the first A cell reached is the
    # narrowest crossing, and the distance is the wall thickness.
    import array
    dist = array.array('i', [-1]) * 0  # placeholder, keep flake quiet
    del dist
    layer = [i for i in range(0)]
    prev = C
    step = 0
    hit = None
    while step < 400:
        step += 1
        nxt = bytearray(n)
        frontier = []
        for i in range(n):
            if not prev[i]:
                continue
            cx, cy = i % g.w, i // g.w
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < g.w and 0 <= ny < g.h):
                    continue
                j = g.idx(nx, ny)
                if nxt[j] or prev[j]:
                    continue
                nxt[j] = 1
                frontier.append(j)
                if A[j]:
                    hit = (j, step)
                    break
            if hit:
                break
        if hit:
            break
        prev = nxt

    if not hit:
        print("no crossing found within 400 cells")
        return 1
    j, step = hit
    x, y = (j % g.w) * H.GRID, (j // g.w) * H.GRID
    print("narrowest crossing: %d cells (%.2f mm) at %.2f,%.2f mm"
          % (step, step * H.GRID, x, y))

    # What copper is at that point?
    print("\ncopper within 1.2 mm of the crossing point:")
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            pos = pad.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            if abs(px - x) < 1.2 and abs(py - y) < 1.2:
                sz = pad.GetSize()
                print("  PAD %s-%s %-14s at %.2f,%.2f size %.2fx%.2f"
                      % (fp.GetReference(), pad.GetNumber(), pad.GetNetname(),
                         px, py, pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)))
    for t in b.GetTracks():
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        s, e = t.GetStart(), t.GetEnd()
        sx, sy = pcbnew.ToMM(s.x), pcbnew.ToMM(s.y)
        ex, ey = pcbnew.ToMM(e.x), pcbnew.ToMM(e.y)
        if (abs(sx - x) < 1.2 and abs(sy - y) < 1.2) or \
           (abs(ex - x) < 1.2 and abs(ey - y) < 1.2):
            print("  TRACK %-14s %.2f,%.2f -> %.2f,%.2f  w=%.2f"
                  % (t.GetNetname(), sx, sy, ex, ey,
                     pcbnew.ToMM(t.GetWidth())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
