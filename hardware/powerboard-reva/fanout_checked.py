#!/usr/bin/python3
"""Insert a collision-checked escape fan-out for fine-pitch pads.

WHY THIS VERSION EXISTS
-----------------------
`fanout_escape.py` built a geometrically correct fan-out -- 57 stubs, widths
0.250/0.300/0.350 mm derived from the package pitch, vias outside the body -- and
then made the board worse, because it placed the stubs WITHOUT CHECKING them
against the 2708 tracks already present:

                  v1      fanout (blind)
    clearance       0      119
    shorting        0       67
    hole_to_hole    0       38
    via_dangling    0       51
    tracks_crossing 0        9

That is the same failure as the inter-block merge: new copper added blind to old
copper. This script does the same construction but tests every stub and every via
against everything already on the board first, and SKIPS what does not fit rather
than forcing it.

THE RULE
--------
For a candidate stub, the occupied region is its centreline widened by
(width/2 + clearance). That rectangle, expanded by the clearance, must not overlap
any copper of a different net on F.Cu: existing tracks, pads, or via annuli.

For a candidate via, the annulus (radius size/2) widened by clearance must not
overlap foreign copper on ANY layer, and the drill must keep hole-to-hole spacing
from every existing via.

Bounding-box tests are used throughout. They are CONSERVATIVE -- they reject a stub
that is geometrically fine but whose bounding box clips a neighbour -- so the result
is a subset of what is truly routable. That is the right direction to err: a skipped
stub is an open item, whereas an inserted short is a silent defect.

Output is a board where every inserted stub is known clear, plus a report of how
many were skipped and why.
"""
import sys
sys.path.insert(0, '.')
import csv
import math

import pcbnew

import hand_route_interblock as H
import fanout_escape as F

# The .kicad_dru grants a RELAXATION, not a blanket rule change:
#
#   Track-to-Pad  : 0.05 mm, and ONLY inside a fine-pitch body
#   Pad-to-Pad    : 0.15 mm
#   Track-to-Track: 0.20 mm (netclass default, never relaxed)
#
# Using 0.05 mm for everything was wrong and produced 27 clearance violations on
# the checked fan-out: the stub is granted 0.05 mm against PADS, but against other
# TRACKS it still owes the netclass 0.2 mm. Applying the escape value everywhere
# checked against a rule that does not exist.
CLEAR_ESCAPE = 0.05   # track-to-pad, inside a fine-pitch body only
CLEAR_TRACK = 0.20    # track-to-track and track-to-via, everywhere
VIA_DRILL = 0.3
VIA_SIZE = 0.6
HOLE_TO_HOLE = 0.50


class Box:
    __slots__ = ('x0', 'y0', 'x1', 'y1', 'net', 'kind')

    def __init__(self, x0, y0, x1, y1, net, kind):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.net, self.kind = net, kind

    def near(self, x0, y0, x1, y1, pad):
        return not (self.x1 + pad <= x0 or self.x0 - pad >= x1 or
                    self.y1 + pad <= y0 or self.y0 - pad >= y1)


def existing_copper(board):
    """Every piece of existing copper as a bounding box, tagged by net and layer."""
    out = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            out.append(Box(pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()),
                           pcbnew.ToMM(bb.GetX()) + pcbnew.ToMM(bb.GetWidth()),
                           pcbnew.ToMM(bb.GetY()) + pcbnew.ToMM(bb.GetHeight()),
                           pad.GetNetname(), 'pad'))
    for t in board.GetTracks():
        bb = t.GetBoundingBox()
        x0 = pcbnew.ToMM(bb.GetX())
        y0 = pcbnew.ToMM(bb.GetY())
        x1 = x0 + pcbnew.ToMM(bb.GetWidth())
        y1 = y0 + pcbnew.ToMM(bb.GetHeight())
        kind = 'via' if t.Type() == pcbnew.PCB_VIA_T else 'track'
        out.append(Box(x0, y0, x1, y1, t.GetNetname(), kind))
    return out


def stub_clear(boxes, net, x0, y0, x1, y1, half_w, in_fine_body):
    """Is the stub corridor free of foreign copper?

    The clearance owed depends on WHAT it is checked against, not on where the stub
    is: a pad inside a fine-pitch body owes 0.05 mm, but a neighbouring track always
    owes the 0.20 mm netclass. Checking everything at the escape value is what
    produced 27 clearance violations on the first checked run.
    """
    bx0 = min(x0, x1) - half_w
    bx1 = max(x0, x1) + half_w
    by0 = min(y0, y1) - half_w
    by1 = max(y0, y1) + half_w
    for b in boxes:
        if b.net == net:
            continue
        if b.kind == 'pad':
            clearance = CLEAR_ESCAPE if in_fine_body else CLEAR_TRACK
        else:
            clearance = CLEAR_TRACK
        if b.near(bx0, by0, bx1, by1, clearance):
            return False, b
    return True, None


def via_clear(boxes, vias, net, x, y, clearance):
    """Is the via annulus free of foreign copper, and is hole spacing OK?

    A via is never inside a fine-pitch body in this construction (it goes outside
    the body edge), so it always owes the netclass clearance.
    """
    r = VIA_SIZE / 2.0
    clearance = max(clearance, CLEAR_TRACK)
    for b in boxes:
        if b.net == net:
            continue
        if b.near(x - r, y - r, x + r, y + r, clearance):
            return False, 'copper:%s:%s' % (b.kind, b.net)
    for vx, vy in vias:
        if math.hypot(vx - x, vy - y) < HOLE_TO_HOLE:
            return False, 'hole_to_hole'
    return True, None


def vec(x_mm, y_mm):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm))


def main():
    src = 'powerboard-reva-routed.kicad_pcb'
    dst = 'powerboard-reva-fanout2.kicad_pcb'
    board = pcbnew.LoadBoard(src)
    print("loaded %s: %d copper items" % (src, len(list(board.GetTracks()))))

    boxes = existing_copper(board)
    vias = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
            for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    print("existing: %d boxes, %d vias" % (len(boxes), len(vias)))

    fine = H.fine_pitch_bodies(board)
    print("fine-pitch bodies: %d" % len(fine))

    inserted = skipped = 0
    reasons = {}
    points = []

    for fp in board.GetFootprints():
        pads = [p for p in fp.Pads() if p.GetNumber()]
        if len(pads) < 8:
            continue
        if F.nearest_pitch(fp, pads[0]) > 0.65:
            continue
        for pad in pads:
            net = pad.GetNetname()
            if net not in H.NETS:
                continue
            d = F.outward_dir(fp, pad)
            w = F.escape_width(fp, pad)
            edge = F.body_edge_distance(fp, pad, d)
            length = edge + F.VIA_MARGIN
            if length <= 0.2:
                skipped += 1
                reasons['too_short'] = reasons.get('too_short', 0) + 1
                continue
            p = pad.GetPosition()
            px, py = pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)
            ex = px + d[0] * length
            ey = py + d[1] * length

            ok, why = stub_clear(boxes, net, px, py, ex, ey, w / 2.0,
                                 H.in_any(fine, px, py))
            if not ok:
                skipped += 1
                k = 'stub_%s' % why.kind
                reasons[k] = reasons.get(k, 0) + 1
                continue
            ok, why = via_clear(boxes, vias, net, ex, ey, CLEAR_ESCAPE)
            if not ok:
                skipped += 1
                k = 'via_%s' % str(why).split(':')[0]
                reasons[k] = reasons.get(k, 0) + 1
                continue

            t = pcbnew.PCB_TRACK(board)
            t.SetStart(vec(px, py))
            t.SetEnd(vec(ex, ey))
            t.SetWidth(pcbnew.FromMM(w))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(pad.GetNet())
            board.Add(t)

            v = pcbnew.PCB_VIA(board)
            v.SetPosition(vec(ex, ey))
            v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetWidth(pcbnew.FromMM(VIA_SIZE))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(pad.GetNet())
            board.Add(v)

            # the new copper becomes an obstacle for the next candidate
            boxes.append(Box(min(px, ex) - w / 2, min(py, ey) - w / 2,
                             max(px, ex) + w / 2, max(py, ey) + w / 2, net, 'track'))
            boxes.append(Box(ex - VIA_SIZE / 2, ey - VIA_SIZE / 2,
                             ex + VIA_SIZE / 2, ey + VIA_SIZE / 2, net, 'via'))
            vias.append((ex, ey))
            inserted += 1
            points.append((net, ex, ey, w, length))

    print("inserted: %d   skipped: %d" % (inserted, skipped))
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("   %-22s %d" % (k, v))
    print("nets with escape points: %d" % len({p[0] for p in points}))

    board.Save(dst)
    print("wrote %s" % dst)
    with open('routing/onboard/escape-points2.csv', 'w') as f:
        f.write("net,x_mm,y_mm,width_mm,length_mm\n")
        for net, x, y, w, L in sorted(points):
            f.write("%s,%.3f,%.3f,%.3f,%.3f\n" % (net, x, y, w, L))
    print("wrote routing/onboard/escape-points2.csv")
    return 0


if __name__ == '__main__':
    sys.exit(main())
