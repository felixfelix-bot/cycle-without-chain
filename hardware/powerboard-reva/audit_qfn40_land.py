#!/usr/bin/python3
"""Verify the stock QFN-40 land pattern against the vendor's published geometry (PCB-02).

WHY THIS GATE EXISTS
--------------------
PCB-02's pad half was only ever done for L501 (a vendor-transcribed TDK land pattern).
The power semiconductors still used KiCad library defaults that had never been compared
to a vendor drawing. A land pattern that is subtly wrong is discovered at assembly, not
in review -- which is exactly the failure mode the gate names.

WHAT IS CHECKED
---------------
QFN-40-1EP_6x6mm_P0.5mm_EP4.6x4.6mm, used by U1 and U2 (both DRV8353). Verified
against the published land geometry:
  * vendor package name: WQFN-40-EP(6x6), 40 pins + exposed pad, 0.5 mm pitch
  * pad 1 centred at (-2.9375, 2.2500) mm from the package origin
  * pad 1 size 0.8250 x 0.2500 mm
  * exposed pad 4.6 x 4.6 mm
  * pitch 0.5 mm, 10 pads per side

KiCad's Y axis is inverted relative to the Eagle-XML convention the vendor table uses,
so a pad at +2.2500 in the vendor table is at -2.2500 in KiCad. The check compares
MAGNITUDES and asserts the sign relationship explicitly, rather than silently
normalising it away -- a sign error in a land pattern mirrors the whole row.

Exit 0 when every checked quantity matches.
"""
import sys
import pcbnew

# Vendor-published geometry, from the DRV835x datasheet package drawing and the CAD
# table for DRV8353SRTAR (WQFN-40-EP 6x6).
VENDOR = {
    "package": "WQFN-40-EP(6x6)",
    "pins": 40,
    "pitch_mm": 0.5,
    "per_side": 10,
    "pad1_x_mm": -2.9375,
    "pad1_y_mm": 2.2500,      # vendor convention; KiCad is negated
    "pad_w_mm": 0.8250,
    "pad_h_mm": 0.2500,
    "ep_mm": 4.6,
}
TOL = 0.0005      # 0.5 um; the numbers are exact to 4 dp


def main():
    board = pcbnew.LoadBoard('powerboard-reva.kicad_pcb')
    fails = []
    checked = 0

    for ref in ("U1", "U2"):
        fp = None
        for f in board.GetFootprints():
            if f.GetReference() == ref:
                fp = f
                break
        if fp is None:
            fails.append("%s not found" % ref)
            continue

        fpid = str(fp.GetFPID().GetLibItemName())
        if fpid != "QFN-40-1EP_6x6mm_P0.5mm_EP4.6x4.6mm":
            fails.append("%s footprint is %s, expected the QFN-40 generic" % (ref, fpid))
            continue

        pads = [p for p in fp.Pads() if p.GetNumber()]
        checked += 1

        # PAD 41 IS THE EXPOSED PAD, and counting 41 pads against "40 pins" is a
        # false failure: the vendor package is WQFN-40-EP, forty pins PLUS a thermal
        # pad. The library models the EP as pad 41 (measured 4.60 x 4.60 mm, on F.Cu
        # and F.Mask). So the pin count excludes it and the EP is checked separately.
        ep = [p for p in fp.Pads() if pcbnew.ToMM(p.GetSize().x) > 3.0]
        ep_nums = {p.GetNumber() for p in ep}
        numbered = [p for p in pads if p.GetNumber().isdigit()
                    and p.GetNumber() not in ep_nums]
        if len(numbered) != VENDOR["pins"]:
            fails.append("%s has %d signal pads (excluding EP %s), vendor says %d"
                         % (ref, len(numbered), sorted(ep_nums), VENDOR["pins"]))

        # pad 1 position and size
        origin = fp.GetPosition()
        ox, oy = pcbnew.ToMM(origin.x), pcbnew.ToMM(origin.y)
        p1 = next((p for p in numbered if p.GetNumber() == "1"), None)
        if p1 is None:
            fails.append("%s has no pad 1" % ref)
            continue
        pos = p1.GetPosition()
        dx = pcbnew.ToMM(pos.x) - ox
        dy = pcbnew.ToMM(pos.y) - oy
        sz = p1.GetSize()
        w, h = pcbnew.ToMM(sz.x), pcbnew.ToMM(sz.y)

        if abs(dx - VENDOR["pad1_x_mm"]) > TOL:
            fails.append("%s pad1 x = %.4f, vendor %.4f" % (ref, dx, VENDOR["pad1_x_mm"]))
        # magnitude, with the sign relationship asserted rather than normalised away
        if abs(abs(dy) - VENDOR["pad1_y_mm"]) > TOL:
            fails.append("%s pad1 |y| = %.4f, vendor %.4f" % (ref, abs(dy), VENDOR["pad1_y_mm"]))
        if dy > 0:
            fails.append("%s pad1 y is positive (%.4f); KiCad's Y is inverted relative "
                         "to the vendor table, so it must be negative" % (ref, dy))
        if abs(w - VENDOR["pad_w_mm"]) > TOL or abs(h - VENDOR["pad_h_mm"]) > TOL:
            fails.append("%s pad1 size %.4fx%.4f, vendor %.4fx%.4f"
                         % (ref, w, h, VENDOR["pad_w_mm"], VENDOR["pad_h_mm"]))

        # PITCH IS ALONG THE SIDE THE PADS SIT ON, WHICH FOR A QFN IS THE CONSTANT-X
        # COLUMN. Pads 1-10 all share one x, so the row that has `per_side` members
        # is same_x, and the pitch runs in y.
        #
        # The earlier version picked whichever list was LONGER and then only computed
        # pitches when same_col won. same_col holds just the two pads that mirror each
        # other across the package (2 members), so ys was always None and the pitch
        # check NEVER RAN. A mutant that moved pad 2 by 0.15 mm -- turning a 0.5 mm
        # pitch into 0.65 then 0.35 -- therefore passed the audit. Caught by writing
        # the negative control instead of trusting the PASS.
        same_x = [p for p in numbered
                  if abs(pcbnew.ToMM(p.GetPosition().x) - pcbnew.ToMM(pos.x)) < 0.01]
        same_y = [p for p in numbered
                  if abs(pcbnew.ToMM(p.GetPosition().y) - pcbnew.ToMM(pos.y)) < 0.01]
        if len(same_x) >= len(same_y):
            side, axis = same_x, "y"
        else:
            side, axis = same_y, "x"
        if len(side) != VENDOR["per_side"]:
            fails.append("%s pad 1 sits in a row of %d along constant-%s, vendor says "
                         "%d per side" % (ref, len(side), "x" if axis == "y" else "y",
                                          VENDOR["per_side"]))
        coords = sorted(pcbnew.ToMM(p.GetPosition().y if axis == "y"
                                    else p.GetPosition().x) for p in side)
        if len(coords) > 1:
            pitches = [b - a for a, b in zip(coords, coords[1:])]
            bad = [pp for pp in pitches if abs(pp - VENDOR["pitch_mm"]) > 0.01]
            if bad:
                fails.append("%s pitch along %s is %s, vendor %.3f"
                             % (ref, axis, ["%.3f" % pp for pp in pitches],
                                VENDOR["pitch_mm"]))

        # exposed pad
        if not ep:
            fails.append("%s has no exposed pad" % ref)
        else:
            e = ep[0].GetSize()
            if (abs(pcbnew.ToMM(e.x) - VENDOR["ep_mm"]) > 0.01 or
                    abs(pcbnew.ToMM(e.y) - VENDOR["ep_mm"]) > 0.01):
                fails.append("%s EP is %.2fx%.2f, vendor %.1fx%.1f"
                             % (ref, pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                                VENDOR["ep_mm"], VENDOR["ep_mm"]))

    print("QFN-40 land pattern audit against %s (%d pins, %.1f mm pitch)"
          % (VENDOR["package"], VENDOR["pins"], VENDOR["pitch_mm"]))
    print("footprints checked: %d" % checked)
    if fails:
        print("\nFAIL:")
        for f in fails:
            print("   %s" % f)
        return 1
    print("\nPASS: pad 1 position, pad size, pitch, per-side count and exposed pad")
    print("      all match the vendor geometry on both DRV8353s.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
