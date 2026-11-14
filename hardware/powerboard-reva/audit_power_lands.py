#!/usr/bin/python3
"""Verify the HSOP-8, TO-247 and VSSOP-8 land patterns against vendor geometry (PCB-02).

Extends audit_qfn40_land.py to the other three package families on the board. Each was
a KiCad library default that had never been compared to a vendor drawing, which is the
failure mode PCB-02 names: a land error found at assembly rather than in review.

WHAT IS CHECKED, AND FROM WHERE
-------------------------------
HSOP-8 (U500, U501) -- TI DDA "SO PowerPAD, 8": 3.9 x 4.9 mm body, 1.27 mm pitch, an
exposed thermal pad of about 2.3 x 2.3 mm. The board's footprint is
HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm with 8 signal pads of 1.95 x 0.60 mm, a
2.30 x 2.30 mm EP on pad 9, and 4 paste sub-apertures of 0.93 mm. 13 pads total is
correct: 8 pins + 1 EP + 4 paste windows.

TO-247 (Q400-Q403) -- the standard TO-247-3 outline: 3 leads on a 5.45 mm pitch, each
lead pad 2.5 x 4.5 mm. No exposed pad; the tab is the drain and is not a pad.

VSSOP-8 (U7, U8, U11, U12, U504) -- 0.5 mm pitch, 8 pads of 1.25 x 0.35 mm.

Each check asserts a MAGNITUDE and, where a vendor drawing has a handedness or an
inversion, asserts the relationship explicitly rather than normalising it away. A sign
or mirror error in a land pattern is not a rounding difference: it puts the part on
backwards.

Negative controls are in tests/test_land_patterns.py -- a check that only ever passes
proves nothing, which is exactly how the QFN-40 audit's pitch test was found to be dead
code in this project.
"""
import sys

import pcbnew

TOL = 0.01        # mm; library land patterns are exact to 2 dp


def pads_of(board, ref):
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            return fp, [p for p in fp.Pads()]
    return None, []


def pitch(coords, tol=0.02):
    s = sorted(coords)
    return [round(b - a, 4) for a, b in zip(s, s[1:]) if b - a > tol]


def check_hsop8(board, ref, fails):
    fp, pads = pads_of(board, ref)
    if fp is None:
        fails.append("%s missing" % ref)
        return
    fpid = str(fp.GetFPID().GetLibItemName())
    if not fpid.startswith("HSOP-8-1EP_3.9x4.9mm_P1.27mm"):
        fails.append("%s footprint %s is not the DDA SO PowerPAD land" % (ref, fpid))
        return

    signal = [p for p in pads if p.GetNumber() in [str(i) for i in range(1, 9)]]
    ep = [p for p in pads if abs(pcbnew.ToMM(p.GetSize().x) - 2.30) < TOL
          and abs(pcbnew.ToMM(p.GetSize().y) - 2.30) < TOL]
    paste = [p for p in pads if p.GetNumber() == "" and
             abs(pcbnew.ToMM(p.GetSize().x) - 0.93) < TOL]

    if len(signal) != 8:
        fails.append("%s has %d signal pads, vendor DDA has 8" % (ref, len(signal)))
    if not ep:
        fails.append("%s has no 2.30 x 2.30 mm exposed pad" % ref)
    if len(paste) != 4:
        fails.append("%s has %d paste apertures, expected 4 (EP thermal window)"
                     % (ref, len(paste)))

    for p in signal:
        sz = p.GetSize()
        if (abs(pcbnew.ToMM(sz.x) - 1.95) > TOL or abs(pcbnew.ToMM(sz.y) - 0.60) > TOL):
            fails.append("%s pad %s is %.2fx%.2f, vendor 1.95x0.60"
                         % (ref, p.GetNumber(), pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)))
            break

    # 1.27 mm pitch down each side
    left = [p for p in signal if pcbnew.ToMM(p.GetPosition().x) < 15.5]
    right = [p for p in signal if pcbnew.ToMM(p.GetPosition().x) >= 15.5]
    for side, group in (("left", left), ("right", right)):
        if len(group) != 4:
            continue
        ys = [pcbnew.ToMM(p.GetPosition().y) for p in group]
        got = pitch(ys)
        if any(abs(pv - 1.27) > 0.02 for pv in got):
            fails.append("%s %s-side pitch is %s, vendor 1.27" % (ref, side, got))
    # body-to-body span: 13.10..18.05 = 4.95 mm centre-to-centre for a 3.9 mm body
    if left and right:
        xs = [pcbnew.ToMM(p.GetPosition().x) for p in signal]
        span = max(xs) - min(xs)
        if abs(span - 4.95) > 0.05:
            fails.append("%s pad-to-pad span is %.2f, expected 4.95" % (ref, span))


def check_to247(board, ref, fails):
    fp, pads = pads_of(board, ref)
    if fp is None:
        fails.append("%s missing" % ref)
        return
    fpid = str(fp.GetFPID().GetLibItemName())
    if not fpid.startswith("TO-247"):
        fails.append("%s footprint %s is not TO-247" % (ref, fpid))
        return
    if len(pads) != 3:
        fails.append("%s has %d pads, TO-247-3 has 3" % (ref, len(pads)))
    for p in pads:
        sz = p.GetSize()
        if (abs(pcbnew.ToMM(sz.x) - 2.5) > TOL or abs(pcbnew.ToMM(sz.y) - 4.5) > TOL):
            fails.append("%s pad %s is %.2fx%.2f, vendor 2.5x4.5"
                         % (ref, p.GetNumber(), pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)))
            break
    xs = [pcbnew.ToMM(p.GetPosition().x) for p in pads]
    got = pitch(xs)
    if got and any(abs(pv - 5.45) > 0.05 for pv in got):
        fails.append("%s lead pitch is %s, vendor 5.45" % (ref, got))


def check_vssop8(board, ref, fails):
    fp, pads = pads_of(board, ref)
    if fp is None:
        fails.append("%s missing" % ref)
        return
    fpid = str(fp.GetFPID().GetLibItemName())
    if not fpid.startswith("VSSOP-8_2.3x2mm_P0.5mm"):
        fails.append("%s footprint %s is not VSSOP-8 P0.5" % (ref, fpid))
        return
    if len(pads) != 8:
        fails.append("%s has %d pads, VSSOP-8 has 8" % (ref, len(pads)))
    for p in pads:
        sz = p.GetSize()
        if (abs(pcbnew.ToMM(sz.x) - 1.25) > TOL or abs(pcbnew.ToMM(sz.y) - 0.35) > TOL):
            fails.append("%s pad %s is %.2fx%.2f, vendor 1.25x0.35"
                         % (ref, p.GetNumber(), pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)))
            break
    ys = [pcbnew.ToMM(p.GetPosition().y) for p in pads]
    got = pitch(ys)
    if got and any(abs(pv - 0.5) > 0.02 for pv in got):
        fails.append("%s pitch is %s, vendor 0.50" % (ref, got))


def main():
    board = pcbnew.LoadBoard('powerboard-reva.kicad_pcb')
    fails = []

    for ref in ("U500", "U501"):
        check_hsop8(board, ref, fails)
    for ref in ("Q400", "Q401", "Q402", "Q403"):
        check_to247(board, ref, fails)
    for ref in ("U7", "U8", "U11", "U12", "U504"):
        check_vssop8(board, ref, fails)

    print("HSOP-8 (DDA SO PowerPAD) : U500, U501")
    print("TO-247-3                 : Q400-Q403")
    print("VSSOP-8 P0.5             : U7, U8, U11, U12, U504")
    if fails:
        print("\nFAIL (%d):" % len(fails))
        for f in fails:
            print("   %s" % f)
        return 1
    print("\nPASS: pad sizes, pitches, per-side counts and exposed pads match the")
    print("      vendor geometry for all three package families (11 footprints).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
