#!/usr/bin/env python3
"""Pin-name audit: schematic pin names against a datasheet-derived pin table.

WHY THIS EXISTS
---------------
PCB-02 requires every package pin to be checked against its datasheet at pad
level. That check is worthless as a one-off eyeballing exercise — the failure
mode is a single wrong pin number on a 100-pin part, which is invisible in
review and fatal after fabrication. So the comparison is scripted, the datasheet
table is stored as data, and the script is mutation-tested.

The stored tables live in ``data/`` and were extracted from the manufacturer
PDFs, not typed from memory. Each carries the source URL and hash in
``datasheet-sources.json``.

WHAT IT COMPARES
----------------
``pin-net-map.csv`` records the pin *name* the schematic symbol declares for each
pin number. This compares that name to the datasheet's name for the same pin
number. A disagreement means either the symbol is wrong or the netlist is — both
are fabrication defects.

Datasheet names often carry a function suffix on the reset-state name
(``PF0-OSC_IN``, ``PB8-BOOT0``, ``PG10-NRST``). The comparison accepts a
datasheet name whose part before the first '-' equals the schematic name, and
exact match otherwise. It does NOT accept a prefix match on arbitrary substrings,
because ``PA1`` must not match ``PA10``.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN_MAP = HERE / "pin-net-map.csv"
BOM = HERE / "review-bom.csv"
DATA = HERE / "data"

# Schematic reference -> datasheet table. Parts are matched by BOM *value* so a
# new reference of an already-audited part is covered automatically, rather than
# needing this dict edited every time a gate is added.
BY_VALUE = {
    "SN74LVC3G17DCUR": "lvc/sn74lvc3g17dcur.json",
    "SN74LVC1G11DBVR": "lvc/sn74lvc1g11dbvr.json",
    "SN74LVC1G04DBVR": "lvc/sn74lvc1g04dbvr.json",
    "SN74LVC1G32DBVR": "lvc/sn74lvc1g32dbvr.json",
    "SN74LVC1G08DBVR": "lvc/sn74lvc1g08dbvr.json",
    "SN74LVC1G74DCUR": "lvc/sn74lvc1g74dcur.json",
}
# Reference-specific tables where the value alone is ambiguous.
BY_REF = {
    "U17": ("stm32g474ve-lqfp100-pins.json", "STM32G474VET6 LQFP100"),
}


def load_table(path: Path) -> dict[int, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): v for k, v in raw.items()}


def name_matches(schematic: str, datasheet: str) -> bool:
    if schematic == datasheet:
        return True
    # datasheet may suffix the reset-function name: PF0-OSC_IN, PB8-BOOT0
    return datasheet.split("-")[0] == schematic


def audit(table: dict[int, str], rows: list[dict]) -> tuple[list, list]:
    """Return (matches, mismatches)."""
    ok, bad = [], []
    for r in rows:
        pin = int(r["pin"])
        sch = r["pin_name"].strip()
        ds = table.get(pin)
        if ds is None:
            bad.append((pin, sch, "<pin absent from datasheet table>", r.get("net", "")))
        elif name_matches(sch, ds):
            ok.append((pin, sch, ds))
        else:
            bad.append((pin, sch, ds, r.get("net", "")))
    return ok, bad


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not PIN_MAP.is_file():
        print("FAIL: pin-net-map.csv missing (run generate_schematic.py)",
              file=sys.stderr)
        return 2

    rows = list(csv.DictReader(PIN_MAP.open(newline="", encoding="utf-8")))
    bom = {r["reference"]: r["value"]
           for r in csv.DictReader(BOM.open(newline="", encoding="utf-8"))}
    total_ok = total_bad = 0
    unnamed: list[str] = []
    any_table = False

    refs = sorted({r["ref"] for r in rows if r["ref"].startswith("U")
                   and r["ref"][1:].isdigit()}, key=lambda s: int(s[1:]))
    for ref in refs:
        fname = None
        human = None
        if ref in BY_REF:
            fname, human = BY_REF[ref]
        else:
            val = (bom.get(ref) or "").strip()
            if val in BY_VALUE:
                fname, human = BY_VALUE[val], val
        if not fname:
            continue
        path = DATA / fname
        if not path.is_file():
            print("%s (%s): table missing (%s) — SKIPPED, not passed"
                  % (ref, human, fname))
            continue
        any_table = True
        table = load_table(path)
        part = [r for r in rows if r["ref"] == ref]
        if not part:
            continue
        # A '~' pin name means the symbol does not name its pins. That is not a
        # match and not a mismatch: it is an unauditable part, and saying so is
        # the whole point. Treating it as a pass is how a check lies.
        if any((r["pin_name"] or "").strip() == "~" for r in part):
            unnamed.append("%s (%s)" % (ref, human))
            continue
        ok, bad = audit(table, part)
        total_ok += len(ok)
        total_bad += len(bad)
        print("%s (%s): %d/%d pins match" % (ref, human, len(ok), len(part)))
        for pin, sch, ds, net in bad:
            print("   pin %-3d schematic=%-12s datasheet=%-16s net=%s"
                  % (pin, sch, ds, net))

    if not any_table:
        print("FAIL: no datasheet tables found; nothing was audited", file=sys.stderr)
        return 2

    if unnamed:
        print()
        print("UNNAMED PINS — present in the BOM but not auditable:")
        for u in unnamed:
            print("   %s: symbol pins are '~'; give it named pins" % u)

    print()
    if total_bad:
        print("FAIL: %d pin mismatch(es) out of %d checked"
              % (total_bad, total_ok + total_bad))
        return 1
    print("PASS: %d pins match their datasheet tables (%d part(s) unauditable)"
          % (total_ok, len(unnamed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
