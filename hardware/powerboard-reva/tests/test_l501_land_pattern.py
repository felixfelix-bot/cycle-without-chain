"""RAIL-18: the L501 land pattern against TDK's published drawing.

WHY THIS EXISTS
---------------
``docs/design/open-gates-register.md`` RAIL-18 records that the TDK
SPM10065VC-D land pattern was never compared to any KiCad footprint, and that
the nearest stock land (``Inductor_SMD:L_Coilcraft_XAL1010-XXX``, 2.38 mm wide on
a 6.65 mm pitch) does not match it. A wrong pad geometry is a defect that only
appears at assembly, so the field was left blank rather than filled with
something plausible.

This module pins the hand-authored footprint to the numbers TDK actually prints,
from the vendor catalogue ``inductor_automotive_power_spm10065vc-d_en`` dated
20250303, page 3, RECOMMENDED LAND PATTERN:

    12.0  outside-to-outside span of both pads
     6.1  clear gap between the pads
     4.5  pad height

Pad width is **not printed**: it is 2.95 mm, derived as (12.0 - 6.1) / 2. The
tests assert the derived value against the printed ones so the derivation cannot
drift from its source.

WHAT THESE TESTS DO NOT ESTABLISH
---------------------------------
They check geometry against the vendor drawing and internal consistency
(courtyard encloses copper, pads symmetric, silk clear of copper). They are
**not** a manufacturability sign-off: TDK defines no solder-mask expansion, no
paste-aperture ratio is claimed, no thermal or current capability is implied, and
this footprint has never been through DRC, a fab DFM check or physical assembly.
"""

import re
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
FP_DIR = MODULE_DIR / "Powerboard.pretty"
FP_FILE = FP_DIR / "L_TDK_SPM10065VC-D.kicad_mod"

# TDK catalogue page 3, RECOMMENDED LAND PATTERN (mm)
TDK_SPAN = 12.0
TDK_GAP = 6.1
TDK_PAD_HEIGHT = 4.5
# TDK catalogue page 3, SHAPE & DIMENSIONS
TDK_BODY_L = 10.5
TDK_BODY_W = 10.0
TDK_BODY_TOL = 0.4

# derived, not printed
TDK_PAD_WIDTH = (TDK_SPAN - TDK_GAP) / 2
TDK_PAD_CENTRE_X = TDK_SPAN / 2 - TDK_PAD_WIDTH / 2

# the stock land the gate says does not match
STOCK_WIDTH = 2.38
STOCK_PITCH = 6.65


def _text():
    if not FP_FILE.is_file():
        raise AssertionError("footprint not implemented: %s" % FP_FILE)
    return FP_FILE.read_text(encoding="utf-8")


def _pads():
    """(number, x, y, w, h) for every smd rect pad."""
    return [
        (num, float(x), float(y), float(w), float(h))
        for num, x, y, w, h in re.findall(
            r'\(pad "(\d+)" smd rect\s*\(at ([\d.-]+) ([\d.-]+)\)\s*'
            r'\(size ([\d.]+) ([\d.]+)\)',
            _text(),
        )
    ]


def _layer_rects(layer):
    """(x1, y1, x2, y2) for each fp_rect on a layer."""
    out = []
    for m in re.finditer(
            r"\(fp_rect\s*\(start ([\d.-]+) ([\d.-]+)\)\s*"
            r"\(end ([\d.-]+) ([\d.-]+)\)(.*?)\n\t\)",
            _text(), re.S):
        if '"%s"' % layer in m.group(5):
            out.append(tuple(float(v) for v in m.groups()[:4]))
    return out


class LandPatternTest(unittest.TestCase):
    def setUp(self):
        self.text = _text()
        self.pads = _pads()

    # --- the file must be loadable at all ------------------------------
    def test_footprint_file_exists(self):
        self.assertTrue(FP_FILE.is_file())
        self.assertEqual(FP_DIR.name, "Powerboard.pretty")

    def test_library_table_registers_the_pretty_dir(self):
        table = (MODULE_DIR / "fp-lib-table").read_text(encoding="utf-8")
        self.assertIn("Powerboard.pretty", table)
        self.assertIn("${KIPRJMOD}", table)

    def test_no_semicolon_comments(self):
        # ';' is not valid in .kicad_mod; it makes KiCad fail with
        # "Unable to load library", which is exactly how this file first broke.
        for line in self.text.splitlines():
            self.assertFalse(line.strip().startswith(";"),
                             "';' comments are not valid in .kicad_mod")

    def test_parens_balance(self):
        depth = 0
        in_str = False
        prev = ""
        for ch in self.text:
            if ch == '"' and prev != "\\":
                in_str = not in_str
            elif not in_str:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    self.assertGreaterEqual(depth, 0, "unbalanced closing paren")
            prev = ch
        self.assertEqual(depth, 0, "unbalanced parens")

    # --- geometry against TDK ------------------------------------------
    def test_exactly_two_pads(self):
        self.assertEqual(len(self.pads), 2)

    def test_overall_span_matches_tdk(self):
        lo = min(x - w / 2 for _, x, _, w, _ in self.pads)
        hi = max(x + w / 2 for _, x, _, w, _ in self.pads)
        self.assertAlmostEqual(hi - lo, TDK_SPAN, places=6)

    def test_clear_gap_matches_tdk(self):
        left, right = sorted(self.pads, key=lambda p: p[1])[:2]
        gap = (right[1] - right[3] / 2) - (left[1] + left[3] / 2)
        self.assertAlmostEqual(gap, TDK_GAP, places=6)

    def test_pad_height_matches_tdk(self):
        for _, _, _, _, h in self.pads:
            self.assertAlmostEqual(h, TDK_PAD_HEIGHT, places=6)

    def test_pad_width_matches_the_derivation(self):
        for _, _, _, w, _ in self.pads:
            self.assertAlmostEqual(w, TDK_PAD_WIDTH, places=6)

    def test_span_equals_gap_plus_two_pad_widths(self):
        self.assertAlmostEqual(TDK_GAP + 2 * TDK_PAD_WIDTH, TDK_SPAN, places=6)

    def test_pads_symmetric_about_the_axis(self):
        left, right = sorted(self.pads, key=lambda p: p[1])[:2]
        self.assertAlmostEqual(left[1], -right[1], places=9)
        self.assertAlmostEqual(left[1], -TDK_PAD_CENTRE_X, places=6)

    def test_pads_share_one_y_centre(self):
        self.assertEqual(len({round(p[2], 6) for p in self.pads}), 1)

    # --- internal consistency ------------------------------------------
    def test_courtyard_encloses_all_copper(self):
        # This caught a real defect: pads reached x=6.00 inside a 5.50 courtyard.
        pad_x = [v for _, x, _, w, _ in self.pads for v in (x - w / 2, x + w / 2)]
        pad_y = [v for _, _, y, _, h in self.pads for v in (y - h / 2, y + h / 2)]
        courts = _layer_rects("F.CrtYd")
        self.assertTrue(courts, "no courtyard rectangle found")
        self.assertLessEqual(min(c[0] for c in courts), min(pad_x))
        self.assertGreaterEqual(max(c[2] for c in courts), max(pad_x))
        self.assertLessEqual(min(c[1] for c in courts), min(pad_y))
        self.assertGreaterEqual(max(c[3] for c in courts), max(pad_y))

    def test_courtyard_covers_body_at_worst_case_tolerance(self):
        half_l = (TDK_BODY_L + TDK_BODY_TOL) / 2
        half_w = (TDK_BODY_W + TDK_BODY_TOL) / 2
        courts = _layer_rects("F.CrtYd")
        self.assertLessEqual(min(c[0] for c in courts), -half_l)
        self.assertGreaterEqual(max(c[2] for c in courts), half_l)
        self.assertLessEqual(min(c[1] for c in courts), -half_w)

    def test_silk_does_not_cross_the_pads(self):
        pad_lo = min(x - w / 2 for _, x, _, w, _ in self.pads)
        pad_hi = max(x + w / 2 for _, x, _, w, _ in self.pads)
        for x1, y1, x2, y2 in _layer_rects("F.SilkS"):
            spans = x1 < pad_hi and x2 > pad_lo
            inside_y = abs(y1) < TDK_PAD_HEIGHT / 2 and abs(y2) < TDK_PAD_HEIGHT / 2
            self.assertFalse(spans and inside_y,
                             "silk outline overlaps the copper pads")

    # --- justification for hand-authoring ------------------------------
    def test_stock_footprint_really_does_not_match(self):
        self.assertGreater(abs(STOCK_WIDTH - TDK_PAD_WIDTH), 0.4)
        self.assertGreater(abs(STOCK_PITCH - TDK_GAP), 0.4)

    def test_description_records_source_and_derivation(self):
        self.assertIn("20250303", self.text,
                      "must cite the catalogue revision read")
        for value in ("12.00", "6.10", "4.50"):
            self.assertIn(value, self.text)
        self.assertIn("DERIVED", self.text,
                      "pad width is not printed by TDK; the file must say so")


if __name__ == "__main__":
    unittest.main()
