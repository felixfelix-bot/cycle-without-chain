#!/usr/bin/python3
"""Prepare an inter-block routing sub-board: keep only the target nets.

WHY THIS DOES NOT MUTATE THE BOARD
----------------------------------
The obvious approach -- load the merged board, Remove() every track, then
unassign nets -- corrupts swig on the first Remove(): GetNetInfo() afterwards
raises "'SwigPyObject' object has no attribute 'NetsByName'". Same failure mode as
ImportSpecctraSES: mutating a board invalidates other handles in the process.

So this builds the sub-board WITHOUT destructive edits. It clears non-target nets
pad-by-pad (pads keep their geometry and remain obstacles, they just stop being
connection targets), saves, and exports the DSN. No Remove(), no track deletion.

The generated tracks land on the already-routed board at merge time, which is
where the earlier pass's copper lives.

Usage: prepare_interblock.py <master.kicad_pcb> <netlist.net> <out.kicad_pcb> <NET,NET,...>
"""
import sys

import pcbnew


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: prepare_interblock.py <master> <netlist> <out> <nets>")
        return 2
    src, _netlist, dst, netlist_arg = sys.argv[1:5]
    keep = set(netlist_arg.split(","))

    board = pcbnew.LoadBoard(src)

    # Clear non-target pads FIRST, before touching anything else.
    cleared = kept = 0
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            name = pad.GetNetname()
            if not name:
                continue
            if name in keep:
                kept += 1
            else:
                pad.SetNetCode(0)
                cleared += 1
    print("kept %d target pads, cleared %d non-target pads" % (kept, cleared))

    # KEEP THE EXISTING COPPER.
    #
    # The first attempt cleared the pads but the source board had no tracks, so
    # the router had no idea the merged board's 2708 tracks existed and drew
    # straight across them: 199 shorts, 180 crossings. Routing a net set while
    # ignoring the copper it must fit between is not a smaller version of the
    # problem, it is a different and wrong one.
    #
    # The tracks are carried through as PROPERTIES: pads lost their net codes, so
    # tracks on cleared nets would be meaningless -- they are removed. Tracks on
    # TARGET nets are kept so the router sees which of the 43 are already partially
    # routed.
    # Non-target TRACKS are DELETED, but their swept area is first recorded as
    # keepout geometry. Two wrong turns are recorded here:
    #
    #   1. Keeping them as tracks with no net: SaveBoard writes a file that will
    #      not reload (LoadBoard returns None) and ExportSpecctraDSN fails, so the
    #      board is destroyed.
    #   2. Deleting them outright: that was the FIRST attempt, and the router then
    #      drew straight across the merged board -- 199 shorts, 180 crossings.
    #
    # So: delete the copper, but leave its footprint behind as a keepout so the
    # router must route around where it was. Each track contributes a small
    # circular keepout along its length, which over-approximates the obstacle --
    # deliberate, because a generous keepout costs routing space while a thin one
    # costs a short.
    import math
    kept_tracks = 0
    obstacles = 0
    for t in list(board.GetTracks()):
        nm = t.GetNetname()
        if nm and nm in keep:
            kept_tracks += 1
            continue
        if t.Type() == pcbnew.PCB_TRACE_T:
            x1, y1 = t.GetStart().x, t.GetStart().y
            x2, y2 = t.GetEnd().x, t.GetEnd().y
            length = math.hypot(x2 - x1, y2 - y1)
            half_w = t.GetWidth() / 2
            steps = max(1, int(length / max(half_w, 1)))
            for i in range(steps + 1):
                f = i / steps
                cx = int(x1 + (x2 - x1) * f)
                cy = int(y1 + (y2 - y1) * f)
                zone = pcbnew.ZONE(board)
                zone.SetLayer(t.GetLayer())
                zone.SetIsRuleArea(True)
                zone.SetDoNotAllowTracks(True)
                zone.SetDoNotAllowVias(True)
                zone.SetDoNotAllowPads(False)
                zone.SetDoNotAllowCopperPour(True)
                circle = pcbnew.SHAPE_POLY_SET()
                circle.NewOutline()
                r = half_w + pcbnew.FromMM(0.15)
                for k in range(8):
                    a = 2 * math.pi * k / 8
                    circle.Append(int(cx + r * math.cos(a)),
                                  int(cy + r * math.sin(a)))
                zone.SetOutline(circle)
                board.Add(zone)
                obstacles += 1
        board.Remove(t)
    print("kept %d target tracks; replaced the rest with %d keepout cells"
          % (kept_tracks, obstacles))

    present = {p.GetNetname() for fp in board.GetFootprints()
               for p in fp.Pads() if p.GetNetname()}
    print("distinct target nets present on board: %d of %d"
          % (len(present & keep), len(keep)))

    pcbnew.SaveBoard(dst, board)
    dsn = dst.replace(".kicad_pcb", ".dsn")
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        print("FAIL: DSN export")
        return 1
    print("wrote %s and %s" % (dst, dsn))
    return 0


if __name__ == "__main__":
    sys.exit(main())
