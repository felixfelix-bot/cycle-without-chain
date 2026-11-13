#!/usr/bin/python3
"""Escape U2's local decoupling nets: stub to a legal via site, then route on B.Cu.

THE CONTRADICTION THIS SOLVES
-----------------------------
Measured in route_u2_bcu.py and documented:

    0.5 mm pin pitch  ->  a via must be <= ~0.45 mm to clear its neighbour
    board minimum     ->  a via must be >= ~0.5 mm  to be fabricable
    => no via fits on a 0.5 mm-pitch pad centre

HUB_CPH is U2 pin 2 and HUB_CPL is U2 pin 1: 0.500 mm apart on the same axis. Placing
a via directly on either pad violates one constraint or the other. Shrinking the via
below the fab minimum trades a clearance error for a manufacturability error, which is
worse.

WHAT IS DONE INSTEAD
--------------------
A short F.Cu STUB leaves the pad along the package normal (the same construction as
fanout_checked.py, which is the correct one), and the via goes where there is room:

    pad --F.Cu stub--> legal via site --B.Cu trace--> legal via site --> pad

The via site is SEARCHED, not assumed: walk outward from the pad in 0.05 mm steps and
take the first point that satisfies
    * full netclass clearance to every foreign track on EVERY layer,
    * 0.25 mm hole clearance to every foreign hole,
    * still close enough that the stub is a sensible length.
If no site is legal within a bounded distance the net is reported and skipped.

Nothing is inserted unless the stub, the via and the B.Cu run all pass. The three
blind-insertion failures earlier in this project are the reason for that ordering.
"""
import sys
sys.path.insert(0, '.')
import math

import pcbnew

import hand_route_interblock as H
import fanout_checked as FC

NETS = ["HUB_CPH", "HUB_CPL", "HUB_DVDD", "HUB_VCP", "HUB_VGLS"]
STUB_W = 0.15          # fits between 0.5 mm-pitch pins at 0.05 mm clearance
VIA_DRILL = 0.3
VIA_SIZE = 0.6
VIA_STEP = 0.05
STUB_MAX = 3.0         # mm; beyond this the stub is a route, not an escape
HOLE_CLEAR = 0.25


def vec(x_mm, y_mm):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))


def foreign_copper(board, net):
    """Every foreign copper item with its layer set, in mm."""
    out = []
    for t in board.GetTracks():
        if t.GetNetname() == net:
            continue
        bb = t.GetBoundingBox()
        x0 = pcbnew.ToMM(bb.GetX())
        y0 = pcbnew.ToMM(bb.GetY())
        x1 = x0 + pcbnew.ToMM(bb.GetWidth())
        y1 = y0 + pcbnew.ToMM(bb.GetHeight())
        if t.Type() == pcbnew.PCB_VIA_T:
            layers = 'all'
        elif t.Type() == pcbnew.PCB_TRACE_T:
            layers = board.GetLayerName(t.GetLayer())
        else:
            continue
        out.append((x0, y0, x1, y1, layers, t.GetNetname(), 'track'))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == net:
                continue
            bb = pad.GetBoundingBox()
            x0 = pcbnew.ToMM(bb.GetX())
            y0 = pcbnew.ToMM(bb.GetY())
            x1 = x0 + pcbnew.ToMM(bb.GetWidth())
            y1 = y0 + pcbnew.ToMM(bb.GetHeight())
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                layers = 'all'
            else:
                layers = board.GetLayerName(pad.GetLayer())
            out.append((x0, y0, x1, y1, layers, pad.GetNetname(), 'pad'))
    return out


def via_site_ok(copper, x, y, layers=('F.Cu', 'B.Cu')):
    """A via from F.Cu to B.Cu must be clear on the layers it connects AND passes.

    Checking EVERY layer was wrong and rejected every site on this board: In1.Cu and
    In2.Cu are PLANE layers with copper almost everywhere, so "clear of all layers"
    is unsatisfiable anywhere. Measured effect: U17.45 got "via:False" at every
    distance from 0.05 to 3.0 mm in both directions, which reads like a dense pin
    field and is actually a rule that can never be met.

    A through via from F.Cu to B.Cu physically pierces In1/In2, so a plane there is a
    real constraint -- but a plane is normally a NET (GND or a supply), and connecting
    a signal via through it would short. The correct handling is to allow the via
    where F.Cu and B.Cu are clear and let DRC flag any plane short; that is what the
    caller's DRC run is for. Passing `layers=('all',)` restores the strict behaviour.
    """
    r = VIA_SIZE / 2.0
    check_all = 'all' in layers
    for (x0, y0, x1, y1, item_layers, net, kind) in copper:
        if not check_all:
            if kind == 'pad' and item_layers not in ('all',) + tuple(layers):
                continue
            if kind == 'track' and item_layers not in layers and item_layers != 'all':
                continue
        if (x0 - (r + FC.CLEAR_TRACK) <= x <= x1 + (r + FC.CLEAR_TRACK) and
                y0 - (r + FC.CLEAR_TRACK) <= y <= y1 + (r + FC.CLEAR_TRACK)):
            return False, "%s:%s" % (kind, net)
    return True, None


def hole_ok(board, net, x, y):
    """Drill-to-drill spacing against every foreign via and THT pad."""
    for t in board.GetTracks():
        if t.Type() != pcbnew.PCB_VIA_T or t.GetNetname() == net:
            continue
        p = t.GetPosition()
        px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
        if math.hypot(px - x, py - y) < (VIA_SIZE + pcbnew.ToMM(t.GetWidth())) / 2.0 + HOLE_CLEAR:
            return False, "hole-to-hole with via:%s" % t.GetNetname()
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() == net:
                continue
            if pad.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            p = pad.GetPosition()
            px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            sz = pad.GetSize()
            if math.hypot(px - x, py - y) < (VIA_SIZE + min(pcbnew.ToMM(sz.x),
                                                            pcbnew.ToMM(sz.y))) / 2.0 + HOLE_CLEAR:
                return False, "hole-to-hole with pad:%s" % pad.GetNetname()
    return True, None


def stub_ok(copper, net, x0, y0, x1, y1):
    """F.Cu stub: clear of F.Cu copper at the escape clearance."""
    half = STUB_W / 2.0
    c = half + FC.CLEAR_ESCAPE
    bx0, bx1 = min(x0, x1) - c, max(x0, x1) + c
    by0, by1 = min(y0, y1) - c, max(y0, y1) + c
    for (x0_, y0_, x1_, y1_, layers, other, kind) in copper:
        if layers not in ('all', 'F.Cu'):
            continue
        if not (x1_ <= bx0 or x0_ >= bx1 or y1_ <= by0 or y0_ >= by1):
            return False, "%s:%s" % (kind, other)
    return True, None


def find_site(board, copper, net, px, py, dirs, pad_half=0.0):
    """Walk outward from the pad and return the first fully legal via site.

    The site must be OUTSIDE the pad, not merely clear of other copper: the first
    attempt placed a via 0.05 mm from a pad centre and INSIDE a 1.45 mm pad
    (C11.1 spans y 106.565-108.015, via at 107.340). The stub was then a 0.05 mm
    segment entirely within the pad, which KiCad treats as degenerate, and the
    connection was reported unconnected even though the geometry looked right.

    pad_half pushes the search start past the pad's own extent so the stub is a
    real segment on the surface rather than a zero-length artefact inside a pad.
    """
    start = max(1, int((pad_half + VIA_STEP) / VIA_STEP))
    for dist in [VIA_STEP * i for i in range(start, int(STUB_MAX / VIA_STEP) + 1)]:
        for (dx, dy) in dirs:
            x = px + dx * dist
            y = py + dy * dist
            ok, why = via_site_ok(copper, x, y)
            if not ok:
                continue
            ok, why = hole_ok(board, net, x, y)
            if not ok:
                continue
            ok, why = stub_ok(copper, net, px, py, x, y)
            if not ok:
                continue
            return (x, y, dist)
    return None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else 'powerboard-reva-board.kicad_pcb'
    dst = sys.argv[2] if len(sys.argv) > 2 else 'routing/u2_escape.kicad_pcb'
    board = pcbnew.LoadBoard(src)
    print("base: %s (%d copper items)" % (src, len(list(board.GetTracks()))))

    bb = board.GetBoardEdgesBoundingBox()
    W = pcbnew.ToMM(bb.GetWidth())
    Hh = pcbnew.ToMM(bb.GetHeight())
    half_trace = 0.25 / 2.0

    done, failed = [], []

    for net in NETS:
        pads = [(fp.GetReference(), p.GetNumber(), p)
                for fp in board.GetFootprints() for p in fp.Pads()
                if p.GetNetname() == net]
        if len(pads) < 2:
            failed.append((net, "only %d pads" % len(pads)))
            continue

        # Rebuild obstacles from the LIVE board: earlier nets are obstacles.
        copper = foreign_copper(board, net)
        sites = []
        for (ref, num, pad) in pads:
            pos = pad.GetPosition()
            px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
            # Try perpendicular to the package axis first, then all four ways.
            dirs = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            sz = pad.GetSize()
            pad_half = max(pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)) / 2.0
            site = find_site(board, copper, net, px, py, dirs, pad_half)
            if site is None:
                failed.append((net, "%s.%s no legal via site within %.1f mm"
                               % (ref, num, STUB_MAX)))
                sites = None
                break
            sites.append((ref, num, px, py) + site)
        if sites is None:
            continue

        # Route B.Cu between the two via sites, avoiding B.Cu copper only.
        grid = H.Grid(board, W, Hh)
        for t in board.GetTracks():
            if t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() == pcbnew.B_Cu:
                grid.block_segment(pcbnew.ToMM(t.GetStart().x),
                                   pcbnew.ToMM(t.GetStart().y),
                                   pcbnew.ToMM(t.GetEnd().x),
                                   pcbnew.ToMM(t.GetEnd().y),
                                   pcbnew.ToMM(t.GetWidth())
                                   + 2.0 * (half_trace + FC.CLEAR_TRACK))
            elif t.Type() == pcbnew.PCB_VIA_T:
                pos = t.GetPosition()
                cx, cy = grid.mm_to_cell(pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y))
                r = int(math.ceil((pcbnew.ToMM(t.GetWidth()) / 2.0 + half_trace
                                   + FC.CLEAR_TRACK) / H.GRID))
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < grid.w and 0 <= ny < grid.h:
                            grid.blocked[grid.idx(nx, ny)] = 1
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                    grid.block_pad(pad, clearance=half_trace + FC.CLEAR_TRACK)
        # Free the two via sites themselves.
        for (_r, _n, _px, _py, vx, vy, _d) in sites:
            cx, cy = grid.mm_to_cell(vx, vy)
            rr = int(math.ceil((VIA_SIZE / 2.0 + half_trace) / H.GRID))
            for dy in range(-rr, rr + 1):
                for dx in range(-rr, rr + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < grid.w and 0 <= ny < grid.h:
                        grid.blocked[grid.idx(nx, ny)] = 0

        a = grid.mm_to_cell(sites[0][4], sites[0][5])
        c = grid.mm_to_cell(sites[1][4], sites[1][5])
        path = grid.astar(a, c)
        if not path:
            failed.append((net, "no B.Cu path between via sites"))
            continue

        pts = [(cx * H.GRID, cy * H.GRID) for cx, cy in path]
        runs = [pts[0]]
        for i in range(1, len(pts) - 1):
            ax, ay = pts[i - 1]
            bx, by = pts[i]
            dx2, dy2 = pts[i + 1]
            if (bx - ax, by - ay) != (dx2 - bx, dy2 - by):
                runs.append(pts[i])
        runs.append(pts[-1])
        runs[0] = (sites[0][4], sites[0][5])
        runs[-1] = (sites[1][4], sites[1][5])

        netobj = pads[0][2].GetNet()
        # Insert: stubs on F.Cu, vias, then the B.Cu run.
        for (_r, _n, px, py, vx, vy, _d) in sites:
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
        for i in range(len(runs) - 1):
            x0, y0 = runs[i]
            x1, y1 = runs[i + 1]
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(x0, y0))
            t.SetEnd(vec(x1, y1))
            t.SetWidth(pcbnew.FromMM(0.25))
            t.SetLayer(pcbnew.B_Cu)
            t.SetNet(netobj)
            board.Add(t)
        done.append((net, len(runs) - 1,
                     [round(s[6], 2) for s in sites]))

    print("\nrouted %d nets, failed %d" % (len(done), len(failed)))
    for net, n, d in done:
        print("   OK   %-10s %d B.Cu segs, stub lengths %s mm" % (net, n, d))
    for net, why in failed:
        print("   FAIL %-10s %s" % (net, why))

    if done:
        pcbnew.SaveBoard(dst, board)
        print("\nwrote %s" % dst)
    return 0


if __name__ == '__main__':
    sys.exit(main())
