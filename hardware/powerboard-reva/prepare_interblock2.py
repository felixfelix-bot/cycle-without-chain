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
