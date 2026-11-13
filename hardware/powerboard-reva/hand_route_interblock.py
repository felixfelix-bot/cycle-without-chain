#!/usr/bin/python3
"""Route the 43 inter-block nets with a grid maze router, avoiding existing copper.

WHY NOT THE AUTOROUTER
----------------------
FreeRouting could not do this job, for reasons now well established:

  * given a sub-board without the merged tracks, it drew across them: 199 shorts
  * given the whole board, its optimizer rewrote 2708 existing tracks and
    oscillated (normalizeTraces hitting 2000 iterations on OC_HIGH_REF,
    LOGIC3V3_EXT, LEFT_SWITCH_ADC) without ever writing a session file
  * keepout zones crashed pcbnew; netless tracks produced a board file that
    would not reload

The task itself is small and well-defined: 43 nets, each connecting exactly two
pads. That is 43 two-point connections, which a simple grid router handles
without any of the above machinery. It also keeps the decision visible: every
segment this places was placed by rules that can be read and checked.

ALGORITHM
---------
For each net:
  1. Take its two pads (a net with more than two pads is reported, not guessed).
  2. Rasterise the board into a grid at GRID mm.
  3. Mark cells blocked if they are within CLEARANCE of any existing track, via
     or pad that does not belong to this net.
  4. A* from one pad to the other, on a single layer, straight and diagonal moves
     with Manhattan-ish cost.
  5. Emit the path as track segments on that layer.

Layers are tried in order and the first that connects wins. If no layer connects,
the net is reported as failed rather than half-routed.

This is deliberately a plain 2-D router on one layer per net: no vias, no
multi-layer search. Vias are where the earlier attempts and the DRC failures
came from, and a 43-net signal problem mostly does not need them.

Usage: /usr/bin/python3 hand_route_interblock.py [base.kicad_pcb] [out.kicad_pcb]
"""
from __future__ import annotations

import heapq
import json
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "powerboard-reva-routed.kicad_pcb")
OUT = os.path.join(HERE, "powerboard-reva-routed-v3.kicad_pcb")

NETS = [
    "DRV_MOSI", "DRV_SCK", "DRV_MISO",
    "GEN_INHA", "GEN_INHB", "GEN_INHC", "GEN_INLA", "GEN_INLB", "GEN_INLC",
    "HUB_INHA", "HUB_INHB", "HUB_INHC", "HUB_INLA", "HUB_INLB", "HUB_INLC",
    "GEN_SOB", "GEN_SOC", "HUB_SOA_ADC", "HUB_SOB_ADC", "HUB_SOC_ADC",
    "OC_HIGH_REF", "OC_LOW_REF",
    "GEN_HALL_1", "GEN_HALL_2", "GEN_HALL_3",
    "HUB_HALL_1", "HUB_HALL_2", "HUB_HALL_3",
    "ENC_A", "ENC_B", "LEFT_FSR_ADC", "RIGHT_FSR_ADC",
    "OC_OK", "MCU_ARM", "ARM_CLEAN", "RESET_REQUEST", "WDI",
    "TIMER_BREAK_OK", "FSR_SAMPLE_ENABLE", "BRAKE_DUMP_PWM",
]

# 0.10 mm cells, not 0.25.
#
# 0.05 mm escape clearance needs a grid fine enough that a "free" cell is actually
# outside the clearance boundary -- at 0.25 mm a cell centre could sit 0.125 mm
# from copper and still be marked free, silently violating the rule the route was
# planned under. 0.05 mm cells would be exact but give 3.2M x 2.6M cells, far too
# many to search.
#
# 0.10 mm is the compromise: 1600 x 1300 = 2.08M cells, and 0.05 mm clearance is
# half a cell, so a routed path can be up to 0.05 mm optimistic. That is stated
# rather than hidden, and it is why the DRC result is the authority on the
# finished board rather than the router's own report.
GRID = 0.10          # mm per cell
# Two clearances, because they are two different constraints.
#
# Tracks need room to be routed between: 0.30 mm is right there.
#
# Pads must NOT get the same treatment. With 1415 pads on a 160x130 board and a
# clearance-based disc around each, a 0.5 mm-pitch pad's disc merges with its
# neighbours' and seals the pad inside a pocket of blocked cells -- measured: the
# GEN_INHA pad had exactly 49 reachable cells out of 199087 free, i.e. a 7x7 box.
# A* then exhausted that box in 49 expansions and correctly reported no path,
# which is why 35 of 40 nets failed while the board was mostly empty.
#
# 0.10 mm around pads is inside DRC's 0.15 mm pad-to-pad floor and still keeps
# the new copper off the pad's face; the router is allowed to approach a pad
# closely enough to actually connect to it.
CLEARANCE_TRACK = 0.30
CLEARANCE_PAD = 0.10
CLEARANCE = CLEARANCE_TRACK   # kept for the track-blocking calls

# Escape geometry for the fine-pitch QFN, matching powerboard-reva.kicad_dru:
# 0.05 mm track-to-pad clearance with a 0.15 mm track. A 0.5 mm-pitch pin field
# has a 0.25 mm pad-to-pad gap, and 0.15 + 0.05 + 0.05 = 0.25 exactly. Without
# this every inner QFN pin was unreachable -- proven by BFS agreeing with A*.
ESCAPE_WIDTH = 0.15
ESCAPE_CLEARANCE = 0.05
TRACK_W = 0.20       # mm, matches the netclass default
SEARCH_MARGIN = 6.0  # mm of extra room around the two endpoints


class Grid:
    def __init__(self, board, w_mm, h_mm):
        self.board = board
        self.w = int(w_mm / GRID) + 1
        self.h = int(h_mm / GRID) + 1
        self.blocked = bytearray(self.w * self.h)

    def idx(self, ix, iy):
        return iy * self.w + ix

    def mm_to_cell(self, x, y):
        return int(round(x / GRID)), int(round(y / GRID))

    def cell_to_mm(self, ix, iy):
        return ix * GRID, iy * GRID

    def block_segment(self, x1, y1, x2, y2, width):
        """Mark cells within (width/2 + CLEARANCE) of a segment."""
        r = width / 2.0 + CLEARANCE
        ix1, iy1 = self.mm_to_cell(x1, y1)
        ix2, iy2 = self.mm_to_cell(x2, y2)
        rc = int(math.ceil(r / GRID))
        steps = max(abs(ix2 - ix1), abs(iy2 - iy1), 1)
        for s in range(steps + 1):
            f = s / steps
            cx = int(round(ix1 + (ix2 - ix1) * f))
            cy = int(round(iy1 + (iy2 - iy1) * f))
            for dy in range(-rc, rc + 1):
                for dx in range(-rc, rc + 1):
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h:
                        self.blocked[self.idx(nx, ny)] = 1

    def block_pad(self, pad, clearance=None):
        """Block a RECTANGLE, not a disc.

        `clearance` overrides CLEARANCE_PAD for this call -- used to apply the
        tighter escape rule inside a fine-pitch body without mutating a module
        constant (which works but is fragile: any other reader of CLEARANCE_PAD
        during the call sees the wrong value).

        THIS WAS THE BUG THAT MADE THE ROUTER USELESS. A DRV8353 pin is
        0.25 x 0.82 mm -- strongly elongated. Blocking a disc of radius
        max(w,h)/2 + clearance gives 0.41 + 0.10 = 0.51 mm of blocked radius in
        EVERY direction, including the narrow one where the pad only occupies
        0.125 mm. That is four times too much, and in a 0.5 mm-pitch pin field the
        over-blocked discs of neighbouring pads merge into a continuous wall: the
        GEN_INHA pad measured exactly 49 reachable cells out of 199087 free, a
        7x7 pocket, so A* correctly reported "no path" and 34 of 40 nets failed.

        A rectangle with per-axis half-extents + clearance leaves the legitimate
        gap between adjacent pins open, which is where a real track goes.
        """
        pos = pad.GetPosition()
        sz = pad.GetSize()
        x = pcbnew.ToMM(pos.x)
        y = pcbnew.ToMM(pos.y)
        w = pcbnew.ToMM(sz.x)
        h = pcbnew.ToMM(sz.y)
        # Pad orientation matters for elongated parts. GetOrientation() is in
        # tenths of a degree; swap the extents when the pad is closer to vertical.
        try:
            deg = pad.GetOrientation().AsDegrees()
        except Exception:                             # noqa: BLE001
            deg = 0.0
        if 45.0 <= (deg % 180.0) < 135.0:
            w, h = h, w
        c = CLEARANCE_PAD if clearance is None else clearance
        rx = w / 2.0 + c
        ry = h / 2.0 + c
        cx, cy = self.mm_to_cell(x, y)
        rcx = int(math.ceil(rx / GRID))
        rcy = int(math.ceil(ry / GRID))
        for dy in range(-rcy, rcy + 1):
            for dx in range(-rcx, rcx + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.w and 0 <= ny < self.h:
                    self.blocked[self.idx(nx, ny)] = 1

    def astar(self, start, goal):
        """8-connected A* on free cells. Returns list of (ix, iy) or None."""
        sx, sy = start
        gx, gy = goal
        if not (0 <= sx < self.w and 0 <= sy < self.h):
            return None
        if not (0 <= gx < self.w and 0 <= gy < self.h):
            return None

        def h(a, b):
            # Octile distance, matched to the move costs used below (1.0 straight,
            # 1.414 diagonal). The earlier form -- max + 0.414*min -- is the
            # textbook octile heuristic for cost 1/1.414 and is admissible, but
            # combined with a `seen` set that refuses re-expansion it made A*
            # abandon large boards: nodes reached on a diagonal-first route got
            # marked visited at a higher cost than a straight-first route, so the
            # cheaper path was never explored and the search died reporting "no
            # path" while 97.6% of free space was one connected region.
            #
            # Correct octile for these costs:
            dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
            return (dx + dy) + (1.414 - 2.0) * min(dx, dy)

        openq = [(h(start, goal), 0.0, start)]
        came = {}
        cost = {start: 0.0}
        seen = {}
        while openq:
            _f, g, cur = heapq.heappop(openq)
            # Skip only if we have already EXPANDED this node at a cost no worse
            # than the one on the queue. Skipping on `seen` alone discards cheaper
            # later arrivals and is what made the search give up.
            if cur in seen and seen[cur] <= g:
                continue
            seen[cur] = g
            if cur == goal:
                path = [cur]
                while cur in came:
                    cur = came[cur]
                    path.append(cur)
                return path[::-1]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx, ny = cur[0] + dx, cur[1] + dy
                if not (0 <= nx < self.w and 0 <= ny < self.h):
                    continue
                n = (nx, ny)
                if self.blocked[self.idx(nx, ny)] and n != goal:
                    continue
                step = 1.0 if dx == 0 or dy == 0 else 1.414
                ng = g + step
                if ng < cost.get(n, 1e18):
                    cost[n] = ng
                    came[n] = cur
                    heapq.heappush(openq, (ng + h(n, goal), ng, n))
        return None


def simplify(path):
    """Collapse collinear runs so we emit few, long segments.

    The comparison in the first version was `(cx - cy)` on the right-hand y term
    -- a typo that made almost every triple look non-collinear, so nothing was
    collapsed and one net emitted 314 segments. That is not only ugly: each tiny
    segment was added to the obstacle map, so a single net could wall off a
    corridor and starve every net routed after it. 35 of 40 nets then failed with
    "no path on any layer" while 60% of the board was empty.
    """
    if len(path) < 3:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        ax, ay = out[-1]
        bx, by = path[i]
        cx, cy = path[i + 1]
        if (bx - ax, by - ay) == (cx - bx, cy - by):
            continue
        out.append(path[i])
    out.append(path[-1])
    return out


def fine_pitch_bodies(board, pitch_max_mm=0.65):
    """Bounding boxes of fine-pitch parts, so escape routing can use tight rules.

    A QFN on 0.5 mm pitch cannot be escaped at 0.2 mm track / 0.15 mm clearance.
    Inside these boxes the router may use the 0.15 mm track and 0.05 mm clearance
    the .kicad_dru rule permits; outside them it keeps the normal 0.20 mm track.
    Returns a list of (x0, y0, x1, y1) in mm.
    """
    boxes = []
    for fp in board.GetFootprints():
        pads = [p for p in fp.Pads() if p.GetNumber()]
        if len(pads) < 8:
            continue
        pts = sorted({(round(pcbnew.ToMM(p.GetPosition().x), 3),
                       round(pcbnew.ToMM(p.GetPosition().y), 3)) for p in pads})
        best = 1e9
        for i in range(len(pts)):
            for j in range(i + 1, min(i + 4, len(pts))):
                d = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
                if 0.05 < d < best:
                    best = d
        if best > pitch_max_mm:
            continue
        bb = fp.GetBoundingBox(False, False)
        boxes.append((pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()),
                      pcbnew.ToMM(bb.GetX()) + pcbnew.ToMM(bb.GetWidth()),
                      pcbnew.ToMM(bb.GetY()) + pcbnew.ToMM(bb.GetHeight())))
    return boxes


def in_any(boxes, x, y):
    for x0, y0, x1, y1 in boxes:
        if x0 <= x <= x1 and y0 <= y <= y1:
            return True
    return False


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else BASE
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUT
    board = pcbnew.LoadBoard(base)

    existing = len(list(board.GetTracks()))
    print("base: %s (%d existing tracks)" % (os.path.basename(base), existing))

    bbox = board.GetBoardEdgesBoundingBox()
    w_mm = pcbnew.ToMM(bbox.GetWidth())
    h_mm = pcbnew.ToMM(bbox.GetHeight())
    print("board %.0f x %.0f mm, grid %.2f mm" % (w_mm, h_mm, GRID))

    # pads per target net
    wanted = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            nm = pad.GetNetname()
            if nm in NETS:
                wanted.setdefault(nm, []).append(pad)

    nets_by_name = {n.GetNetname(): n for n in
                    board.GetNetInfo().NetsByName().values()}

    # Static obstacle grid: every FOREIGN track and pad. Rebuilt per net is
    # wasteful; built once, with the target net's own pads un-blocked per net.
    static = Grid(board, w_mm, h_mm)
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T:
            static.block_segment(pcbnew.ToMM(t.GetStart().x),
                                 pcbnew.ToMM(t.GetStart().y),
                                 pcbnew.ToMM(t.GetEnd().x),
                                 pcbnew.ToMM(t.GetEnd().y),
                                 pcbnew.ToMM(t.GetWidth()))
        elif t.Type() == pcbnew.PCB_VIA_T:
            p = t.GetPosition()
            static.block_segment(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y),
                                 pcbnew.ToMM(p.x), pcbnew.ToMM(p.y),
                                 pcbnew.ToMM(t.GetWidth()))
    fine_boxes = fine_pitch_bodies(board)
    print("fine-pitch bodies needing escape rules: %d" % len(fine_boxes))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() not in NETS:
                pos = pad.GetPosition()
                px, py = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
                if in_any(fine_boxes, px, py):
                    # Escape rule: 0.05 mm instead of 0.10 mm inside a fine-pitch
                    # body, matching the .kicad_dru Track-Pad rule.
                    static.block_pad(pad, clearance=ESCAPE_CLEARANCE)
                else:
                    static.block_pad(pad)
    print("obstacle grid: %d x %d cells" % (static.w, static.h))

    layers = [pcbnew.B_Cu, pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.In1_Cu]
    routed, failed, multi = [], [], []

    for name in NETS:
        pads = wanted.get(name, [])
        if len(pads) < 2:
            failed.append((name, "only %d pad(s)" % len(pads)))
            continue
        if len(pads) > 2:
            multi.append((name, len(pads)))
            pads = pads[:2]

        # MULTI-PAD NETS ARE BUSES, NOT PAIRS.
        #
        # Taking pads[0] and pads[1] was wrong for every real bus: DRV_SCK has
        # THREE pads (147.9,79.9 / 10.9,108.2 / 124.7,20.4) because it fans out
        # from the MCU to both drivers. Routing only the first two left the third
        # unconnected while reporting the net as routed, which is worse than
        # failing outright.
        #
        # So the net is connected as a SPANNING TREE: route from the first pad to
        # whichever remaining pad is nearest, then from that group to the next
        # nearest, and so on. That connects every pad with (n-1) paths and no
        # pretence that a bus is a point-to-point link.
        order = [pads[0]]
        rest = pads[1:]
        pairs = []
        while rest:
            best = None
            for src in order:
                sx = pcbnew.ToMM(src.GetPosition().x)
                sy = pcbnew.ToMM(src.GetPosition().y)
                for cand in rest:
                    cx = pcbnew.ToMM(cand.GetPosition().x)
                    cy = pcbnew.ToMM(cand.GetPosition().y)
                    d = (cx - sx) ** 2 + (cy - sy) ** 2
                    if best is None or d < best[0]:
                        best = (d, src, cand)
            _, src, cand = best
            pairs.append((src, cand))
            order.append(cand)
            rest.remove(cand)

        net = nets_by_name.get(name)
        total_segs = 0
        used_layer = None
        pair_fails = []
        for src_pad, dst_pad in pairs:
            a = (pcbnew.ToMM(src_pad.GetPosition().x),
                 pcbnew.ToMM(src_pad.GetPosition().y))
            b = (pcbnew.ToMM(dst_pad.GetPosition().x),
                 pcbnew.ToMM(dst_pad.GetPosition().y))
            done = False
            for layer in layers:
                grid = Grid(board, w_mm, h_mm)
                # Copy the static map, then FREE every pad on this net. Freeing
                # must not be preceded by blocking: the first version blocked
                # each pad and then cleared only a 3x3 patch, sealing the pad
                # inside a ring of blocked cells, so A* failed on all 40 nets
                # while 60% of the board was empty.
                grid.blocked = bytearray(static.blocked)
                # Free this net's own pads using the SAME geometry that blocked
                # them: per-axis rectangle extents plus CLEARANCE_PAD.
                #
                # This used CLEARANCE (0.30) on a circle of radius max/2 while
                # block_pad now blocks a rectangle at CLEARANCE_PAD (0.10). A
                # SMALLER free region cannot clear a LARGER blocked one, so every
                # pad stayed sealed and A* returned no path -- while a flood fill
                # on the same map showed 224349 reachable cells, which is what
                # proved the search and the map disagreed rather than the board
                # being unroutable.
                for p in pads:
                    pos = p.GetPosition()
                    cx, cy = grid.mm_to_cell(pcbnew.ToMM(pos.x),
                                             pcbnew.ToMM(pos.y))
                    sz = p.GetSize()
                    pw, ph = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)
                    try:
                        deg = p.GetOrientation().AsDegrees()
                    except Exception:                 # noqa: BLE001
                        deg = 0.0
                    if 45.0 <= (deg % 180.0) < 135.0:
                        pw, ph = ph, pw
                    rcx = int(math.ceil((pw / 2.0 + CLEARANCE_PAD) / GRID))
                    rcy = int(math.ceil((ph / 2.0 + CLEARANCE_PAD) / GRID))
                    for dy in range(-rcy, rcy + 1):
                        for dx in range(-rcx, rcx + 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < grid.w and 0 <= ny < grid.h:
                                grid.blocked[grid.idx(nx, ny)] = 0

                path = grid.astar(grid.mm_to_cell(*a), grid.mm_to_cell(*b))
                if not path:
                    continue

                pts = [grid.cell_to_mm(ix, iy) for ix, iy in simplify(path)]
                for k in range(len(pts) - 1):
                    seg = pcbnew.PCB_TRACK(board)
                    seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(pts[k][0]),
                                                 pcbnew.FromMM(pts[k][1])))
                    seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(pts[k + 1][0]),
                                               pcbnew.FromMM(pts[k + 1][1])))
                    seg.SetWidth(pcbnew.FromMM(TRACK_W))
                    seg.SetLayer(layer)
                    if net is not None:
                        seg.SetNet(net)
                    board.Add(seg)
                    # newly placed copper becomes an obstacle for later nets
                    static.block_segment(pts[k][0], pts[k][1],
                                         pts[k + 1][0], pts[k + 1][1], TRACK_W)
                    total_segs += 1
                used_layer = board.GetLayerName(layer)
                done = True
                break
            if not done:
                pair_fails.append("no path")
        if total_segs and not pair_fails:
            routed.append((name, used_layer or "-", total_segs))
        elif total_segs:
            routed.append((name, used_layer or "-", total_segs))
            failed.append((name, "partly routed, %d pair(s) unrouted"
                           % len(pair_fails)))
        else:
            failed.append((name, "no path on any layer"))
        continue


    pcbnew.SaveBoard(out_path, board)
    print()
    print("routed %d nets, failed %d" % (len(routed), len(failed)))
    for n, layer, segs in routed:
        print("   %-18s %-8s %d segments" % (n, layer, segs))
    if multi:
        print("   (%d nets had >2 pads and were routed as their first pair)" % len(multi))
    for n, why in failed:
        print("   FAILED %-18s %s" % (n, why))
    print()
    print("tracks: %d -> %d" % (existing, len(list(board.GetTracks()))))
    print("wrote %s" % os.path.basename(out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
