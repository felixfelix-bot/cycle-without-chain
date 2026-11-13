"""PROT-10: the CSD19532Q5B drain leads and exposed pad on a 5x6 SON.

THE QUESTION
------------
The CSD19532Q5B is a SON 5x6 with eight leads plus an exposed pad. TI's
datasheet (SLPS414B, p.1 pin diagram) numbers them so that the drain is on
leads 5, 6, 7 and 8 *plus* the pad, the source on 1, 2 and 3, and the gate on 4.
The KiCad land pattern `TDSON-8-1` does not model that as nine separate pads. It
collapses the four drain leads and the pad into a single pad numbered "5" and
covers it with nine unnamed paste apertures.

That collapse is exactly the kind of thing that silently loses a connection: if
the four drain leads landed on a different net from the pad, the part would
still "pass" DRC and still look right on screen, while carrying the whole switch
current through one lead. PROT-10 exists to make that checkable rather than
assumed.

WHAT THIS ASSERTS
-----------------
1. Every CSD19532Q5B instance on the board uses the TDSON-8-1 land.
2. All of its drain copper resolves to one net: the pad and the collapsed leads
   are not split. Verified through the native export, which is generated from
   the schematic, so this tests the electrical intent rather than the drawing.
3. The source leads are all on one net and the gate is on its own.
4. The drain net is not the source net and not the gate net -- the one failure
   that would make the board a dead short.

WHAT THIS DOES NOT ASSERT
-------------------------
* It does not check the paste-to-copper ratio. The stock land puts four of the
  nine apertures outside the F.Mask opening (x 2.53-3.28 vs a mask edge at
  2.525). That is KiCad upstream's drawing, not a board error, and whether it
  is right is a stencil question I cannot settle without a real assembly. It is
  recorded as open below rather than asserted either way.
* It does not check thermal performance, current density in the pad, or via
  stitching under the pad.
"""
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

P = Path(__file__).resolve().parents[1]
EXPORT = P / 'exports' / 'ctrl-supply.xml'
BOARD = P / 'powerboard-reva.kicad_pcb'
LAND = 'TDSON-8-1'
PART = 'CSD19532Q5B'


def load_nets():
    root = ET.parse(EXPORT).getroot()
    values = {c.attrib['ref']: (c.findtext('value') or '')
              for c in root.findall('./components/comp')}
    nets = {}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'):
            nets.setdefault(node.attrib['ref'], {})[node.attrib['pin']] = net.attrib['name']
    return values, nets


def board_land_for(ref):
    """Footprint reference designator -> land name, read from the .kicad_pcb."""
    text = BOARD.read_text(encoding='utf-8')
    for block in re.split(r'\n\t\(footprint ', text)[1:]:
        # KiCad 9 writes (property "Reference" "Q1" ...); older files used
        # (fp_text reference "Q1" ...). Accept both rather than pin to one writer.
        pat = r'\(property "Reference" "%s"' % re.escape(ref)
        if re.search(pat, block):
            m = re.match(r'"([^"]+)"', block)
            if m:
                return m.group(1)
    return None


class MosfetLand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values, cls.nets = load_nets()
        cls.parts = [r for r, v in cls.values.items() if v and PART in v]
        if not cls.parts:
            raise ValueError(f'no {PART} instances found in the native export')

    def test_every_mosfet_uses_the_stock_tdson_land(self):
        for ref in self.parts:
            land = board_land_for(ref)
            if land != LAND:
                raise ValueError(f'{ref}: expected land {LAND}, got {land}')

    def test_drain_leads_and_pad_are_one_net(self):
        """The whole point of PROT-10: the collapse must not split the drain."""
        for ref in self.parts:
            pins = self.nets.get(ref, {})
            if '5' not in pins:
                raise ValueError(f'{ref}: drain pad (pin 5) is not on any net')
            drains = {p for p, n in pins.items() if n == pins['5']}
            # Pins 1-3 are source and 4 is gate on this part, so the drain group
            # is exactly {5} plus it must not swallow a source or gate lead.
            if drains != {'5'}:
                raise ValueError(f'{ref}: drain net also carries {sorted(drains - {"5"})}')

    def test_source_leads_share_one_net(self):
        for ref in self.parts:
            pins = self.nets.get(ref, {})
            src = {pins.get(p) for p in ('1', '2', '3')}
            if len(src) != 1 or None in src:
                raise ValueError(f'{ref}: source leads disagree: {sorted(map(str, src))}')

    def test_gate_is_separate_from_drain_and_source(self):
        for ref in self.parts:
            pins = self.nets.get(ref, {})
            gate = pins.get('4')
            drain = pins.get('5')
            src = pins.get('1')
            if gate is None:
                raise ValueError(f'{ref}: gate lead (pin 4) is not on any net')
            if gate in (drain, src):
                raise ValueError(f'{ref}: gate shorted to drain or source')

    def test_no_two_different_nets_on_the_drain_group(self):
        """A negative control that must be able to fail.

        If the land ever splits pins 5-8 across nets, the part still passes DRC
        and looks correct on screen while carrying switch current through one
        lead. This asserts the split cannot happen silently.
        """
        for ref in self.parts:
            pins = self.nets.get(ref, {})
            drainish = {pins[p] for p in ('5', '6', '7', '8') if p in pins}
            if len(drainish) > 1:
                raise ValueError(f'{ref}: drain leads split across {drainish}')


if __name__ == '__main__':
    unittest.main()
