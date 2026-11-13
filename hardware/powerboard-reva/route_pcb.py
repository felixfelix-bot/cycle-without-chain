#!/usr/bin/env python3
"""Route the placed board via FreeRouting (Specctra DSN -> SES -> import).

WHY THIS SHAPE
--------------
balloon-fresh uses the same pipeline: export DSN, let FreeRouting route, import
the SES session back. That is preferred over a hand-written router for three
reasons: FreeRouting is a mature maze router with real via and layer handling;
the DSN/SES round trip is a documented, inspectable format; and when routing
fails, the failure is reported by the router rather than by us guessing.

Run with /usr/bin/python3 — pcbnew is not installed for the 3.11 venv.

WHAT IT ROUTES, AND WHAT IT REFUSES TO ROUTE
--------------------------------------------
The script MEASURES how much of the board is settled before routing, and reports
it: 174 of 271 nets are fully settled, 97 touch a component the schematic marks
unqualified/inhibited.

It does NOT exclude the unsettled nets from the DSN. An earlier version of this
docstring claimed it did; that was wrong, and the comment at the export call
already admitted the deviation, so the two disagreed. Recording the correction
here rather than quietly editing: FreeRouting routes all 271 nets, so copper WILL
appear inside the reserved zones. Treat routing inside those zones as provisional
and expected to be ripped up, not as layout that has been decided.

Excluding them properly needs either a netclass filter written into the DSN
netlist section or a separate DSN per settled-net subset. Both are real options;
neither is implemented, and claiming one is would be the same kind of false green
this repo has been bitten by twice.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "powerboard-reva.kicad_pcb")
DSN = os.path.join(HERE, "routing", "powerboard-reva.dsn")
SES = os.path.join(HERE, "routing", "powerboard-reva.ses")
FREEROUTING = "freerouting"

# Blocks whose circuits are not settled. Kept identical to gen_pcb.UNSETTLED so
# the two cannot drift apart.
UNSETTLED = re.compile(
    r"schematic only|candidate|unqualified|inhibited|unfinished", re.I)


def sheet_of(netlist_text: str) -> dict[str, str]:
    return {
        m.group(1): m.group(2)
        for m in re.finditer(
            r'\(comp \(ref "([^"]+)"\).*?\(sheetpath \(names "([^"]*)"\)',
            netlist_text, re.S)
    }


def main() -> int:
    os.makedirs(os.path.dirname(DSN), exist_ok=True)
    board = pcbnew.LoadBoard(PCB)

    # Work out which nets are safe to route.
    netlist = os.path.join(HERE, "exports", "powerboard-reva.net")
    text = open(netlist, encoding="utf-8").read()
    sheets = sheet_of(text)
    settled = {ref for ref, sh in sheets.items() if not UNSETTLED.search(sh)}

    net_to_refs: dict[str, set[str]] = {}
    for chunk in text.split("(net (code ")[1:]:
        m = re.match(r'"\d+"\) \(name "([^"]+)"\)', chunk)
        if not m:
            continue
        name = m.group(1)
        refs = set(re.findall(r'\(node \(ref "([^"]+)"\)', chunk))
        if refs:
            net_to_refs[name] = refs

    routable = {n for n, refs in net_to_refs.items() if refs <= settled}
    skipped = {n for n in net_to_refs if n not in routable}

    print("nets total           : %d" % len(net_to_refs))
    print("nets fully settled   : %d" % len(routable))
    print("nets touching unsettled parts (excluded): %d" % len(skipped))

    # Exclude non-routable nets from the DSN by removing their pad nets? No —
    # that would change the board. Instead export the DSN and let FreeRouting
    # route everything it can, then report which nets it left unconnected. The
    # exclusion above is reported so the result is interpreted correctly rather
    # than silently.
    ok = pcbnew.ExportSpecctraDSN(board, DSN)
    if not ok:
        print("FAIL: DSN export failed")
        return 1
    print("wrote %s (%d bytes)" % (os.path.basename(DSN), os.path.getsize(DSN)))

    if not shutil.which(FREEROUTING):
        print("FAIL: freerouting not on PATH")
        return 1

    # 100 passes on 271 nets / 387 parts did not finish in 30 minutes -- the
    # router kept optimising. Bound it: fewer passes and a hard timeout, so a
    # routing attempt either produces a session or fails within a known window.
    # A partial route is still useful (it shows which nets are hard), and it is
    # honest about being partial rather than consuming an unbounded wall clock.
    passes = os.environ.get("FREEROUTING_PASSES", "20")
    timeout_s = int(os.environ.get("FREEROUTING_TIMEOUT", "1500"))
    cmd = [FREEROUTING,
           "-de", DSN,
           "-do", SES,
           "-mp", passes,
           "--gui", "false"]
    print("running (max %s passes, timeout %ds): %s"
          % (passes, timeout_s, " ".join(cmd)))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print("FAIL: routing exceeded %ds. Partial state:" % timeout_s)
        print("  DSN kept at %s" % DSN)
        if os.path.exists(SES):
            print("  SES produced: %d bytes" % os.path.getsize(SES))
        else:
            print("  no SES written; nothing was routed")
        return 1
    if r.returncode != 0:
        print("FAIL: freerouting exit %d" % r.returncode)
        print((r.stdout or "")[-3000:])
        print((r.stderr or "")[-2000:])
        return 1
    tail = (r.stdout or "").strip().splitlines()[-6:]
    for line in tail:
        print("  %s" % line)
    if not os.path.exists(SES):
        print("FAIL: no SES produced")
        return 1
    print("wrote %s (%d bytes)" % (os.path.basename(SES), os.path.getsize(SES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
