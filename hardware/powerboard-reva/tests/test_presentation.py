"""Frozen native-export invariance and measured stroke-layout regression gates."""
import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from check_presentation_invariant import canonical
from check_legibility import measure,TITLES,overlap

class PresentationTests(unittest.TestCase):
    def test_native_identity(self):
        before=canonical(ROOT/'exports/legibility-before.xml')
        after=canonical(ROOT/'exports/legibility-after.xml')
        self.assertEqual(before,after)
        broken=copy.deepcopy(after)
        ref,pin,net=broken['ref_pin_net'][0]
        broken['ref_pin_net'][0]=(ref,pin,net+'_BROKEN')
        self.assertNotEqual(before,broken)

    def test_native_svg_clearances(self):
        pages=[p for p in (ROOT/'exports/svg').glob('*.svg') if any(t in p.name for t in TITLES)]
        self.assertEqual(len(pages),8)
        for p in pages:
            with self.subTest(page=p.name):
                r=measure(p)
                self.assertGreater(len(r['text_bounds_mm']),20)
                self.assertEqual(r['text_text'],[])
                self.assertEqual(r['text_graphic'],[])
        self.assertTrue(overlap([0,0,2,2],[1,1,3,3]))
        self.assertFalse(overlap([0,0,1,1],[2,2,3,3]))
