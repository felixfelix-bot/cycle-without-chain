#!/usr/bin/env python3
"""BOM completeness gate: every populated reference has a footprint and an MPN.

WHY THIS FILE WAS REWRITTEN
---------------------------
The first version read ``approved-mpns.json`` and checked that every *entry* had
a non-empty footprint. It passed. Then the exported netlist was inspected
directly:

    387 components, 143 with an EMPTY footprint field

The same 143 references the work was supposed to fix. The gate had been checking
the approved list, where the footprint had been filled in from the MPN table, and
never the artifact layout actually consumes. A footprint that exists only in an
approved list is not on the board.

That is a false green of exactly the kind this repo guards against elsewhere, and
it was committed as "PCB-03 CLOSED". This rewrite is the correction: the netlist
is the authority, and the approved list is checked *against* it.

WHAT IT CHECKS NOW, AND AGAINST WHAT
------------------------------------
1. **Netlist footprint present.** Every component in
   ``exports/powerboard-reva.net`` must carry a non-empty, library-qualified
   footprint. This is the check that was missing.
2. **Reference-set equality** between the netlist and the approved MPN list.
3. **One MPN per reference**, and no MPN shared across two different footprints.
4. **Every MPN declares a source and a provenance kind** (``datasheet`` or
   ``series``) — an unlabelled claim is not evidence.
5. **Footprint agreement**: where the approved list and the netlist both name a
   footprint they must match, or one was edited without the other.

WHAT THIS GATE DOES NOT DO
--------------------------
It does not verify that a claimed MPN exists, is in stock, or that its datasheet
says what the line claims. It enforces that the claim is *present, unique,
attributable and consistent with the netlist*. A passing gate is a complete BOM,
not a correct one.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NETLIST = HERE / "exports" / "powerboard-reva.net"
BOM_CSV = HERE / "review-bom.csv"
MPN_JSON = HERE / "approved-mpns.json"

UNFROZEN_MARKERS = ("candidate", "provisional", "tbd", "tba", "to be decided",
                    "unqualified", "?")


def load_netlist(path: Path = NETLIST) -> dict[str, dict]:
    """Parse refs, values and footprints from a KiCad sexpr netlist."""
    if not path.is_file():
        raise FileNotFoundError(
            "netlist missing (run export_artifacts.py): %s" % path)
    text = path.read_text(encoding="utf-8")
    comps: dict[str, dict] = {}
    for m in re.finditer(r'\(comp \(ref "([^"]+)"\)(.*?)(?=\(comp \(ref |\Z)',
                         text, re.S):
        ref, body = m.group(1), m.group(2)
        fp = re.search(r'\(footprint "([^"]*)"\)', body)
        val = re.search(r'\(value "([^"]*)"\)', body)
        comps[ref] = {
            "footprint": (fp.group(1) if fp else "").strip(),
            "value": (val.group(1) if val else "").strip(),
        }
    if not comps:
        raise ValueError("netlist parsed to zero components; format changed?")
    return comps


def load_schematic_bom(path: Path = BOM_CSV) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_mpns(path: Path = MPN_JSON) -> dict:
    if not path.is_file():
        raise FileNotFoundError("approved MPN list missing: %s" % path)
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def is_unfrozen(value: str) -> bool:
    low = (value or "").lower()
    return any(m in low for m in UNFROZEN_MARKERS)


def check(netlist: dict[str, dict], bom: list[dict], mpns: dict) -> list[str]:
    """Return a list of failure strings; empty means pass."""
    fails: list[str] = []

    # 1. the netlist IS the board: an empty footprint cannot be laid out
    for ref, c in sorted(netlist.items()):
        fp = c["footprint"]
        if not fp:
            fails.append("%s: EMPTY footprint in the netlist" % ref)
        elif ":" not in fp:
            fails.append("%s: footprint %r is not library-qualified" % (ref, fp))

    approved = mpns.get("parts", {})

    # 2. reference-set equality, netlist vs approved list
    net_refs = set(netlist)
    mpn_refs = {k.strip() for k in approved}
    for ref in sorted(net_refs - mpn_refs):
        fails.append("in netlist but not in approved MPN list: %s" % ref)
    for ref in sorted(mpn_refs - net_refs):
        fails.append("approved MPN with no netlist reference: %s" % ref)

    # 3/4. per-entry completeness, against the netlist's own footprint
    seen: dict[str, str] = {}
    for ref, entry in sorted(approved.items()):
        mpn = (entry.get("mpn") or "").strip()
        footprint = (entry.get("footprint") or "").strip()
        source = (entry.get("source") or "").strip()
        kind = (entry.get("kind") or "").strip()
        if not mpn:
            fails.append("%s: no MPN" % ref)
        if not footprint:
            fails.append("%s: no footprint in the approved list" % ref)
        if not source:
            fails.append("%s: no source (datasheet or vendor reference)" % ref)
        if kind not in ("datasheet", "series"):
            fails.append("%s: kind %r is neither 'datasheet' nor 'series'"
                         % (ref, kind))
        if mpn:
            if mpn in seen:
                other_fp = (approved[seen[mpn]].get("footprint") or "").strip()
                if other_fp and footprint and other_fp != footprint:
                    fails.append(
                        "%s and %s share MPN %r on different footprints"
                        % (seen[mpn], ref, mpn))
            else:
                seen[mpn] = ref

    # 5. the two sources must agree
    for ref, entry in sorted(approved.items()):
        net_fp = (netlist.get(ref) or {}).get("footprint", "")
        app_fp = (entry.get("footprint") or "").strip()
        if net_fp and app_fp and net_fp != app_fp:
            fails.append("%s: netlist footprint %r != approved %r"
                         % (ref, net_fp, app_fp))

    # 6. unfrozen values: only a defect when the part is also un-pinned
    deferred = mpns.get("deferred", {})
    for ref, entry in sorted(approved.items()):
        value = entry.get("value") or ""
        if is_unfrozen(value) and not (entry.get("mpn") or "").strip():
            if ref in deferred:
                if not (deferred[ref] or "").strip():
                    fails.append("%s: deferred with no reason" % ref)
            else:
                fails.append("%s: value not frozen and no MPN: %r" % (ref, value))
    for ref in deferred:
        entry = approved.get(ref)
        if entry is None:
            fails.append("%s: deferred but not in the approved list" % ref)
        elif (entry.get("mpn") or "").strip():
            fails.append("%s: declared deferred but already has an MPN" % ref)

    return fails


def summary(netlist: dict[str, dict], mpns: dict) -> dict:
    """Separate what cannot be ordered from what is merely mislabelled."""
    approved = mpns.get("parts", {})
    deferred = set(mpns.get("deferred", {}))

    blank_net = sorted(r for r, c in netlist.items() if not c["footprint"])

    open_decisions, stale = [], []
    for ref, entry in sorted(approved.items()):
        if not is_unfrozen(entry.get("value") or ""):
            continue
        if (entry.get("mpn") or "").strip():
            stale.append(ref)
        elif ref not in deferred:
            open_decisions.append(ref)

    return {
        "netlist_components": len(netlist),
        "blank_footprints_in_netlist": len(blank_net),
        "blank_footprint_refs": blank_net,
        "approved_mpns": len(approved),
        "references_without_mpn": sum(
            1 for e in approved.values() if not (e.get("mpn") or "").strip()),
        "open_decisions": open_decisions,
        "stale_qualifiers": stale,
        "deferred": sorted(deferred),
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    as_json = "--json" in argv

    try:
        netlist = load_netlist()
        bom = load_schematic_bom()
        mpns = load_mpns()
    except (FileNotFoundError, ValueError) as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        return 2

    fails = check(netlist, bom, mpns)
    stats = summary(netlist, mpns)

    if as_json:
        print(json.dumps({"ok": not fails, "stats": stats, "failures": fails},
                         indent=1))
        return 1 if fails else 0

    print("components in netlist        : %d" % stats["netlist_components"])
    print("BLANK footprints in netlist : %d"
          % stats["blank_footprints_in_netlist"])
    print("references with approved MPN: %d" % stats["approved_mpns"])
    print("references without an MPN   : %d" % stats["references_without_mpn"])
    print("open decisions              : %d" % len(stats["open_decisions"]))
    print("declared deferred           : %d" % len(stats["deferred"]))
    print("stale qualifiers (cosmetic) : %d" % len(stats["stale_qualifiers"]))
    if stats["blank_footprint_refs"]:
        b = stats["blank_footprint_refs"]
        print("  blank footprint on: %s%s"
              % (", ".join(b[:20]), " ..." if len(b) > 20 else ""))
    print()

    if fails:
        print("FAIL: %d problem(s)" % len(fails))
        for f in fails[:40]:
            print("  - %s" % f)
        if len(fails) > 40:
            print("  ... and %d more" % (len(fails) - 40))
        return 1

    print("PASS: every netlist component has a library-qualified footprint, "
          "one MPN and a declared source; approved list and netlist agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
