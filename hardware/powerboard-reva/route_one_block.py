#!/usr/bin/python3
"""Route ONE block of the board and write its tracks as JSON.

Runs in its own process, because pcbnew/swig state does not survive repeated
board operations: after tracks are added to a board, or after
ImportSpecctraSES runs, every other BOARD reference in the same interpreter
degrades to a bare SwigPyObject. One process per block is the only arrangement
that stayed reliable.

Usage: route_one_block.py <block-name> <master.kicad_pcb> <workdir> <out.json>
Writes {"block":..., "parts":N, "tracks":[{...}], "status":"ok"|"skip"|"fail"}
"""
import json
import os
import subprocess
import sys

import pcbnew

JAR = "/opt/freerouting/freerouting-2.5.0.jar"


def main() -> int:
    if len(sys.argv) != 6:
        print("usage: route_one_block.py <block> <master> <workdir> <out.json> <members.json>")
        return 2
    block, master_path, workdir, out_path, members_path = sys.argv[1:6]

    # DO NOT import gen_pcb here. gen_pcb calls pcbnew.FootprintLoad, and that
    # followed by ImportSpecctraSES in the same interpreter leaves every BOARD
    # reference as a bare SwigPyObject -- GetTracks() then fails even on a board
    # freshly LoadBoard()ed after the import. Membership is computed by the
    # parent and passed in as JSON; this process only loads, routes, imports,
    # reads tracks, and exits.
    members = set(json.load(open(members_path, encoding="utf-8")))
    if not members:
        json.dump({"block": block, "parts": 0, "tracks": [], "status": "skip",
                   "why": "no parts"}, open(out_path, "w"))
        return 0
    if len(members) > 120:
        # Measured limit: above ~120 parts a single pass stops finishing.
        json.dump({"block": block, "parts": len(members), "tracks": [],
                   "status": "skip", "why": "over 120 parts"}, open(out_path, "w"))
        return 0

    board = pcbnew.LoadBoard(master_path)
    for fp in list(board.GetFootprints()):
        if fp.GetReference() not in members:
            board.Remove(fp)
    sub_path = os.path.join(workdir, "%s.kicad_pcb" % block)
    dsn = os.path.join(workdir, "%s.dsn" % block)
    ses = os.path.join(workdir, "%s.ses" % block)
    pcbnew.SaveBoard(sub_path, board)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        json.dump({"block": block, "parts": len(members), "tracks": [],
                   "status": "fail", "why": "dsn"}, open(out_path, "w"))
        return 1

    cmd = ["java", "-Xmx5g", "-Djava.awt.headless=true", "-jar", JAR,
           "--gui.enabled=false", "-de", dsn, "-do", ses, "-mp", "10"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        json.dump({"block": block, "parts": len(members), "tracks": [],
                   "status": "fail", "why": "timeout"}, open(out_path, "w"))
        return 1
    if not os.path.exists(ses):
        json.dump({"block": block, "parts": len(members), "tracks": [],
                   "status": "fail", "why": "no ses rc=%d" % r.returncode},
                  open(out_path, "w"))
        return 1

    # Import in a CHILD process, read in ANOTHER child process.
    #
    # ImportSpecctraSES poisons the interpreter that runs it: afterwards every
    # BOARD reference in that process -- including one freshly LoadBoard()ed from
    # the file it just wrote -- is a bare SwigPyObject and GetTracks() raises
    # AttributeError. The import and the save both succeed; only reading in the
    # same process fails. Verified: a fresh interpreter reads the imported file
    # normally, which is why the read is a separate exec.
    here = os.path.dirname(os.path.abspath(__file__))
    imp = subprocess.run([sys.executable, os.path.join(here, "import_ses.py"),
                          sub_path, ses], capture_output=True, text=True,
                         timeout=300)
    if imp.returncode != 0:
        json.dump({"block": block, "parts": len(members), "tracks": [],
                   "status": "fail", "why": "import"}, open(out_path, "w"))
        return 1
    tracks_json = os.path.join(workdir, "%s.tracks.json" % block)
    rd = subprocess.run([sys.executable, os.path.join(here, "read_tracks.py"),
                         sub_path, tracks_json], capture_output=True, text=True,
                        timeout=300)
    if rd.returncode != 0 or not os.path.exists(tracks_json):
        json.dump({"block": block, "parts": len(members), "tracks": [],
                   "status": "fail", "why": "read"}, open(out_path, "w"))
        return 1
    tracks = json.load(open(tracks_json, encoding="utf-8"))
    json.dump({"block": block, "parts": len(members), "tracks": tracks,
               "status": "ok"}, open(out_path, "w"))
    print("%s: %d parts, %d tracks" % (block, len(members), len(tracks)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
