#!/usr/bin/python3
"""Re-read already-routed block boards and rebuild all-tracks.json with net names.

The blocks were routed successfully; only the track hand-off was wrong (it
carried renumbered net codes). Those boards are still on disk in
routing/blocks/, so re-reading them is cheap -- no re-routing needed.

Usage: /usr/bin/python3 reharvest.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "routing", "blocks")

BLOCKS = [
    "mcu", "analog_filter", "fault_logic", "gen_sense", "hub_sense",
    "oc_window", "ov_chopper", "brake_left", "brake_right", "hall",
    "fsr_left", "fsr_right", "aux_supply", "rail_partition", "brake_chopper",
]


def main() -> int:
    all_tracks = []
    per_block = {}
    for block in BLOCKS:
        board = os.path.join(WORK, "%s.kicad_pcb" % block)
        out = os.path.join(WORK, "%s.tracks.json" % block)
        if not os.path.exists(board):
            continue
        r = subprocess.run([sys.executable, os.path.join(HERE, "read_tracks.py"),
                            board, out], capture_output=True, text=True,
                           timeout=300)
        if r.returncode != 0 or not os.path.exists(out):
            print("%-16s FAIL read: %s" % (block, (r.stderr or "")[-120:]))
            continue
        tracks = json.load(open(out, encoding="utf-8"))
        per_block[block] = len(tracks)
        all_tracks.extend(tracks)
        print("%-16s %4d tracks" % (block, len(tracks)))

    merged = os.path.join(WORK, "all-tracks.json")
    with open(merged, "w", encoding="utf-8") as fh:
        json.dump(all_tracks, fh)
    named = sum(1 for t in all_tracks if t.get("netname"))
    print()
    print("total %d segments, %d with a net name"
          % (len(all_tracks), named))
    if named != len(all_tracks):
        print("FAIL: %d segments have no net name and cannot be assigned"
              % (len(all_tracks) - named))
        return 1
    print("wrote %s" % merged)
    return 0


if __name__ == "__main__":
    sys.exit(main())
