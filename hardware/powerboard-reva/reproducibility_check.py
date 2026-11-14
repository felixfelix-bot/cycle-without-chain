#!/usr/bin/python3
"""Two-build reproducibility check for the schematic and PCB generators.

WHY THIS EXISTS (PCB-07)
------------------------
PCB-07 asks whether the generators "reproduce byte-identically" and names
deterministic identifiers as the remedy, because "the audited upstream pipeline
replaced placeholder UUIDs with UUID4". The claim has never been tested by running
the generators twice and comparing the bytes. This does that.

WHAT IT MEASURES
----------------
Each artifact is generated in two separate scratch trees and compared two ways:

  1. BYTE IDENTITY -- cmp. This is the gate's own wording.
  2. STRUCTURAL IDENTITY -- after stripping uuid fields and normalising the
     ordering-insensitive parts, is the CONTENT the same? This distinguishes
     "same board, different random ids" from "a genuinely different board",
     which is the difference between a fixable determinism gap and a real
     non-determinism bug.

The distinction matters. If only uuid text differs, the geometry, placement and
netlist binding are reproducible and only the identifiers need deriving. If the
geometry differs, two builds of the same input produce different boards, which is
a much worse defect.

Usage: reproducibilty_check.py [workdir]
Exit 0 when both artifacts are byte-identical, 1 otherwise.
"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = "/usr/bin/python3"          # pcbnew is only installed for system python
CARRY = ("generate_schematic.py", "gen_pcb.py", "fp-lib-table",
         "powerboard-reva.kicad_dru", "Powerboard.pretty", "exports")


def stage(dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    os.makedirs(dst)
    for name in CARRY:
        src = os.path.join(HERE, name)
        if not os.path.exists(src):
            continue
        target = os.path.join(dst, name)
        if os.path.isdir(src):
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)
    # the generator reads approved-mpns.json and the review CSV
    for name in os.listdir(HERE):
        if name.endswith((".json", ".csv", ".py")) and not os.path.exists(
                os.path.join(dst, name)):
            src = os.path.join(HERE, name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(dst, name))


def run(cwd, script, log):
    r = subprocess.run([PY, script], cwd=cwd, capture_output=True, text=True,
                       timeout=900)
    with open(log, "w") as f:
        f.write(r.stdout + r.stderr)
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else ""


def strip_uuids(text):
    text = re.sub(r'\(uuid "[^"]*"\)', '(uuid "")', text)
    text = re.sub(r'\(uuid [0-9a-fA-F-]{36}\)', '(uuid "")', text)
    text = re.sub(r'"uuid": "[^"]*"', '"uuid": ""', text)
    return text


def main():
    workdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/repro"
    a = os.path.join(workdir, "a")
    b = os.path.join(workdir, "b")
    print("staging two trees under %s" % workdir)
    stage(a)
    stage(b)

    results = {}
    for script, artifact in (("generate_schematic.py", "powerboard-reva.kicad_sch"),
                             ("gen_pcb.py", "powerboard-reva.kicad_pcb")):
        print("\n== %s" % script)
        ra, la = run(a, script, os.path.join(workdir, script + ".a.log"))
        rb, lb = run(b, script, os.path.join(workdir, script + ".b.log"))
        print("   run A rc=%d  %s" % (ra, la))
        print("   run B rc=%d  %s" % (rb, lb))
        if ra != 0 or rb != 0:
            results[artifact] = ("ERROR", "generator failed")
            continue
        pa = os.path.join(a, artifact)
        pb = os.path.join(b, artifact)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            results[artifact] = ("MISSING", "artifact not produced")
            continue
        ba = open(pa, 'rb').read()
        bb = open(pb, 'rb').read()
        if ba == bb:
            print("   bytes: IDENTICAL (%d bytes)" % len(ba))
            results[artifact] = ("BYTE-IDENTICAL", "%d bytes" % len(ba))
            continue
        print("   bytes: DIFFER (%d vs %d)" % (len(ba), len(bb)))
        ta = strip_uuids(ba.decode('utf-8', 'replace'))
        tb = strip_uuids(bb.decode('utf-8', 'replace'))
        if ta == tb:
            nu = len(re.findall(r'uuid "[^"]+"', ba.decode('utf-8', 'replace')))
            print("   content: IDENTICAL once uuid fields are blanked "
                  "(%d uuid fields differ)" % nu)
            results[artifact] = ("UUID-ONLY", "%d uuid fields" % nu)
        else:
            # count differing lines to size the real difference
            la_ = ta.splitlines()
            lb_ = tb.splitlines()
            diff = sum(1 for x, y in zip(la_, lb_) if x != y)
            diff += abs(len(la_) - len(lb_))
            print("   content: DIFFERS -- %d of %d lines differ after blanking uuids"
                  % (diff, max(len(la_), len(lb_))))
            results[artifact] = ("CONTENT-DIFFERS", "%d lines" % diff)

    print("\n== PCB-07 verdict")
    ok = True
    for art, (verdict, detail) in results.items():
        print("   %-24s %-16s %s" % (art, verdict, detail))
        if verdict != "BYTE-IDENTICAL":
            ok = False
    print("\n   %s" % ("PASS: both artifacts reproduce byte-identically"
                       if ok else
                       "FAIL: byte-identical reproduction is NOT achieved. "
                       "PCB-07 remains OPEN."))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
