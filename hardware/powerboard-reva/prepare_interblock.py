#!/usr/bin/python3
"""Prepare an inter-block routing sub-board: strip tracks, keep only target nets.

Takes the merged routed board, deletes every existing track and via (they are
already recorded on the merged board and re-routing them is wasted work), then
removes all nets that are NOT in the target list so FreeRouting has a 43-net
problem instead of a 277-net one.

Removing a net means removing it from the DSN, not from the board's pads: the pads
stay, they simply carry no net, so the router sees them as obstacles rather than
targets. That keeps the board geometry identical to the one the tracks will land
on, which is the whole point of routing this separately.

Usage: prepare_interblock.py <in.kicad_pcb> <out.kicad_pcb> <NET1,NET2,...>
"""
import sys

import pcbnew


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: prepare_interblock.py <in> <out> <net,net,...>")
        return 2
    src, dst, netlist = sys.argv[1:4]
    keep = set(netlist.split(","))

    board = pcbnew.LoadBoard(src)

    # 1. Drop every existing track and via: already on the merged board.
    removed = 0
    for t in list(board.GetTracks()):
        board.Remove(t)
        removed += 1
    print("removed %d existing tracks/vias" % removed)

    # 2. Drop every net we are not routing, so the DSN is small.
    netinfo = board.GetNetInfo()
    dropped = 0
    for name, net in list(netinfo.NetsByName().items()):
        if name in keep or not name:
            continue
        # Unassign this net from every pad: the pads stay as obstacles.
        code = net.GetNetCode()
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() == code:
                    pad.SetNetCode(0)
        dropped += 1
    print("unassigned %d nets outside the target list" % dropped)

    pcbnew.SaveBoard(dst, board)
    print("wrote %s" % dst)

    # 3. Export the DSN here rather than in the orchestrator, so this process is
    # the only one that ever holds a board with modified nets. Exporting after
    # SaveBoard in the same process is safe; importing a SES here is not.
    dsn = dst.replace(".kicad_pcb", ".dsn")
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        print("FAIL: DSN export")
        return 1
    print("wrote %s" % dsn)
    return 0


if __name__ == "__main__":
    sys.exit(main())
