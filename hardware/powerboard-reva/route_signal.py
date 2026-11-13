#!/usr/bin/python3
"""Route one named signal net across the board: stub -> via -> B.Cu -> via -> stub.

Handles N pads via a nearest-neighbour spanning tree, so a net that fans out to more
than two points is connected with (N-1) paths rather than pretending to be a pair.

Built for HUB_nSCS, the last genuinely open net after the cross-net/cross-net split
showed 11 of 12 remaining nets were design-excluded power stages:

    U2.30  at  10.94,107.66   (hub driver)
    R23.1  at   8.80,120.33   (series resistor)
    U17.45 at 133.67, 20.43   (MCU, far side of the board)

Everything is checked before insertion, because blind insertion produced shorts three
times in this project: searched via sites (outside the pad, clear of foreign copper on
every pierced layer, hole spacing >= 0.25 mm), a B.Cu-only A* for the long run, and a
layer-aware verification pass.

Usage: route_signal.py <net> [base.kicad_pcb] [out.kicad_pcb]
"""
import sys
sys.path.insert(0, '.')
import math

import pcbnew

import hand_route_interblock as H
import fanout_checked as FC
from route_u2_escape import (foreign_copper, via_site_ok, hole_ok, stub_ok,
                             vec, VIA_DRILL, VIA_SIZE, VIA_STEP, STUB_MAX,
                             HOLE_CLEAR, STUB_W)

TRACE_W = 0.25


def find_site(board, copper, net, px, py, dirs, pad_half):
    """First legal via site walking outward from the pad, past the pad's own extent."""
    start = max(1, int((pad_half + VIA_STEP) / VIA_STEP))
    for step in range(start, int(STUB_MAX / VIA_STEP) + 1):
        dist = VIA_STEP * step
        for (dx, dy) in dirs:
            x = px + dx * dist
            y = py + dy * dist
            if not via_site_ok(copper, x, y)[0]:
                continue
            if not hole_ok(board, net, x, y)[0]:
                continue
            if not stub_ok(copper, net, px, py, x, y)[0]:
                continue
            return (x, y, dist)
    return None


def bcu_grid(board, W, Hh, half_trace):
    """Obstacle grid for B.Cu: B.Cu tracks, all vias, THT pads."""
    g = H.Grid(board, W, Hh)
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() == pcbnew.B_Cu:
            g.block_segment(pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y),
                            pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y),
                            pcbnew.ToMM(t.GetWidth()) + 2.0 * (half_trace + FC.CLEAR_TRACK))
        elif t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            cx, cy = g.mm_to_cell(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
            r = int(math.ceil((pcbnew.ToMM(t.GetWidth()) / 2.0 + half_trace
                               + FC.CLEAR_TRACK) / H.GRID))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < g.w and 0 <= ny < g.h:
                        g.blocked[g.idx(nx, ny)] = 1
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                g.block_pad(pad, clearance=half_trace + FC.CLEAR_TRACK)
    return g


def runs_from(path):
    """Collapse a cell path into straight runs, in mm."""
    pts = [(cx * H.GRID, cy * H.GRID) for cx, cy in path]
    runs = [pts[0]]
    for i in range(1, len(pts) - 1):
        ax, ay = pts[i - 1]
        bx, by = pts[i]
        dx2, dy2 = pts[i + 1]
        if (bx - ax, by - ay) != (dx2 - bx, dy2 - by):
            runs.append(pts[i])
    runs.append(pts[-1])
    return runs


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    net = sys.argv[1]
    src = sys.argv[2] if len(sys.argv) > 2 else 'powerboard-reva-board.kicad_pcb'
    dst = sys.argv[3] if len(sys.argv) > 3 else 'routing/signal.kicad_pcb'

    board = pcbnew.LoadBoard(src)
    print("base: %s (%d copper items)" % (src, len(list(board.GetTracks()))))
    print("net: %s" % net)

    pads = [(fp.GetReference(), p.GetNumber(), p)
            for fp in board.GetFootprints() for p in fp.Pads()
            if p.GetNetname() == net]
    if len(pads) < 2:
        print("FAIL: %d pads on %s" % (len(pads), net))
        return 1
    print("pads: %s" % ", ".join("%s.%s" % (r, n) for r, n, _ in pads))

    bb = board.GetBoardEdgesBoundingBox()
    W = pcbnew.ToMM(bb.GetWidth())
    Hh = pcbnew.ToMM(bb.GetHeight())
    half = TRACE_W / 2.0

    # 1. A legal via site for every pad, computed against the live board.
    sites = {}
    for (ref, num, pad) in pads:
        pos = pad.GetPosition()
        px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
        sz = pad.GetSize()
        pad_half = max(pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)) / 2.0
        copper = foreign_copper(board, net)
        # THE STUB MUST LEAVE ALONG THE PAD'S OWN AXIS.
        #
        # U17 is LQFP-100 on 0.5 mm pitch: pin 45 at 133.67,20.43 has pins 44 and 46
        # at exactly 0.500 mm, up and down the row. Walking outward in ANY direction
        # tries to squeeze a 0.6 mm via between 0.5 mm-pitch neighbours, which is the
        # closed contradiction found earlier (via must be <= 0.45 to clear, >= 0.5 to
        # be fabricable). The escape that works leaves perpendicular to the row,
        # along the pad's long axis, where the neighbours are not.
        long_is_y = pcbnew.ToMM(sz.y) >= pcbnew.ToMM(sz.x)
        dirs = [(0, 1), (0, -1)] if long_is_y else [(1, 0), (-1, 0)]
        site = find_site(board, copper, net, px, py, dirs, pad_half)
        if site is None:
            print("FAIL: %s.%s no legal via site within %.1f mm"
                  % (ref, num, STUB_MAX))
            return 1
        sites[num] = (px, py) + site
        print("   %s.%s pad %.2f,%.2f -> via %.2f,%.2f (stub %.2f mm)"
              % (ref, num, px, py, site[0], site[1], site[2]))

    # 2. Nearest-neighbour spanning tree over the pads.
    keys = [n for _, n, _ in pads]
    tree = [keys[0]]
    rest = keys[1:]
    pairs = []
    while rest:
        best = None
        for a in tree:
            ax, ay = sites[a][2], sites[a][3]
            for b in rest:
                bx, by = sites[b][2], sites[b][3]
                d = (bx - ax) ** 2 + (by - ay) ** 2
                if best is None or d < best[0]:
                    best = (d, a, b)
        _, a, b = best
        pairs.append((a, b))
        tree.append(b)
        rest.remove(b)
    print("spanning tree: %s" % " ".join("%s->%s" % p for p in pairs))

    # 3. Route each pair on B.Cu, one at a time, against the live board.
    netobj = pads[0][2].GetNet()
    done_pads = set()
    for (a, b) in pairs:
        grid = bcu_grid(board, W, Hh, half)
        for key in (a, b):
            vx, vy = sites[key][2], sites[key][3]
            cx, cy = grid.mm_to_cell(vx, vy)
            rr = int(math.ceil((VIA_SIZE / 2.0 + half) / H.GRID))
            for dy in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < grid.w and 0 <= ny < grid.h:
                        grid.blocked[grid.idx(nx, ny)] = 0
        start = grid.mm_to_cell(sites[a][2], sites[a][3])
        goal = grid.mm_to_cell(sites[b][2], sites[b][3])
        path = grid.astar(start, goal)
        if not path:
            print("FAIL: no B.Cu path %s -> %s" % (a, b))
            return 1
        runs = runs_from(path)
        runs[0] = (sites[a][2], sites[a][3])
        runs[-1] = (sites[b][2], sites[b][3])

        # Insert stubs + vias for this pair (once per pad, guarded below).
        for key in (a, b):
            if key in done_pads:
                continue
            px, py, vx, vy, _d = sites[key]
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(px, py))
            t.SetEnd(vec(vx, vy))
            t.SetWidth(pcbnew.FromMM(STUB_W))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(netobj)
            board.Add(t)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(vec(vx, vy))
            v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetWidth(pcbnew.FromMM(VIA_SIZE))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(netobj)
            board.Add(v)
            done_pads.add(key)
        for i in range(len(runs) - 1):
            x0, y0 = runs[i]
            x1, y1 = runs[i + 1]
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(x0, y0))
            t.SetEnd(vec(x1, y1))
            t.SetWidth(pcbnew.FromMM(TRACE_W))
            t.SetLayer(pcbnew.B_Cu)
            t.SetNet(netobj)
            board.Add(t)
        print("   %s -> %s: %d B.Cu segments" % (a, b, len(runs) - 1))

    pcbnew.SaveBoard(dst, board)
    print("wrote %s" % dst)
    return 0


if __name__ == '__main__':
    sys.exit(main())
