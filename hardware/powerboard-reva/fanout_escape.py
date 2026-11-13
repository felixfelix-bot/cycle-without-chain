#!/usr/bin/python3
"""Emit escape stubs + vias for pads trapped inside fine-pitch pin fields.

WHY THIS EXISTS
---------------
The 43 inter-block nets could not be routed. Three distinct causes were found and
fixed in turn (clearance rule, routing order, then grid resolution), and the last
one is geometric, measured by diagnose_wall.py:

    region around U1 pin 32:  1478657 cells
    region around U17 pin 40:    6149 cells      <- the LQFP-100 pin field
    corridor between adjacent LQFP pins: 0.20 - 2*0.05 = 0.10 mm == exactly 1 grid cell

A cell-by-cell search cannot follow a one-cell corridor; rounding closes it. So the
escape is not a search problem at all -- it is a fixed geometric fact:

    pad row at 0.5 mm pitch, pad width w  ->  gap = 0.5 - w
    escape track width = gap - 2 * 0.05 mm clearance
        LQFP-100 (0.30 mm pads): 0.20 - 0.10 = 0.10 mm
        QFN-40   (0.25 mm pads): 0.25 - 0.10 = 0.15 mm

Both are ordinary 1 oz prototype features. So this script draws the stub straight
out along the package's outward normal and drops a via just outside the body, where
there is room. Routing then continues on B.Cu, which is empty.

This deliberately does NOT try to be clever: one straight segment per pad, one via
per pad, length fixed from the footprint bounding box. Every stub is inspectable and
its width is derived from the package, not guessed.
"""
import sys
sys.path.insert(0, '.')
import math

import pcbnew

import hand_route_interblock as H

# Clearance the .kicad_dru grant allows for Track-to-Pad in a fine-pitch body.
ESCAPE_CLEARANCE = 0.05
# Nothing thinner than this is worth drawing; below it a stub is a fab risk.
MIN_STUB = 0.10
# How far past the body edge the via goes.
VIA_MARGIN = 0.45
VIA_DRILL = 0.3
VIA_SIZE = 0.6


def nearest_pitch(fp, pad):
    """Distance to the nearest other pad on the same footprint, in mm."""
    p = pad.GetPosition()
    px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    best = 1e9
    for q in fp.Pads():
        if q.GetNumber() == pad.GetNumber():
            continue
        r = q.GetPosition()
        d = math.hypot(pcbnew.ToMM(r.x) - px, pcbnew.ToMM(r.y) - py)
        if 1e-6 < d < best:
            best = d
    return best


def pitch_axis(fp, pad):
    """Unit vector from this pad toward its nearest neighbour: the pitch direction."""
    p = pad.GetPosition()
    px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    best = None
    for q in fp.Pads():
        if q.GetNumber() == pad.GetNumber():
            continue
        r = q.GetPosition()
        qx, qy = pcbnew.ToMM(r.x), pcbnew.ToMM(r.y)
        d = math.hypot(qx - px, qy - py)
        if 1e-6 < d and (best is None or d < best[0]):
            best = (d, qx - px, qy - py)
    if best is None:
        return (1.0, 0.0)
    _, dx, dy = best
    n = math.hypot(dx, dy) or 1.0
    return (dx / n, dy / n)


def extent_along(fp, pad, d):
    """Pad extent projected onto direction `d`, in mm.

    THIS WAS THE BUG. The previous version used max(size_x, size_y), on the theory
    that the larger dimension leaves the smaller gap. That is wrong for a
    perimeter pad: the pad's LONG axis runs perpendicular to the pitch, so a
    VSSOP-8 pad is 1.250 x 0.350 while the pitch is 0.500 -- max() gives 1.250,
    gap = 0.5 - 1.25 = -0.750 mm, and every stub clamped to MIN_STUB. All 57 stubs
    came out at exactly 0.100 mm, which is what exposed it.

    The correct extent is the pad's size projected onto the pitch direction: 0.350
    for the VSSOP-8, giving a real gap of 0.150 mm.
    """
    sz = pad.GetSize()
    sx, sy = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)
    if abs(d[0]) >= abs(d[1]):
        return sx
    return sy


def escape_width(fp, pad):
    """Stub width for a pad escaping PERPENDICULAR to its pin row.

    The stub does not run between two pads -- it leaves the pad outward, away from
    the package body. So the width is bounded by the pad's own extent across the
    pitch direction, and the clearance to the neighbouring pads in the same row is
    simply the pad-to-pad gap, which the package fixes:

        VSSOP-8    pitch 0.500, pad across-pitch 0.350 -> gap 0.150
        QFN-40     pitch 0.500, pad across-pitch 0.250 -> gap 0.250
        LQFP-100   pitch 0.500, pad across-pitch 0.300 -> gap 0.200

    All three gaps exceed the 0.05 mm escape clearance, so a stub no wider than the
    pad is always legal.
    """
    d = pitch_axis(fp, pad)
    across = extent_along(fp, pad, d)
    # A stub no wider than the pad leaves gap/2 to each neighbour, and every gap
    # here (0.15 / 0.20 / 0.25 mm) is at least 3x the 0.05 mm escape clearance.
    return max(MIN_STUB, across)


def outward_dir(fp, pad):
    """Unit vector pointing away from the footprint centre, snapped to an axis."""
    c = fp.GetPosition()
    p = pad.GetPosition()
    dx = pcbnew.ToMM(p.x) - pcbnew.ToMM(c.x)
    dy = pcbnew.ToMM(p.y) - pcbnew.ToMM(c.y)
    if abs(dx) >= abs(dy):
        return (1.0 if dx >= 0 else -1.0, 0.0)
    return (0.0, 1.0 if dy >= 0 else -1.0)


def body_edge_distance(fp, pad, d):
    """Distance along `d` from the pad centre to the footprint bounding box edge."""
    bb = fp.GetBoundingBox(False, False)
    x0 = pcbnew.ToMM(bb.GetX())
    y0 = pcbnew.ToMM(bb.GetY())
    x1 = x0 + pcbnew.ToMM(bb.GetWidth())
    y1 = y0 + pcbnew.ToMM(bb.GetHeight())
    p = pad.GetPosition()
    px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
    if d[0] > 0:
        return max(0.0, x1 - px)
    if d[0] < 0:
        return max(0.0, px - x0)
    if d[1] > 0:
        return max(0.0, y1 - py)
    return max(0.0, py - y0)


def vec(x_mm, y_mm):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))


def main():
    src = 'powerboard-reva-routed.kicad_pcb'
    dst = 'powerboard-reva-fanout.kicad_pcb'
    board = pcbnew.LoadBoard(src)
    print("loaded %s: %d tracks" % (src, len(list(board.GetTracks()))))

    fine = H.fine_pitch_bodies(board)
    print("fine-pitch bodies: %d" % len(fine))

    stubs = vias = skipped = 0
    by_net = {}

    for fp in board.GetFootprints():
        pads = [p for p in fp.Pads() if p.GetNumber()]
        if len(pads) < 8:
            continue
        # Skip parts that are not fine pitch at all.
        sample = pads[0]
        if nearest_pitch(fp, sample) > 0.65:
            continue
        for pad in pads:
            net = pad.GetNetname()
            if net not in H.NETS:
                continue
            d = outward_dir(fp, pad)
            w = escape_width(fp, pad)
            edge = body_edge_distance(fp, pad, d)
            length = edge + VIA_MARGIN
            if length <= 0.2:
                skipped += 1
                continue
            p = pad.GetPosition()
            px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            ex = px + d[0] * length
            ey = py + d[1] * length

            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(px, py))
            t.SetEnd(vec(ex, ey))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(pad.GetNet())
            board.Add(t)
            stubs += 1

            v = pcbnew.PCB_VIA(board)
            v.SetPosition(vec(ex, ey))
            v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetWidth(pcbnew.FromMM(VIA_SIZE))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(pad.GetNet())
            board.Add(v)
            vias += 1

            by_net.setdefault(net, []).append((ex, ey, w, length))

    print("stubs: %d   vias: %d   skipped: %d" % (stubs, vias, skipped))
    print("nets with escape points: %d" % len(by_net))

    widths = {}
    for net, pts in by_net.items():
        for _, _, w, _ in pts:
            widths[round(w, 3)] = widths.get(round(w, 3), 0) + 1
    print("stub widths used: %s" % ", ".join(
        "%.3f mm x%d" % (k, v) for k, v in sorted(widths.items())))

    board.Save(dst)
    print("wrote %s" % dst)

    with open('routing/onboard/escape-points.csv', 'w') as f:
        f.write("net,x_mm,y_mm,width_mm,length_mm\n")
        for net, pts in sorted(by_net.items()):
            for x, y, w, L in pts:
                f.write("%s,%.3f,%.3f,%.3f,%.3f\n" % (net, x, y, w, L))
    print("wrote routing/onboard/escape-points.csv")
    return 0


if __name__ == '__main__':
    sys.exit(main())
