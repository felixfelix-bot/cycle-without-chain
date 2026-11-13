#!/usr/bin/python3
"""Merge harvested block tracks onto the master board, in one clean process.

Imports the track JSON that route_board_blocks.py produced and draws each segment
on powerboard-reva.kicad_pcb. Writes to a NEW file so the unrouted master is not
destroyed if the merge is wrong -- a merge you cannot undo is worse than no merge.

This is the only script in the routing chain that both loads a board and adds
tracks to it. That combination is safe as long as ImportSpecctraSES never runs
here, which is why the SES import lives in its own process.

Usage: /usr/bin/python3 merge_tracks.py [in.json] [out.kicad_pcb]
"""
import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(HERE, "powerboard-reva.kicad_pcb")
TRACKS = os.path.join(HERE, "routing", "blocks", "all-tracks.json")
OUT = os.path.join(HERE, "powerboard-reva-routed.kicad_pcb")


def main() -> int:
    """Usage: merge_tracks.py [in.json] [out.kicad_pcb] [base.kicad_pcb]

    The base matters: merging onto the unrouted master is right for the first
    pass, but merging inter-block tracks must land on the ALREADY ROUTED board or
    the first pass's tracks are discarded. It defaults to the unrouted master, so
    every existing caller keeps its meaning and the routed-base case must ask for
    it explicitly.
    """
    tracks_path = sys.argv[1] if len(sys.argv) > 1 else TRACKS
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUT
    base_path = sys.argv[3] if len(sys.argv) > 3 else MASTER
    if not os.path.exists(tracks_path):
        print("FAIL: %s missing; run route_board_blocks.py first" % tracks_path)
        return 1
    tracks = json.load(open(tracks_path, encoding="utf-8"))
    print("segments to merge: %d" % len(tracks))

    board = pcbnew.LoadBoard(base_path)
    before = len(list(board.GetTracks()))
    print("base: %s (%d existing tracks)"
          % (os.path.basename(base_path), before))

    # NET IDENTITY MUST BE BY NAME, NOT CODE.
    #
    # Removing footprints from a sub-board deletes nets that lost all their pads
    # and renumbers the survivors, so a block's net code does not correspond to
    # the master's. Merging by code produced 2428 tracks that were every one
    # dangling, and DRC still reported 499 unconnected -- the same number as an
    # unrouted board. That coincidence was the tell.
    nets_by_name = {}
    for net in board.GetNetInfo().NetsByName().values():
        try:
            nets_by_name[net.GetNetname()] = net
        except Exception:                             # noqa: BLE001
            continue
    print("master nets: %d" % len(nets_by_name))

    added = skipped = unmatched = 0
    for t in tracks:
        try:
            if t.get("kind") == "via":
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(t["x1"]),
                                                pcbnew.FromMM(t["y1"])))
                via.SetWidth(pcbnew.FromMM(t["width"]))
                via.SetDrill(pcbnew.FromMM(t["drill"]))
                via.SetLayerPair(int(t["top"]), int(t["bottom"]))
                net = nets_by_name.get(t.get("netname"))
                if net is None:
                    unmatched += 1
                    continue
                via.SetNet(net)
                board.Add(via)
                added += 1
                continue
            seg = pcbnew.PCB_TRACK(board)
            seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(t["x1"]),
                                         pcbnew.FromMM(t["y1"])))
            seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(t["x2"]),
                                       pcbnew.FromMM(t["y2"])))
            seg.SetWidth(pcbnew.FromMM(t["width"]))
            # Accept both spellings: the block router emits "layer_id", but the
            # extractor used for the route-first copper emits "layer". A silent
            # key mismatch here skipped 2075 of 2194 segments and looked like a
            # successful merge of 119.
            seg.SetLayer(int(t.get("layer_id", t.get("layer"))))
            net = nets_by_name.get(t.get("netname"))
            if net is None:
                unmatched += 1
                continue
            seg.SetNet(net)
            board.Add(seg)
            added += 1
        except Exception as exc:                      # noqa: BLE001
            skipped += 1
            if skipped <= 3:
                print("  skip segment: %s" % exc)

    pcbnew.SaveBoard(out_path, board)
    after = len(list(board.GetTracks()))
    print("tracks before: %d, after: %d, added: %d, skipped: %d, unmatched net: %d"
          % (before, after, added, skipped, unmatched))
    print("wrote %s" % os.path.basename(out_path))
    return 0 if added else 1


if __name__ == "__main__":
    sys.exit(main())
