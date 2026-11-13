#!/usr/bin/python3
"""Route the inter-block nets FIRST, on a board with no block copper.

WHY THIS EXISTS
---------------
The block-routing pass consumed the space the inter-block nets needed. Measured
on the merged board: only 14 of 57 escape pads could be fan-out, the other 43
blocked by the 2708 tracks already routed through the pin fields. Three separate
attempts (blind, checked, gap-fill) all arrived at the same wall from different
directions, which is why the fix is an ordering change rather than a router fix.

So: take the placed-but-unrouted board, delete every track, keep only the
inter-block nets as connection targets, route them, and let the block pass run
afterwards around that copper. The inter-block nets get the space they need
because nothing else has claimed it yet.

WHAT THIS DOES NOT DO
---------------------
* It does not route the GEN/HUB power stages. Those are hand layout by intent.
* It does not claim the result is complete routing. It claims the inter-block
  nets are routed and the block pass can follow.
* It does not touch the placed board on disk; everything lands in routing/first/.

Usage: /usr/bin/python3 route_first.py [--timeout S] [--out NAME]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "powerboard-reva.kicad_pcb")
WORK = os.path.join(HERE, "routing", "first")
PY = "/usr/bin/python3"
# freerouting is a shell wrapper (ansible role 81-kicad-headless), not a jar:
# /usr/bin/java -jar <wrapper> fails with "Invalid or corrupt jarfile". The
# wrapper already supplies the real jar and --gui.enabled=false.
ROUTER = "/usr/local/bin/freerouting"

# The inter-block nets, from the DRC split. Listed explicitly rather than
# derived from a block definition, so a change in block boundaries cannot
# silently widen or narrow the routing scope.
NETS = [
    "DRV_MOSI", "DRV_SCK", "DRV_MISO",
    "GEN_INHA", "GEN_INHB", "GEN_INHC", "GEN_INLA", "GEN_INLB", "GEN_INLC",
    "HUB_INHA", "HUB_INHB", "HUB_INHC", "HUB_INLA", "HUB_INLB", "HUB_INLC",
    "GEN_SOB", "GEN_SOC", "HUB_SOA_ADC", "HUB_SOB_ADC", "HUB_SOC_ADC",
    "OC_HIGH_REF", "OC_LOW_REF",
    "GEN_HALL_1", "GEN_HALL_2", "GEN_HALL_3",
    "HUB_HALL_1", "HUB_HALL_2", "HUB_HALL_3",
    "ENC_A", "ENC_B", "LEFT_FSR_ADC", "RIGHT_FSR_ADC",
    "OC_OK", "MCU_ARM", "ARM_CLEAN", "RESET_REQUEST", "WDI",
    "TIMER_BREAK_OK", "FSR_SAMPLE_ENABLE", "BRAKE_DUMP_PWM",
]

_PREP = r'''
import sys, pcbnew
src, dst, nets_csv = sys.argv[1], sys.argv[2], sys.argv[3]
keep = set(n for n in nets_csv.split(",") if n)
board = pcbnew.LoadBoard(src)
if board is None:
    print("FATAL: could not load", src); sys.exit(1)

# Clear non-target pads BEFORE touching anything else: mutating a board
# invalidates other handles in the process (see prepare_interblock2.py).
kept = cleared = 0
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

# Delete all copper. The base board has none, but be explicit so this cannot
# silently inherit a routed input and produce a meaningless result.
removed = 0
for t in list(board.GetTracks()):
    board.Remove(t)
    removed += 1

pcbnew.SaveBoard(dst, board)
print("PREP kept=%d cleared=%d tracks_removed=%d" % (kept, cleared, removed))
'''

_DSN = r'''
import sys, pcbnew
src, dsn = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(src)
if board is None:
    print("FATAL: could not load", src); sys.exit(1)
ok = pcbnew.ExportSpecctraDSN(board, dsn)
print("DSN ok=%s" % ok)
sys.exit(0 if ok else 1)
'''

_IMPORT = r'''
import sys, pcbnew
board_path, ses_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
board = pcbnew.LoadBoard(board_path)
if board is None:
    print("FATAL: could not load", board_path); sys.exit(1)
ok = pcbnew.ImportSpecctraSES(board, ses_path)
pcbnew.SaveBoard(out_path, board)
print("IMPORT ok=%s" % ok)
sys.exit(0 if ok else 1)
'''

_READ = r'''
import sys, json, collections, pcbnew
path, out = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(path)
if board is None:
    print("FATAL: could not load", path); sys.exit(1)
per = collections.Counter()
nets = collections.Counter()
for t in board.GetTracks():
    per[board.GetLayerName(t.GetLayer())] += 1
    if t.GetNetname():
        nets[t.GetNetname()] += 1
try:
    unconnected = board.GetConnectivity().GetUnconnectedCount(False)
except Exception:
    unconnected = None
json.dump({"tracks_per_layer": dict(per), "tracks_per_net": dict(nets),
           "total_tracks": sum(per.values()), "unconnected": unconnected},
          open(out, "w"), indent=1)
print("READ", sum(per.values()), "tracks, unconnected", unconnected)
'''


def sh(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", default="powerboard-reva-first.kicad_pcb")
    args = ap.parse_args()

    os.makedirs(WORK, exist_ok=True)
    sub = os.path.join(WORK, "interblock-only.kicad_pcb")
    dsn = os.path.join(WORK, "interblock-only.dsn")
    ses = os.path.join(WORK, "interblock-only.ses")
    routed = os.path.join(WORK, "interblock-only-routed.kicad_pcb")
    stats = os.path.join(WORK, "interblock-only-stats.json")
    final = os.path.join(HERE, args.out)

    if not os.path.exists(BASE):
        print("FATAL: no base board at", BASE)
        return 1

    print("== 1. restrict the bare board to %d inter-block nets" % len(NETS))
    r = sh([PY, "-c", _PREP, BASE, sub, ",".join(NETS)])
    print(r.stdout.strip() or r.stderr[-600:])
    if r.returncode != 0:
        return 1

    print("== 2. export DSN")
    r = sh([PY, "-c", _DSN, sub, dsn])
    print(r.stdout.strip() or r.stderr[-400:])
    if r.returncode != 0:
        return 1

    print("== 3. route with freerouting (timeout %ds)" % args.timeout)
    for f in (ses,):
        if os.path.exists(f):
            os.remove(f)
    try:
        rr = sh([ROUTER, "-de", dsn, "-do", ses, "-mp", "10"],
                timeout=args.timeout)
        print("   freerouting rc=%d" % rr.returncode)
        tail = [l for l in (rr.stdout or "").splitlines() if l.strip()][-6:]
        for l in tail:
            print("   ", l[:110])
    except subprocess.TimeoutExpired:
        print("   TIMEOUT after %ds -- no session file will exist" % args.timeout)
        return 1

    if not os.path.exists(ses):
        print("FATAL: freerouting produced no session file")
        return 1

    print("== 4. import the session")
    r = sh([PY, "-c", _IMPORT, sub, ses, routed])
    print(r.stdout.strip() or r.stderr[-400:])
    if r.returncode != 0:
        return 1

    print("== 5. measure")
    r = sh([PY, "-c", _READ, routed, stats])
    print(r.stdout.strip() or r.stderr[-300:])

    data = json.load(open(stats, encoding="utf-8"))
    done = len(data["tracks_per_net"])
    print()
    print("   nets routed:      %d of %d" % (done, len(NETS)))
    print("   total tracks:     %d" % data["total_tracks"])
    print("   per layer:        %s" % data["tracks_per_layer"])
    print("   unconnected:      %s  (this counts ALL board nets, most of which"
          " are not in scope here)" % data["unconnected"])

    # The deliverable is the inter-block copper, to be merged onto the placed
    # board before block routing runs.
    import shutil
    shutil.copyfile(routed, final)
    print()
    print("   wrote %s" % final)
    print("   next: block routing runs AFTER this copper, not before")
    return 0


if __name__ == "__main__":
    sys.exit(main())
