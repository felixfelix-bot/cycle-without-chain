#!/usr/bin/python3
"""Read tracks from a routed board and dump them as JSON.

Runs as its own process, after import_ses.py has finished. ImportSpecctraSES
poisons the interpreter that ran it, so the reading must happen elsewhere -- a
fresh process loads the imported file and enumerates tracks normally.

Usage: read_tracks.py <board.kicad_pcb> <out.json>
Writes a JSON list of {netcode, layer_id, width, x1, y1, x2, y2} in mm.
"""
import json
import sys

import pcbnew


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: read_tracks.py <board> <out.json>")
        return 2
    board_path, out_path = sys.argv[1:3]
    board = pcbnew.LoadBoard(board_path)
    tracks = []
    for t in board.GetTracks():
        # VIAS MUST BE CARRIED ACROSS TOO.
        #
        # FreeRouting routed on all four layers, so it changed layers through
        # vias. This loop skipped anything that was not PCB_TRACE_T, so every via
        # was dropped: F.Cu and In1.Cu tracks then met at a point with no via
        # between them, producing 199 dangling ends and 499 unconnected items
        # while the tracks themselves looked fine. DRC's own wording -- "Track
        # has unconnected end" -- is what pointed at a missing interconnect
        # rather than a missing track.
        if t.Type() == pcbnew.PCB_VIA_T:
            tracks.append({
                "kind": "via",
                "netname": t.GetNetname(),
                "netcode": t.GetNetCode(),
                "x1": pcbnew.ToMM(t.GetPosition().x),
                "y1": pcbnew.ToMM(t.GetPosition().y),
                "width": pcbnew.ToMM(t.GetWidth()),
                "drill": pcbnew.ToMM(t.GetDrillValue()),
                "top": t.TopLayer(),
                "bottom": t.BottomLayer(),
            })
            continue
        if t.Type() != pcbnew.PCB_TRACE_T:
            continue
        tracks.append({
            # Emit the net NAME as well as the code. The code is meaningless
            # across boards: removing footprints from a sub-board deletes nets
            # that no longer have pads and RENUMBERS the rest, so block net 37 is
            # not master net 37. Merging by code produced 2428 tracks that were
            # all dangling and left 499 items unconnected -- exactly the same
            # count as an unrouted board, which is what gave the bug away.
            "kind": "track",
            "netname": t.GetNetname(),
            "netcode": t.GetNetCode(),
            "layer_id": t.GetLayer(),
            "width": pcbnew.ToMM(t.GetWidth()),
            "x1": pcbnew.ToMM(t.GetStart().x),
            "y1": pcbnew.ToMM(t.GetStart().y),
            "x2": pcbnew.ToMM(t.GetEnd().x),
            "y2": pcbnew.ToMM(t.GetEnd().y),
        })
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(tracks, fh)
    print("read %d tracks" % len(tracks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
