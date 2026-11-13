#!/usr/bin/python3
"""Route U2's local decoupling nets, which the block pass missed.

WHY THESE
---------
`HUB_CPH`, `HUB_CPL`, `HUB_DVDD`, `HUB_VCP`, `HUB_VGLS` are five two-point nets
between the HUB DRV8353 (U2) and its local capacitors C11-C14. Measured spans:

    HUB_CPH    U2.2  -> C11.1    8.0 mm
    HUB_CPL    U2.1  -> C11.2    9.8 mm
    HUB_DVDD   U2.38 -> C14.1   14.4 mm
    HUB_VCP    U2.5  -> C12.1    5.5 mm
    HUB_VGLS   U2.40 -> C13.1    8.7 mm

Every one of these is a genuine miss, not a design exclusion: the reserved power
stage owns U2's GATE DRIVE outputs, but the charge-pump and VGLS decoupling caps sit
in the driver block itself and should have been joined.

Fifteen pads, five connections, all short. That is a maze-router problem the grid
tool can actually solve, unlike the QFN escape case.

HOW
---
Reuses the collision-checked machinery: build the obstacle grid from the board as it
stands, free only the two pads of the net being routed, A* between them, then insert
the track only if the resulting geometry survives the same clearance tests the
fan-out uses. No blind insertion -- that mistake has been made three times.
"""
import sys
sys.path.insert(0, '.')
import math

import pcbnew

import hand_route_interblock as H
import fanout_checked as FC

NETS = ["HUB_CPH", "HUB_CPL", "HUB_DVDD", "HUB_VCP", "HUB_VGLS"]
# 0.25 mm is a normal signal track and these are all short local runs inside a
# driver block; nothing here needs the pitched escape width.
WIDTH = 0.25


def vec(x_mm, y_mm):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'powerboard-reva-board.kicad_pcb'
    dst = sys.argv[2] if len(sys.argv) > 2 else 'routing/u2_local.kicad_pcb'
    board = pcbnew.LoadBoard(src)
    print("base: %s (%d copper items)" % (src, len(list(board.GetTracks()))))

    boxes = FC.existing_copper(board)
    fine = H.fine_pitch_bodies(board)
    print("obstacle boxes: %d  fine-pitch bodies: %d" % (len(boxes), len(fine)))

    # THE GRID MUST BE AS STRICT AS THE VERIFICATION, OR NOTHING EVER PASSES.
    #
    # First attempt: the grid blocked pads at CLEARANCE_PAD (0.10 mm) and tracks at
    # their own width, while the run test in fanout_checked.stub_clear demands
    # width/2 + CLEAR_ESCAPE against pads and width/2 + CLEAR_TRACK (0.20) against
    # other tracks. The grid was therefore MORE PERMISSIVE than the check, so every
    # path A* found was afterwards rejected: HUB_VCP reported "run blocked by
    # pad:HUB_GHA" and HUB_DVDD "blocked by pad:LOGIC3V3_EXT". Two failures that
    # look like geometry are actually two different clearance models disagreeing.
    #
    # So the obstacle map is now built with the same margins the test applies:
    # a cell is blocked if a WIDTH/2 track centred on it would violate.
    half = WIDTH / 2.0
    bb = board.GetBoardEdgesBoundingBox()
    grid = H.Grid(board, pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T:
            w = pcbnew.ToMM(t.GetWidth())
            grid.block_segment(pcbnew.ToMM(t.GetStart().x),
                               pcbnew.ToMM(t.GetStart().y),
                               pcbnew.ToMM(t.GetEnd().x),
                               pcbnew.ToMM(t.GetEnd().y),
                               w + 2.0 * (half + FC.CLEAR_TRACK))
        elif t.Type() == pcbnew.PCB_VIA_T:
            pos = t.GetPosition()
            w = pcbnew.ToMM(t.GetWidth())
            cx, cy = grid.mm_to_cell(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
            r = int(math.ceil((w / 2.0 + half + FC.CLEAR_TRACK) / H.GRID))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < grid.w and 0 <= ny < grid.h:
                        grid.blocked[grid.idx(nx, ny)] = 1
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            pos = pad.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            c = (FC.CLEAR_ESCAPE if H.in_any(fine, px, py)
                 else FC.CLEAR_TRACK)
            grid.block_pad(pad, clearance=half + c)
    static = bytearray(grid.blocked)

    done = []
    failed = []
    for net in NETS:
        pads = [p for fp in board.GetFootprints() for p in fp.Pads()
                if p.GetNetname() == net]
        if len(pads) < 2:
            failed.append((net, "only %d pads" % len(pads)))
            continue
        pts = []
        for p in pads:
            pos = p.GetPosition()
            pt = (pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
            pts.append(pt)

        # Free this net's own pads so A* can start and finish on them.
        g = H.Grid(board, pcbnew.ToMM(bb.GetWidth()),
                   pcbnew.ToMM(bb.GetHeight()))
        g.blocked = bytearray(static)
        for p, (px, py) in zip(pads, pts):
            sz = p.GetSize()
            pw, ph = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)
            # Free using the SAME margin the map blocked with, or the freed
            # region is smaller than the blocked one and nothing reopens.
            c = (FC.CLEAR_ESCAPE if H.in_any(fine, px, py)
                 else FC.CLEAR_TRACK)
            cx, cy = g.mm_to_cell(px, py)
            rcx = int(math.ceil((pw / 2 + half + c) / H.GRID))
            rcy = int(math.ceil((ph / 2 + half + c) / H.GRID))
            for dy in range(-rcy, rcy + 1):
                for dx in range(-rcx, rcx + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < g.w and 0 <= ny < g.h:
                        g.blocked[g.idx(nx, ny)] = 0

        a = g.mm_to_cell(*pts[0])
        c = g.mm_to_cell(*pts[1])
        path = g.astar(a, c)
        if not path:
            failed.append((net, "no path %.1f mm" % math.hypot(
                pts[0][0] - pts[1][0], pts[0][1] - pts[1][1])))
            continue

        # Walk the cell path into straight runs and test each against real copper.
        pts_mm = [(cx * H.GRID, cy * H.GRID) for cx, cy in path]
        runs = [pts_mm[0]]
        for i in range(1, len(pts_mm) - 1):
            ax, ay = pts_mm[i - 1]
            bx, by = pts_mm[i]
            dx2, dy2 = pts_mm[i + 1]
            if (bx - ax, by - ay) != (dx2 - bx, dy2 - by):
                runs.append(pts_mm[i])
        runs.append(pts_mm[-1])

        ok_all = True
        for i in range(len(runs) - 1):
            x0, y0 = runs[i]
            x1, y1 = runs[i + 1]
            ok, why = FC.stub_clear(boxes, net, x0, y0, x1, y1, WIDTH / 2.0,
                                    H.in_any(fine, x0, y0))
            if not ok:
                ok_all = False
                failed.append((net, "run blocked by %s:%s" % (why.kind, why.net)))
                break
        if not ok_all:
            continue

        for i in range(len(runs) - 1):
            x0, y0 = runs[i]
            x1, y1 = runs[i + 1]
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(x0, y0))
            t.SetEnd(vec(x1, y1))
            t.SetWidth(pcbnew.FromMM(WIDTH))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(pads[0].GetNet())
            board.Add(t)
        done.append((net, len(runs) - 1))

    print("\nrouted %d nets, failed %d" % (len(done), len(failed)))
    for net, n in done:
        print("   OK   %-10s %d segments" % (net, n))
    for net, why in failed:
        print("   FAIL %-10s %s" % (net, why))

    if done:
        pcbnew.SaveBoard(dst, board)
        print("\nwrote %s" % dst)
    return 0


if __name__ == '__main__':
    sys.exit(main())
