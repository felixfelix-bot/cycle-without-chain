#!/usr/bin/env python3
"""Orchestrate block-by-block routing and harvest the tracks.

WHY BLOCK ROUTING
-----------------
A single-shot full-board autoroute does not finish at this size. Measured:

    12 parts   routed, 0 incomplete, 0 clearance      5.21 s
    80 parts   routed, 0 incomplete, 0 clearance   2 min 45 s
   397 parts   no session file, four attempts     > 20 min each

So the board is routed one functional block at a time.

WHY THIS PROCESS TOUCHES NO PCB LIBRARY
---------------------------------------
pcbnew/swig state does not survive repeated board operations in one interpreter.
Observed, in order, while building this:

  * after ImportSpecctraSES, the board handed to it becomes a bare SwigPyObject
  * re-LoadBoard()ing does not help -- the damage is interpreter-wide, not
    per-variable
  * after tracks are added to a board, footprint handles degrade too, so even
    GetPosition() on the NEXT block's footprint fails
  * iterating GetNetInfo()/GetLayerName() on a corrupted board segfaults (139)

Each time, "one more board operation in the same process" failed. So this file is
pure orchestration: it shells out to route_one_block.py once per block (clean
process each time), reads JSON, and never imports pcbnew.

Power stages are deliberately NOT autorouted. The GEN/HUB bridges, their
gate-drive loops and the shunt sense paths need hand layout: that copper geometry
is exactly what the OC-03 envelope and the gate-resistor sizing assume, and an
autorouter is least likely to get it right.

Usage: python3 route_board_blocks.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MASTER = os.path.join(HERE, "powerboard-reva.kicad_pcb")
WORK = os.path.join(HERE, "routing", "blocks")
PY = "/usr/bin/python3"

BLOCKS = [
    "mcu", "analog_filter", "fault_logic", "gen_sense", "hub_sense",
    "oc_window", "ov_chopper", "brake_left", "brake_right", "hall",
    "fsr_left", "fsr_right", "aux_supply", "rail_partition", "brake_chopper",
]


def block_members() -> dict[str, list[str]]:
    """Which references belong to each block, computed WITHOUT any board ops.

    gen_pcb gives the region rectangles and the sheet-to-block mapping, so the
    routing script cannot disagree with the placement about where a block is.
    This runs in the parent, which never loads a board -- importing gen_pcb calls
    pcbnew.FootprintLoad, and that plus a later ImportSpecctraSES in the same
    interpreter is what corrupted the children.
    """
    sys.path.insert(0, HERE)
    import gen_pcb as g

    text = open(os.path.join(HERE, "exports", "powerboard-reva.net"),
                encoding="utf-8").read()
    comps = g.parse_comps(text)
    sheets = g.sheet_of(text)
    for c in comps:
        c["region"] = g.region_for(c["ref"], sheets)
        w, h = g.footprint_size(c["footprint"])
        c["area"] = w * h
    return {b: [c["ref"] for c in comps if c["region"] == b] for b in BLOCKS}


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    members = block_members()
    results = []
    for block in BLOCKS:
        out = os.path.join(WORK, "%s.json" % block)
        if os.path.exists(out):
            os.remove(out)
        members_json = os.path.join(WORK, "%s.members.json" % block)
        with open(members_json, "w", encoding="utf-8") as fh:
            json.dump(members.get(block, []), fh)
        try:
            r = subprocess.run([PY, os.path.join(HERE, "route_one_block.py"),
                                block, MASTER, WORK, out, members_json],
                               capture_output=True, text=True, timeout=1200)
        except subprocess.TimeoutExpired:
            print("%-16s TIMEOUT" % block)
            results.append({"block": block, "status": "fail",
                            "tracks": [], "parts": 0, "why": "timeout"})
            continue
        if not os.path.exists(out):
            print("%-16s FAIL process: %s"
                  % (block, (r.stderr or "").strip()[-160:]))
            results.append({"block": block, "status": "fail",
                            "tracks": [], "parts": 0, "why": "process"})
            continue
        data = json.load(open(out, encoding="utf-8"))
        results.append(data)
        if data["status"] == "ok":
            print("%-16s %3d parts  %4d tracks"
                  % (block, data["parts"], len(data["tracks"])))
        else:
            print("%-16s %3d parts  %s%s"
                  % (block, data["parts"], data["status"].upper(),
                     " (%s)" % data["why"] if data.get("why") else ""))

    ok = [d for d in results if d["status"] == "ok"]
    total = sum(len(d["tracks"]) for d in ok)
    print()
    print("blocks routed: %d of %d attempts, %d track segments harvested"
          % (len(ok), len(BLOCKS), total))
    if not total:
        print("FAIL: nothing routed; nothing to merge")
        return 1

    merged = os.path.join(WORK, "all-tracks.json")
    with open(merged, "w", encoding="utf-8") as fh:
        json.dump([t for d in ok for t in d["tracks"]], fh)
    print("wrote %s (%d segments)" % (merged, total))
    print()
    print("Power stages (GEN/HUB bridges, drivers) deliberately NOT routed.")
    print("Inter-block connections are NOT joined; they remain unconnected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
