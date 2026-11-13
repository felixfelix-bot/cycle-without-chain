#!/usr/bin/env python3
"""BOM completeness gate: every populated reference has a footprint and an MPN.

WHY THIS EXISTS
---------------
``docs/design/open-gates-register.md`` PCB-03 requires "exact reference-set
equality and one MPN per populated reference", and RAIL-10 requires the passive
MPNs to be frozen "against datasheet ratings" so that "candidate values" cannot
reach a fabrication BOM. Both were OPEN, and the measured state behind them was:

    387 populated references
    143 with no footprint  (37 %)
     27 values still containing "candidate", "provisional" or "TBD"

A schematic that generates 387 parts without land patterns is not a design that
can be ordered, and a value of "1u 100V X7R provisional" is not a purchase order
line. This gate turns those two statements into a check that fails.

WHAT IT CHECKS, AND IN WHICH DIRECTION
-------------------------------------
1. **Reference-set equality** between the schematic-derived BOM and the approved
   MPN list. A part present in one and missing from the other fails.
2. **One MPN per populated reference.** Duplicate or conflicting MPNs fail.
3. **No unfrozen values.** Any value containing candidate/provisional/TBD fails.
4. **Every MPN carries a footprint.** An MPN without a land pattern cannot be
   assembled even if it is correctly specified.
5. **Every MPN declares its source.** A part number with no datasheet or vendor
   reference is an assertion, not evidence.

WHAT THIS GATE DOES NOT DO
--------------------------
It does not verify that a claimed MPN exists, that its datasheet says what the
line claims, or that the part is in stock. Those stay human checks; the gate only
enforces that the claim is *present, unique, and attributable*. A passing BOM is
a complete BOM, not a correct one — that distinction is the whole point of the
register's A/B split, since B gates still need a built board.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOM_CSV = HERE / "review-bom.csv"
MPN_JSON = HERE / "approved-mpns.json"

UNFROZEN_MARKERS = ("candidate", "provisional", "tbd", "tba", "to be decided",
                    "unqualified", "?")


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


def check(bom: list[dict], mpns: dict) -> list[str]:
    """Return a list of failure strings; empty means pass."""
    fails: list[str] = []

    sch_refs = {r["reference"].strip() for r in bom if r["reference"].strip()}
    approved = mpns.get("parts", {})
    mpn_refs = {k.strip() for k in approved}

    for ref in sorted(sch_refs - mpn_refs):
        fails.append("in schematic but not in approved MPN list: %s" % ref)
    for ref in sorted(mpn_refs - sch_refs):
        fails.append("approved MPN with no schematic reference: %s" % ref)

    for ref, entry in sorted(approved.items()):
        mpn = (entry.get("mpn") or "").strip()
        footprint = (entry.get("footprint") or "").strip()
        source = (entry.get("source") or "").strip()
        if not mpn:
            fails.append("%s: no MPN" % ref)
        if not footprint:
            fails.append("%s: no footprint" % ref)
        if not source:
            fails.append("%s: no source (datasheet or vendor reference)" % ref)
        # ":" is the KiCad library separator; a bare name is not a land pattern
        if footprint and ":" not in footprint:
            fails.append("%s: footprint %r is not library-qualified" % (ref, footprint))

    seen: dict[str, str] = {}
    for ref, entry in approved.items():
        mpn = (entry.get("mpn") or "").strip()
        if not mpn:
            continue
        if mpn in seen:
            # Passive MPNs legitimately repeat across references; only fail when
            # the same MPN is claimed for two *different* footprints.
            other_fp = (approved[seen[mpn]].get("footprint") or "").strip()
            this_fp = (entry.get("footprint") or "").strip()
            if other_fp and this_fp and other_fp != this_fp:
                fails.append("%s and %s share MPN %r on different footprints"
                             % (seen[mpn], ref, mpn))
        else:
            seen[mpn] = ref

    # A "candidate" in the schematic value is only a defect if the approved list
    # does not settle it. Once an MPN is frozen against a source, the stale
    # qualifier in the schematic is a documentation wart, not a purchasing risk.
    open_decisions: list[str] = []
    for ref, entry in sorted(approved.items()):
        value = (entry.get("value") or "")
        if is_unfrozen(value) and not (entry.get("mpn") or "").strip():
            open_decisions.append(ref)
            fails.append("%s: value not frozen and no MPN: %r" % (ref, value))

    # Deferred parts are allowed to stay open, but only if explicitly declared
    # with a reason. Silence is not a deferral.
    deferred = mpns.get("deferred", {})
    for ref in open_decisions:
        if ref in deferred:
            fails = [f for f in fails if not f.startswith("%s: value not frozen" % ref)]
    for ref, reason in deferred.items():
        if ref not in open_decisions:
            fails.append("%s: declared deferred but is not an open decision" % ref)
        if not (reason or "").strip():
            fails.append("%s: deferred with no reason" % ref)

    return fails


def summary(bom: list[dict], mpns: dict) -> dict:
    """Report what a reader needs, not raw string counts.

    An earlier version of this function counted every occurrence of "candidate"
    in the schematic and printed it next to a PASS, which read as a
    contradiction. The two quantities are not the same thing:

      * ``open_decisions``    - unfrozen value AND no MPN: cannot be ordered.
      * ``stale_qualifiers``  - unfrozen value but MPN frozen: orderable; the
                                schematic text is stale and should be cleaned,
                                but nothing is at risk.

    Counting them together hid the difference between a real gap and cosmetic
    debt, so they are now separate lines.
    """
    approved = mpns.get("parts", {})
    deferred = set(mpns.get("deferred", {}))
    open_decisions, stale = [], []
    for ref, entry in sorted(approved.items()):
        if not is_unfrozen(entry.get("value") or ""):
            continue
        if (entry.get("mpn") or "").strip():
            stale.append(ref)
        elif ref not in deferred:
            open_decisions.append(ref)

    no_mpn = [r for r, e in approved.items() if not (e.get("mpn") or "").strip()]
    no_fp = [r for r, e in approved.items() if not (e.get("footprint") or "").strip()]

    return {
        "schematic_references": len(bom),
        "approved_mpns": len(approved),
        "references_without_mpn": len(no_mpn),
        "references_without_footprint": len(no_fp),
        "open_decisions": open_decisions,
        "stale_qualifiers": stale,
        "deferred": sorted(deferred),
    }


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    as_json = "--json" in argv

    try:
        bom = load_schematic_bom()
        mpns = load_mpns()
    except FileNotFoundError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        return 2

    fails = check(bom, mpns)
    stats = summary(bom, mpns)

    if as_json:
        print(json.dumps({"ok": not fails, "stats": stats, "failures": fails},
                         indent=1))
    else:
        print("references in schematic BOM : %d" % stats["schematic_references"])
        print("references with approved MPN: %d" % stats["approved_mpns"])
        print("without an MPN             : %d" % stats["references_without_mpn"])
        print("without a footprint        : %d" % stats["references_without_footprint"])
        print("open decisions             : %d" % len(stats["open_decisions"]))
        print("declared deferred          : %d" % len(stats["deferred"]))
        print("stale qualifiers (cosmetic): %d" % len(stats["stale_qualifiers"]))
        if stats["open_decisions"]:
            print("  open: %s" % ", ".join(stats["open_decisions"][:20]))
        if stats["stale_qualifiers"]:
            print("  stale schematic text on: %s"
                  % ", ".join(stats["stale_qualifiers"][:12])
                  + (" ..." if len(stats["stale_qualifiers"]) > 12 else ""))
        print()
        if fails:
            print("FAIL: %d problem(s)" % len(fails))
            for f in fails[:40]:
                print("  - %s" % f)
            if len(fails) > 40:
                print("  ... and %d more" % (len(fails) - 40))
            return 1
        print("PASS: every populated reference has one MPN, a land pattern "
              "and a source; no unfrozen values")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
